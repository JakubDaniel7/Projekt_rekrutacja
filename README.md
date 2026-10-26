# Książka telefoniczna

Aplikacja do zarządzania kontaktami w Django – zadanie rekrutacyjne na stanowisko Junior Fullstack Developer w Supra Brokers.

Można w niej wyszukiwać, dodawać, edytować i usuwać kontakty, importować je z CSV i eksportować z powrotem. Przy każdym kontakcie widać aktualną pogodę w jego mieście, a w zakładce Statystyki są dwa proste wykresy.

## Uruchomienie

Potrzebny jest Python 3.10 lub nowszy (pisałem na 3.13) i Git.

```bash
git clone https://github.com/JakubDaniel7/Projekt_rekrutacja.git
cd Projekt_rekrutacja

python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows (PowerShell)
# source .venv/bin/activate       # Linux / macOS

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Aplikacja działa pod http://127.0.0.1:8000/. Baza jest na starcie pusta, więc najszybciej kliknąć **Import CSV** i wybrać plik `sample_contacts.csv` z katalogu projektu – to 30 przykładowych kontaktów.

Statusy („nowy”, „w trakcie”, „zagubiony”, „nieaktualny”) tworzą się same przy `migrate`. Jeśli chcesz je edytować albo dodać nowy, przyda się konto do panelu admina:

```bash
python manage.py createsuperuser
```

Jeśli na Windowsie aktywacja środowiska kończy się błędem o *execution policy*, wystarczy raz wpisać `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

Testy:

```bash
python manage.py test
```

### Docker

Można też postawić wszystko w Dockerze (potrzebny Docker Desktop):

```bash
docker compose up --build
```

Aplikacja wstaje pod http://localhost:8000/. Przy starcie kontener sam robi migracje, a baza leży w osobnym wolumenie, więc dane zostają po `docker compose down`. Konto do admina i testy w kontenerze:

```bash
docker compose exec web python manage.py createsuperuser
docker compose run --rm web python manage.py test
```

To jest konfiguracja do developmentu (`runserver`, włączony `DEBUG`). Na produkcję podmieniłbym serwer na gunicorna i ustawił prawdziwy `SECRET_KEY` w zmiennych środowiskowych.

## Co jest zrobione

Wszystkie wymagania z treści zadania, a z zadań dodatkowych: Docker, cache pogody, testy (13), wykresy ze statystykami i eksport do CSV. Logowania z izolacją danych (zadanie 6) nie robiłem.

Poza tym dodałem kilka rzeczy od siebie: tryb ciemny, usuwanie bez przeładowania strony z oknem potwierdzenia, ikony pogody zależne od tego, czy pada, świeci słońce itd., i widok kart zamiast tabeli na telefonie.

Użyłem Django 5.2, Django REST Framework i SQLite. Na froncie Bootstrap 5, htmx i Chart.js, wszystko ładowane z CDN, więc nie trzeba instalować Node'a ani niczego budować.

## API

| Metoda | Adres | Co robi |
|---|---|---|
| GET | `/api/contacts/` | lista kontaktów (id, imię, nazwisko, miasto, status, data dodania) |
| POST | `/api/contacts/` | dodanie kontaktu |
| GET | `/api/contacts/{id}/` | szczegóły jednego kontaktu |
| PUT / PATCH | `/api/contacts/{id}/` | edycja |
| DELETE | `/api/contacts/{id}/` | usunięcie |
| GET | `/api/weather/?city=Kraków` | pogoda dla miasta (z tego korzysta lista) |

Status podaje się nazwą, nie numerem:

```bash
curl -X POST http://127.0.0.1:8000/api/contacts/ \
  -H "Content-Type: application/json" \
  -d '{"first_name": "Anna", "last_name": "Nowak", "phone": "600 100 200", "email": "anna@example.com", "city": "Kraków", "status": "nowy"}'
```

API można też przeklikać w przeglądarce: http://127.0.0.1:8000/api/contacts/

## Plik CSV

Pierwszy wiersz to nagłówki:

```
imię,nazwisko,telefon,email,miasto,status
Anna,Nowak,600 100 200,anna@example.com,Kraków,w trakcie
```

Kolumna `status` może nie istnieć, wtedy kontakt dostaje „nowy”. Separatorem może być przecinek albo średnik, bo polski Excel zapisuje CSV ze średnikami i w kodowaniu cp1250 – oba warianty działają. Błędne wiersze są pomijane, a po imporcie widać, który wiersz i dlaczego nie przeszedł. Eksport da się zaimportować z powrotem.

## Kilka decyzji, które warto wyjaśnić

Telefon i e-mail normalizuję w `Contact.clean()` (usuwam spacje i myślniki z numeru, e-mail zmieniam na małe litery). Formularz, panel admina i import CSV przechodzą przez ten sam `ContactForm`, a serializer w API woła `full_clean()` sam, bo DRF domyślnie pomija walidację modelu. Dzięki temu „600 100 200” i „600-100-200” są traktowane jako ten sam numer wszędzie, a nie tylko w formularzu. Walidacja w JS sprawdza to samo dla szybszej informacji, ale unikalność może sprawdzić tylko serwer.

Wyszukiwanie miało problem z polskimi literami – SQLite ignoruje wielkość liter tylko dla ASCII, więc „łukasz” nie znajdowało „Łukasz”. Dodałem pole `search_text` z małymi literami, liczone przy zapisie, i po nim szukam. Przy okazji każde słowo z wyszukiwarki jest sprawdzane osobno, więc „jan kraków” też działa.

Pogodę pobiera przeglądarka, ale nie bezpośrednio z Nominatim i Open-Meteo, tylko przez mój endpoint `/api/weather/`, który trzyma wyniki w cache. Współrzędne miasta są pamiętane tydzień, pogoda 30 minut. Zapamiętuję też, że miasta nie znaleziono, żeby literówka nie odpytywała API przy każdym odświeżeniu. Nominatim w regulaminie wymaga max 1 zapytania na sekundę i własnego User-Agenta, więc to też jest pilnowane. Na stronie każde miasto jest odpytywane raz, nawet jeśli jest przy kilku kontaktach.

Przykładowy adres Open-Meteo z treści zadania (`current_weather=true`) nie zwraca wilgotności, dlatego używam parametru `current=` z ich aktualnej dokumentacji.

Zamiast pisać front w React wziąłem htmx – wyszukiwanie, sortowanie, stronicowanie i usuwanie wysyłają zwykłe żądania, Django zwraca kawałek HTML, a htmx podmienia tylko tabelę. Bez JavaScriptu lista, wyszukiwanie i usuwanie nadal działają, tylko z przeładowaniem strony.

Domyślne statusy tworzy migracja danych, więc są od razu po `migrate`. Każdy status ma też zapisany kolor plakietki, więc nowy status dodany w adminie od razu dobrze wygląda.

## Struktura

```
config/                 ustawienia projektu
contacts/
  models.py             modele i reguły normalizacji
  forms.py              formularz kontaktu i formularz importu
  views.py              widoki HTML (lista, formularze, import/eksport, statystyki)
  api.py                REST API i endpoint pogody
  serializers.py        serializery DRF
  csv_io.py             import i eksport CSV
  weather.py            pobieranie pogody z cache
  tests.py              testy
  templates/contacts/   szablony (_contact_table.html to fragment podmieniany przez htmx)
  static/contacts/      CSS i JS
sample_contacts.csv     dane przykładowe
Dockerfile, docker-compose.yml
```
