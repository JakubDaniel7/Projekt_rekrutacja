from unittest import mock

import requests
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from . import weather
from .csv_io import import_contacts
from .forms import ContactForm
from .models import Contact, ContactStatus


def make_contact(**overrides):
    data = {
        "first_name": "Jan",
        "last_name": "Kowalski",
        "phone": "600100200",
        "email": "jan@example.com",
        "city": "Kraków",
        "status": ContactStatus.objects.get(name="nowy"),  # created by the data migration
    }
    data.update(overrides)
    return Contact.objects.create(**data)


class ContactValidationTests(TestCase):
    def form_data(self, **overrides):
        data = {
            "first_name": "Anna",
            "last_name": "Nowak",
            "phone": "600 200 300",
            "email": "Anna@Example.com",
            "city": "Gdańsk",
            "status": ContactStatus.objects.get(name="nowy").pk,
        }
        data.update(overrides)
        return data

    def test_phone_and_email_are_normalized(self):
        form = ContactForm(self.form_data())
        self.assertTrue(form.is_valid(), form.errors)

        contact = form.save()

        self.assertEqual(contact.phone, "600200300")
        self.assertEqual(contact.email, "anna@example.com")

    def test_same_phone_written_differently_is_a_duplicate(self):
        make_contact(phone="600200300", email="other@example.com")

        form = ContactForm(self.form_data(phone="600-200-300"))

        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)

    def test_phone_with_too_few_digits_is_rejected(self):
        form = ContactForm(self.form_data(phone="12 34"))

        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)


class ContactApiTests(TestCase):
    payload = {
        "first_name": "Ewa",
        "last_name": "Mazur",
        "phone": "600 300 400",
        "email": "ewa@example.com",
        "city": "Opole",
        "status": "w trakcie",
    }

    def test_list_returns_the_fields_required_by_the_task(self):
        make_contact()

        response = self.client.get(reverse("contact-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.json()[0]),
            {"id", "first_name", "last_name", "city", "status", "created_at"},
        )

    def test_create_update_and_delete(self):
        response = self.client.post(reverse("contact-list"), self.payload, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["phone"], "600300400")  # same normalization as the HTML form

        detail_url = reverse("contact-detail", args=[response.json()["id"]])
        response = self.client.put(detail_url, {**self.payload, "city": "Gliwice"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["city"], "Gliwice")

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Contact.objects.exists())

    def test_duplicate_phone_is_rejected(self):
        make_contact(phone="600300400")

        with self.assertLogs("django.request", "WARNING"):  # Django logs every 400 response
            response = self.client.post(reverse("contact-list"), self.payload, content_type="application/json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("phone", response.json())


class ContactListViewTests(TestCase):
    def test_search_ignores_letter_case_in_polish_names(self):
        make_contact(last_name="Łukasiewicz")
        make_contact(last_name="Nowak", phone="600100201", email="nowak@example.com")

        response = self.client.get(reverse("contacts:list"), {"q": "ŁUKASIEWICZ"})

        self.assertEqual([contact.last_name for contact in response.context["contacts"]], ["Łukasiewicz"])

    def test_htmx_delete_removes_the_contact_and_triggers_a_toast(self):
        contact = make_contact()

        response = self.client.post(
            reverse("contacts:delete", args=[contact.pk]), headers={"HX-Request": "true"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("showMessage", response.headers["HX-Trigger"])
        self.assertFalse(Contact.objects.exists())


class CsvImportTests(TestCase):
    def csv_file(self, text, encoding="utf-8"):
        return SimpleUploadedFile("contacts.csv", text.encode(encoding))

    def test_valid_rows_are_imported_and_invalid_rows_reported(self):
        csv_file = self.csv_file(
            "imię,nazwisko,telefon,email,miasto,status\n"
            "Anna,Nowak,600 100 200,anna@example.com,Kraków,w trakcie\n"
            "Jan,Krótki,123,jan@example.com,Opole,nowy\n"  # phone too short
            "Ewa,Mazur,600 100 201,ewa@example.com,Łódź,\n"  # no status - defaults to "nowy"
        )

        result = import_contacts(csv_file)

        self.assertEqual(result.created, 2)
        self.assertEqual([line_number for line_number, _ in result.errors], [3])
        self.assertEqual(Contact.objects.get(last_name="Mazur").status.name, "nowy")

    def test_file_from_polish_excel_is_supported(self):
        # Polish Excel saves CSV with ";" separators and cp1250 encoding
        csv_file = self.csv_file(
            "Imię;Nazwisko;Telefon;Email;Miasto\n"
            "Żaneta;Łęcka;700 100 200;zaneta@example.com;Łódź\n",
            encoding="cp1250",
        )

        result = import_contacts(csv_file)

        self.assertEqual(result.created, 1)
        self.assertTrue(Contact.objects.filter(last_name="Łęcka", city="Łódź").exists())


def fake_response(json_data):
    response = mock.Mock()
    response.json.return_value = json_data
    return response


GEOCODING_RESPONSE = [{"lat": "50.06", "lon": "19.94"}]
WEATHER_RESPONSE = {
    "current": {"temperature_2m": 7.5, "relative_humidity_2m": 80, "wind_speed_10m": 12.0, "weather_code": 3}
}


@mock.patch("contacts.weather._wait_for_nominatim")  # skip the 1-second pause between Nominatim calls
@mock.patch("contacts.weather.requests.get")  # no real HTTP requests in tests
class WeatherTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_weather_is_fetched_once_then_served_from_cache(self, get, _wait):
        get.side_effect = [fake_response(GEOCODING_RESPONSE), fake_response(WEATHER_RESPONSE)]

        first = weather.get_weather("Kraków")
        second = weather.get_weather(" kraków ")

        self.assertEqual(first, {"temperature": 7.5, "humidity": 80, "wind_speed": 12.0, "weather_code": 3})
        self.assertEqual(second, first)
        self.assertEqual(get.call_count, 2)  # one Nominatim + one Open-Meteo call in total

    def test_unknown_city_returns_404(self, get, _wait):
        get.return_value = fake_response([])

        with self.assertLogs("django.request", "WARNING"):
            response = self.client.get(reverse("weather"), {"city": "Xyzqwerty"})

        self.assertEqual(response.status_code, 404)

    def test_service_failure_returns_503(self, get, _wait):
        get.side_effect = requests.ConnectionError

        with self.assertLogs("contacts.api", "WARNING"), self.assertLogs("django.request", "ERROR"):
            response = self.client.get(reverse("weather"), {"city": "Kraków"})

        self.assertEqual(response.status_code, 503)