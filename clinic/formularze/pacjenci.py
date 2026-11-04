import re
from django import forms
from django.utils import timezone
from ..models import Pacjent
from .pola import StylFormularza, poczatek_numeru_pesel, cyfra_kontrolna_pesel


class FormularzPacjenta(StylFormularza, forms.ModelForm):
    class Meta:
        model = Pacjent
        fields = [
            "first_name",
            "second_name",
            "last_name",
            "birth_date",
            "pesel",
            "sex",
            "phone",
            "email",
            "address",
        ]
        widgets = {
            "birth_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ustaw_wyglad()

    def clean(self):
        data = super().clean()
        value = data.get("pesel", "")
        if value:
            if not re.fullmatch(r"[0-9]{11}", value):
                self.add_error(
                    "pesel",
                    "PESEL musi zawierać dokładnie 11 cyfr, bez spacji i myślników.",
                )
            elif value[-1] != cyfra_kontrolna_pesel(value[:10]):
                self.add_error(
                    "pesel",
                    "Nieprawidłowa cyfra kontrolna PESEL. Sprawdź wpisany numer.",
                )
            elif data.get("birth_date") and value[:6] != poczatek_numeru_pesel(
                data["birth_date"]
            ):
                self.add_error(
                    "pesel",
                    "Data urodzenia zakodowana w PESEL nie zgadza się z podaną datą urodzenia.",
                )
            elif data.get("sex") in ["K", "M"] and int(value[9]) % 2 != (
                data["sex"] == "M"
            ):
                self.add_error(
                    "pesel", "Płeć zakodowana w PESEL nie zgadza się z wybraną płcią."
                )
            elif (
                Pacjent.objects.filter(doctor_id=self.instance.doctor_id, pesel=value)
                .exclude(pk=self.instance.pk)
                .exists()
            ):
                self.add_error(
                    "pesel", "Ten PESEL jest już przypisany do innej kartoteki."
                )
        return data

    def clean_birth_date(self):
        value = self.cleaned_data["birth_date"]
        today = timezone.localdate()
        age = (
            today.year
            - value.year
            - ((today.month, today.day) < (value.month, value.day))
        )
        if age < 18 or age > 120:
            raise forms.ValidationError(
                "Poradnia obsługuje osoby pełnoletnie (18–120 lat)."
            )
        return value


class FormularzWynikuBadania(forms.Form):
    result = forms.FileField(
        label="Wynik badania (PDF)",
        widget=forms.ClearableFileInput(
            attrs={"accept": ".pdf,application/pdf", "class": "input"}
        ),
        help_text="Plik PDF do 5 MB.",
    )

    def clean_result(self):
        upload = self.cleaned_data["result"]
        if upload.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Plik może mieć maksymalnie 5 MB.")
        header = upload.read(5)
        upload.seek(0)
        if not upload.name.lower().endswith(".pdf") or header != b"%PDF-":
            raise forms.ValidationError("Wybierz plik PDF z poprawnym nagłówkiem.")
        return upload

