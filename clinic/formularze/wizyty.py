import re
from django import forms
from ..models import Wizyta
from .pola import StylFormularza


ETAPY_WIZYTY = [
    (
        "Wywiad wstępny",
        [
            "past_diseases",
            "history",
            "allergies",
            "disability",
            "development",
            "family_history",
            "hereditary_burden",
            "hospitalizations",
            "operations",
            "risk_factors",
            "vaccinations",
            "addictions",
            "specialist_care",
        ],
    ),
    (
        "Badanie przedmiotowe",
        [
            "weight",
            "general_condition",
            "lymph_nodes",
            "head",
            "neck",
            "upper_airways",
            "chest",
            "lower_airways",
            "circulation",
            "abdomen",
            "urinary_system",
            "musculoskeletal",
        ],
    ),
    ("Wywiad ogólny", ["complaint", "diet", "medication"]),
]


POLA_WYWIADU = [name for _, names in ETAPY_WIZYTY for name in names]


class FormularzWizyty(StylFormularza, forms.ModelForm):
    weight = forms.CharField(
        label="Masa ciała [kg]",
        required=False,
        widget=forms.TextInput(attrs={"inputmode": "decimal"}),
    )
    revision = forms.IntegerField(widget=forms.HiddenInput)
    medicines_reviewed = forms.BooleanField(
        required=False,
        label="Sprawdziłem dla preparatów z katalogu: pełny skład i alergie, interakcje i dublowanie leków, choroby nerek i wątroby, przeciwwskazania, ciążę/karmienie oraz objawy alarmowe. Dane zapisane w wywiadzie są aktualne.",
    )
    privacy_checked = forms.BooleanField(
        required=False,
        label="Sprawdziłem podgląd danych dla AI: nie zawiera danych identyfikujących pacjenta.",
    )

    class Meta:
        model = Wizyta
        fields = POLA_WYWIADU + ["summary", "recommendations", "medicines_reviewed"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["revision"].initial = self.instance.revision
        self.fields["weight"].widget.attrs["placeholder"] = "Nie podaje"
        self.fields["weight"].label = "Masa ciała [kg]"
        if not self.is_bound and self.instance.weight is None:
            self.initial["weight"] = "Nie podaje"
        self.fields["complaint"].label = "Objawy ogólne (wymagane)"
        self.fields["complaint"].widget.attrs["placeholder"] = "Wymagane"
        if (
            not self.is_bound
            and self.initial.get("complaint", "").strip().casefold() == "nie podaje"
        ):
            self.initial["complaint"] = ""
        self.ustaw_wyglad()

    def clean_weight(self):
        value = self.cleaned_data.get("weight", "").strip()
        if not value or value.casefold() == "nie podaje":
            return None
        return forms.DecimalField(max_digits=5, decimal_places=1).clean(
            value.replace(",", ".")
        )

    def clean(self):
        data = super().clean()
        for name, low, high in [
            ("pulse", 20, 300),
            ("temperature", 30, 45),
            ("weight", 20, 400),
            ("height", 80, 250),
        ]:
            value = data.get(name)
            if value is not None and not low <= value <= high:
                self.add_error(name, f"Dopuszczalny zakres: {low}–{high}.")
        pressure = data.get("pressure", "")
        if pressure and not re.fullmatch(r"\d{2,3}\s*/\s*\d{2,3}", pressure):
            self.add_error("pressure", "Podaj wartość w formacie np. 120/80.")
        for name in POLA_WYWIADU + ["summary", "recommendations"]:
            if isinstance(data.get(name), str) and len(data[name]) > 5000:
                self.add_error(name, "Maksymalnie 5000 znaków w polu.")
        return data

