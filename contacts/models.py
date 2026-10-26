import re

from django.core.exceptions import ValidationError
from django.db import models

# 9-15 digits with an optional leading "+", checked after removing spaces, dashes and brackets
PHONE_PATTERN = re.compile(r"^\+?\d{9,15}$")


class ContactStatus(models.Model):
    """Contact status stored in its own table, so statuses can be added or renamed without code changes."""

    BADGE_COLORS = [
        ("primary", "Niebieski"),
        ("success", "Zielony"),
        ("warning", "Żółty"),
        ("danger", "Czerwony"),
        ("info", "Turkusowy"),
        ("secondary", "Szary"),
    ]

    name = models.CharField("nazwa", max_length=50, unique=True)
    color = models.CharField("kolor etykiety", max_length=20, choices=BADGE_COLORS, default="secondary")

    class Meta:
        ordering = ["id"]
        verbose_name = "status kontaktu"
        verbose_name_plural = "statusy kontaktów"

    def __str__(self):
        return self.name


class Contact(models.Model):
    first_name = models.CharField("imię", max_length=50)
    last_name = models.CharField("nazwisko", max_length=50)
    phone = models.CharField(
        "numer telefonu",
        max_length=20,
        unique=True,
        error_messages={"unique": "Ten numer telefonu jest już przypisany do innego kontaktu."},
    )
    email = models.EmailField(
        "adres e-mail",
        unique=True,
        error_messages={"unique": "Ten adres e-mail jest już przypisany do innego kontaktu."},
    )
    city = models.CharField("miasto", max_length=100)
    status = models.ForeignKey(
        ContactStatus,
        on_delete=models.PROTECT,  # a status that is still in use cannot be deleted
        related_name="contacts",
        verbose_name="status",
    )
    created_at = models.DateTimeField("data dodania", auto_now_add=True)
    # Lowercase copy of searchable fields. SQLite ignores letter case only for ASCII,
    # so without this, searching for "łukasz" would not find "Łukasz".
    # Filled in save(), so it can still be empty during validation.
    search_text = models.TextField(editable=False, blank=True, default="")

    class Meta:
        ordering = ["last_name", "first_name"]
        verbose_name = "kontakt"
        verbose_name_plural = "kontakty"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def clean(self):
        # Runs during form validation, before Django checks uniqueness,
        # so "600 100 200" and "600100200" are treated as the same number.
        if self.email:
            self.email = self.email.strip().lower()
        if self.phone:
            self.phone = re.sub(r"[\s\-()]", "", self.phone)
            if not PHONE_PATTERN.match(self.phone):
                raise ValidationError(
                    {"phone": "Podaj od 9 do 15 cyfr, opcjonalnie z + na początku."}
                )

    def save(self, *args, **kwargs):
        self.search_text = " ".join(
            [self.first_name, self.last_name, self.email, self.phone, self.city]
        ).lower()
        super().save(*args, **kwargs)