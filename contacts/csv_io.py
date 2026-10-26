import csv
import io
from dataclasses import dataclass, field

from django.db import transaction
from django.utils import timezone

from .forms import ContactForm
from .models import Contact, ContactStatus

# Accepted CSV headers (lowercase) mapped to model fields; Polish and English names both work
COLUMN_ALIASES = {
    "imię": "first_name",
    "imie": "first_name",
    "first_name": "first_name",
    "nazwisko": "last_name",
    "last_name": "last_name",
    "telefon": "phone",
    "phone": "phone",
    "email": "email",
    "e-mail": "email",
    "miasto": "city",
    "city": "city",
    "status": "status",
}
REQUIRED_FIELDS = ["first_name", "last_name", "phone", "email", "city"]
DEFAULT_STATUS = "nowy"
EXPORT_HEADERS = ["imię", "nazwisko", "telefon", "email", "miasto", "status", "data dodania"]


class CsvImportError(Exception):
    """The whole file cannot be imported (unreadable encoding, missing columns)."""


@dataclass
class ImportResult:
    created: int = 0
    errors: list = field(default_factory=list)  # (line number, message) pairs


def import_contacts(uploaded_file):
    """Create contacts from a CSV file. Invalid rows are skipped and reported."""
    text = _decode(uploaded_file.read())

    # Polish Excel separates columns with ";", most other tools use ","
    try:
        dialect = csv.Sniffer().sniff(text[:2048], delimiters=",;")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)

    # Map each CSV header to a model field (unknown columns are ignored)
    columns = {}
    for header in reader.fieldnames or []:
        model_field = COLUMN_ALIASES.get(header.strip().lower())
        if model_field:
            columns[header] = model_field

    missing = [name for name in REQUIRED_FIELDS if name not in columns.values()]
    if missing:
        labels = ", ".join(str(Contact._meta.get_field(name).verbose_name) for name in missing)
        raise CsvImportError(f"Brak wymaganych kolumn: {labels}.")

    statuses = {status.name.lower(): status.pk for status in ContactStatus.objects.all()}
    result = ImportResult()

    # One transaction for the whole file - much faster on SQLite than a commit per row
    with transaction.atomic():
        # Line 1 is the header, so data starts at line 2
        for line_number, row in enumerate(reader, start=2):
            data = {model_field: (row.get(header) or "").strip() for header, model_field in columns.items()}

            status_name = data.pop("status", "").lower() or DEFAULT_STATUS
            if status_name not in statuses:
                result.errors.append((line_number, f"Nieznany status „{status_name}”."))
                continue
            data["status"] = statuses[status_name]

            # The same form as in the UI, so every validation rule (format, uniqueness) applies
            form = ContactForm(data)
            if form.is_valid():
                form.save()
                result.created += 1
            else:
                result.errors.append((line_number, _format_errors(form)))

    return result


def _decode(raw):
    # Excel saves CSV either as UTF-8 (often with a BOM) or, on Polish Windows, as cp1250
    for encoding in ("utf-8-sig", "cp1250"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise CsvImportError("Nie udało się odczytać pliku. Zapisz go jako CSV w kodowaniu UTF-8.")


def _format_errors(form):
    parts = []
    for name, messages in form.errors.items():
        text = " ".join(messages)
        parts.append(f"{form.fields[name].label}: {text}" if name in form.fields else text)
    return " ".join(parts)


def export_contacts(contacts, output):
    """Write contacts as CSV that opens in Polish Excel and can be imported back."""
    # Polish Excel expects ";" as the separator
    writer = csv.writer(output, delimiter=";")
    writer.writerow(EXPORT_HEADERS)
    for contact in contacts:
        writer.writerow([
            contact.first_name,
            contact.last_name,
            contact.phone,
            contact.email,
            contact.city,
            contact.status.name,
            timezone.localtime(contact.created_at).strftime("%Y-%m-%d %H:%M"),
        ])