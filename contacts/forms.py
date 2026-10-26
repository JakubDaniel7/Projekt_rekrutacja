from django import forms

from .models import Contact, ContactStatus

# Browser-side hint only; the exact rule (9-15 digits) is enforced in Contact.clean()
PHONE_INPUT_PATTERN = r"\+?[0-9\s\-\(\)]{9,20}"


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ["first_name", "last_name", "phone", "email", "city", "status"]
        widgets = {
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name"}),
            "phone": forms.TextInput(attrs={
                "type": "tel",
                "autocomplete": "tel",
                "placeholder": "np. 600 100 200",
                "pattern": PHONE_INPUT_PATTERN,
                "title": "Od 9 do 15 cyfr, mogą być spacje i myślniki.",
            }),
            "email": forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "np. jan@example.com"}),
            "city": forms.TextInput(attrs={"autocomplete": "address-level2", "placeholder": "np. Warszawa"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to every widget
        for field in self.fields.values():
            is_select = isinstance(field.widget, forms.Select)
            field.widget.attrs["class"] = "form-select" if is_select else "form-control"

        # No empty "---------" option; new contacts start as "nowy"
        self.fields["status"].empty_label = None
        if not self.instance.pk:
            self.fields["status"].initial = ContactStatus.objects.filter(name="nowy").first()

    def full_clean(self):
        super().full_clean()
        # Highlight invalid fields with Bootstrap's red border
        for name in self.errors:
            if name in self.fields:
                self.fields[name].widget.attrs["class"] += " is-invalid"


class CsvImportForm(forms.Form):
    file = forms.FileField(
        label="Plik CSV",
        widget=forms.FileInput(attrs={"class": "form-control", "accept": ".csv"}),
    )

    def clean_file(self):
        file = self.cleaned_data["file"]
        if not file.name.lower().endswith(".csv"):
            raise forms.ValidationError("Wybierz plik z rozszerzeniem .csv.")
        if file.size > 2 * 1024 * 1024:
            raise forms.ValidationError("Plik jest za duży (maksymalnie 2 MB).")
        return file    