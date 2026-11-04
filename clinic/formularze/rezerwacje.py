from datetime import timedelta
import re
from django import forms
from .pacjenci import FormularzPacjenta
from .pola import WyborWieluPlikow
from django.utils import timezone
from ..models import Rezerwacja
from .pola import StylFormularza, PolePlikowMedycznych


class FormularzRezerwacji(StylFormularza, forms.ModelForm):
    first_name = forms.CharField(label="Imię", max_length=80)
    last_name = forms.CharField(label="Nazwisko", max_length=100)
    acknowledged = forms.BooleanField(label="Potwierdzam poprawność podanych danych.")
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Rezerwacja
        fields = [
            "first_name",
            "second_name",
            "last_name",
            "birth_date",
            "phone",
            "email",
            "address",
        ]
        widgets = {
            "birth_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.Meta.fields:
            self.fields[name].required = name != "second_name"
        self.ustaw_wyglad()

    def clean(self):
        data = super().clean()
        if data.get("first_name") and data.get("last_name"):
            data["name"] = " ".join(
                part
                for part in [
                    data["first_name"],
                    data.get("second_name", ""),
                    data["last_name"],
                ]
                if part
            )
            self.instance.name = data["name"]
        return data

    def clean_phone(self):
        value = self.cleaned_data["phone"]
        if not re.fullmatch(r"[+\d ()-]{7,30}", value):
            raise forms.ValidationError("Wpisz poprawny numer telefonu.")
        return value

    clean_birth_date = FormularzPacjenta.clean_birth_date

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Nieprawidłowe zgłoszenie.")
        return ""


class FormularzRezerwacjiPacjenta(FormularzRezerwacji):
    birth_date = forms.DateField(
        label="Data urodzenia", widget=forms.DateInput(attrs={"type": "date"})
    )

    clean_birth_date = FormularzPacjenta.clean_birth_date
    attachments = PolePlikowMedycznych(
        required=False,
        label="Dokumenty z wcześniejszych badań (opcjonalnie)",
        help_text="Do 5 plików PDF, JPG lub PNG, każdy do 5 MB. Możesz też przynieść wyniki na wizytę. Pliki nie są przekazywane do AI.",
        widget=WyborWieluPlikow(attrs={"accept": ".pdf,.jpg,.jpeg,.png"}),
    )


class FormularzDostepnosci(forms.Form):
    day = forms.DateField(label="Dzień", widget=forms.DateInput(attrs={"type": "date"}))
    start = forms.TimeField(
        label="Od godziny",
        widget=forms.TimeInput(attrs={"type": "time"}),
        initial="09:00",
    )
    end = forms.TimeField(
        label="Do godziny",
        widget=forms.TimeInput(attrs={"type": "time"}),
        initial="15:00",
    )
    duration = forms.TypedChoiceField(
        label="Długość wizyty",
        choices=[
            (20, "20 minut"),
            (30, "30 minut"),
            (45, "45 minut"),
            (60, "60 minut"),
        ],
        coerce=int,
        initial=30,
    )

    def clean(self):
        data = super().clean()
        if data.get("day") and not timezone.localdate() <= data[
            "day"
        ] <= timezone.localdate() + timedelta(days=365):
            self.add_error("day", "Wybierz dzień w ciągu najbliższego roku.")
        if data.get("start") and data.get("end") and data["start"] >= data["end"]:
            self.add_error("end", "Koniec musi przypadać po początku.")
        return data

