from django import forms
from django.utils import timezone
from ..models import Pacjent, Wizyta, Umowa, Dokument
from .pola import StylFormularza


class FormularzDokumentu(StylFormularza, forms.ModelForm):
    patient_name = forms.CharField(
        label="Pani/Pan — imię i nazwisko, wiek", disabled=True, required=False
    )
    patient_pesel = forms.CharField(label="PESEL", disabled=True, required=False)
    patient_address = forms.CharField(label="Adres zamieszkania", max_length=250)

    class Meta:
        model = Dokument
        fields = ["kind", "patient", "visit", "title", "content", "reason", "agreement"]
        labels = {
            "patient": "Pacjent",
            "visit": "Powiązana wizyta (opcjonalnie)",
            "kind": "Rodzaj dokumentu",
            "agreement": "Umowa (opcjonalnie)",
        }

    def __init__(self, *args, doctor, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["patient"].queryset = Pacjent.objects.filter(doctor=doctor)
        patient_id = (
            self.data.get("patient") if self.is_bound else self.initial.get("patient")
        )
        try:
            patient_id = int(patient_id)
        except (TypeError, ValueError):
            patient_id = None
        self.fields["visit"].queryset = Wizyta.objects.filter(
            doctor=doctor, patient_id=patient_id, status="zakonczona"
        ).select_related("patient")
        self.fields["visit"].empty_label = "Brak powiązanej wizyty"
        self.fields["visit"].help_text = "Zakończone wizyty wybranego pacjenta."
        self.fields["visit"].label_from_instance = (
            lambda v: f"{v.patient} · {timezone.localtime(v.created):%d.%m.%Y} · #{v.pk}"
        )
        today = timezone.localdate()
        self.fields["agreement"].queryset = Umowa.objects.filter(
            doctor=doctor, active=True, valid_from__lte=today, valid_to__gte=today
        )
        selected = self.fields["patient"].queryset.filter(pk=patient_id).first()
        if selected:
            age = (
                today.year
                - selected.birth_date.year
                - (
                    (today.month, today.day)
                    < (selected.birth_date.month, selected.birth_date.day)
                )
            )
            self.initial["patient_name"] = (
                f'{dict(K="Pani", M="Pan").get(selected.sex, "Pacjent")} {selected}, wiek: {age} lat'
            )
            self.initial["patient_pesel"] = selected.pesel
            self.initial["patient_address"] = selected.address
        self.uporzadkuj_pola_dokumentu()
        self.ustaw_wyglad()

    def uporzadkuj_pola_dokumentu(self):
        self.order_fields(
            [
                "kind",
                "agreement",
                "facility_address",
                "facility_phone",
                "patient",
                "patient_name",
                "patient_pesel",
                "patient_address",
                "patient_birth",
                "visit",
                "issued_on",
            ]
        )

    def clean(self):
        data = super().clean()
        if data.get("patient") and not data["patient"].pesel:
            self.add_error(
                "patient",
                "Przed wystawieniem dokumentu uzupełnij PESEL w kartotece pacjenta.",
            )
        if (
            data.get("visit")
            and data.get("patient")
            and data["visit"].patient_id != data["patient"].pk
        ):
            self.add_error("visit", "Wizyta należy do innego pacjenta.")
        agreement = data.get("agreement")
        if agreement:
            if agreement.kind != data.get("kind"):
                self.add_error(
                    "agreement", "Umowa nie obejmuje tego rodzaju dokumentu."
                )
        return data


class FormularzDokumentuMedycznego(FormularzDokumentu):
    def __init__(self, *args, kind, **kwargs):
        self.document_kind = kind
        super().__init__(*args, **kwargs)
        for name in ["title", "content", "reason"]:
            self.fields.pop(name)
        self.initial["kind"] = kind
        self.fields["kind"].required = False
        self.instance.kind = kind
        if kind != "skierowanie":
            self.fields.pop("agreement")
        else:
            self.fields["agreement"].queryset = self.fields[
                "agreement"
            ].queryset.filter(kind="skierowanie")
            self.fields["agreement"].label = "Nazwa pracowni / placówki (umowa)"
            self.fields["agreement"].required = True

        def dodaj_pole_tekstowe(name, label, required=True):
            self.fields[name] = forms.CharField(
                label=label,
                required=required,
                max_length=5000,
                widget=forms.Textarea(attrs={"rows": 2}),
            )

        self.fields["issued_on"] = forms.DateField(
            label="Data wystawienia",
            initial=timezone.localdate,
            disabled=True,
            widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        )
        if kind == "skierowanie":
            self.fields["patient_name"].label = "Pani/Pan — imię i nazwisko, wiek"
            dodaj_pole_tekstowe("facility_address", "Adres placówki")
            dodaj_pole_tekstowe("facility_phone", "Telefon placówki")
            dodaj_pole_tekstowe("diagnosis", "Rozpoznanie")
            dodaj_pole_tekstowe("purpose", "Cel porady")
            dodaj_pole_tekstowe("previous_tests", "Badania dotychczas wykonane")
        else:
            if kind == "zaswiadczenie":
                self.fields["patient_birth"] = forms.CharField(
                    label="Data urodzenia", disabled=True, required=False
                )
                dodaj_pole_tekstowe("diagnosis", "Rozpoznanie")
                dodaj_pole_tekstowe("purpose", "Cel wydania zaświadczenia")
                dodaj_pole_tekstowe("issued_place", "Miejsce wystawienia zaświadczenia")
            else:
                dodaj_pole_tekstowe("destination", "Miejsce — placówka, do której skierowano pacjenta")
                dodaj_pole_tekstowe("procedure", "Rodzaj zabiegu")
                self.fields["procedure_count"] = forms.IntegerField(
                    label="Liczba zabiegów", min_value=1, max_value=10000
                )
                dodaj_pole_tekstowe("medicine", "Nazwa i dawka leku", required=False)
                self.fields["procedure_place"] = forms.ChoiceField(
                    label="Miejsce realizacji zabiegu",
                    choices=[
                        ("office", "W gabinecie"),
                        ("home", "W domu chorego"),
                        ("other", "Innym"),
                    ],
                )
                dodaj_pole_tekstowe(
                    "other_place",
                    "Inne miejsce realizacji (jeśli wybrano „Innym”)",
                    required=False,
                )
        self.uporzadkuj_pola_dokumentu()
        self.ustaw_wyglad()

    def clean(self):
        self.cleaned_data["kind"] = self.document_kind
        data = super().clean()
        if data.get("procedure_place") == "other" and not data.get("other_place"):
            self.add_error("other_place", "Podaj inne miejsce realizacji zabiegu.")
        patient = data.get("patient")
        if patient:
            today = timezone.localdate()
            age = (
                today.year
                - patient.birth_date.year
                - (
                    (today.month, today.day)
                    < (patient.birth_date.month, patient.birth_date.day)
                )
            )
            name = f'{dict(K="Pani", M="Pan").get(patient.sex, "Pacjent")} {patient}, wiek: {age} lat'
            values = {
                "patient_name": name,
                "patient_pesel": patient.pesel,
                "patient_birth": patient.birth_date.strftime("%d.%m.%Y"),
                "issued_on": today.strftime("%d.%m.%Y"),
            }
            lines = []
            for key, field in self.fields.items():
                if key == "agreement" and data.get("agreement"):
                    lines.append(
                        f'Nazwa pracowni / placówki: {data["agreement"].partner}'
                    )
                if key in [
                    "kind",
                    "patient",
                    "visit",
                    "agreement",
                    "eligibility_confirmed",
                ]:
                    continue
                value = values.get(key, data.get(key, ""))
                if key == "procedure_place":
                    value = dict(field.choices).get(value, value)
                if value:
                    lines.append(f"{field.label}: {value}")
            self.instance.title = {
                "skierowanie": "Skierowanie lekarskie",
                "zaswiadczenie": "Zaświadczenie lekarskie",
                "zlecenie_leczenia": "Zlecenie lekarskie",
            }[self.document_kind]
            self.instance.content = "\n\n".join(lines)
            self.instance.reason = data.get("purpose") or data.get("procedure", "")
        return data


class FormularzRecepty(FormularzDokumentu):
    drug_search = forms.CharField(
        label="Wyszukaj lek",
        required=False,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "placeholder": "Wpisz nazwę leku lub substancji…",
            }
        ),
    )
    package_id = forms.IntegerField(widget=forms.HiddenInput)
    quantity = forms.IntegerField(
        label="Liczba opakowań", min_value=1, max_value=100, initial=1
    )
    dosage = forms.CharField(
        label="Dawkowanie", max_length=2000, widget=forms.Textarea(attrs={"rows": 2})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("content")
        self.fields.pop("reason")
        self.fields.pop("title")
        self.initial["kind"] = "recepta"
        self.instance.title = "Recepta"
        self.fields.pop("agreement")
        if self.is_bound:
            from ..models import OpakowanieLeku

            try:
                selected = OpakowanieLeku.objects.select_related("product").get(
                    pk=self.data.get("package_id"), product__active=True
                )
                self.selected_label = f"{selected.product.name} · {selected.product.form} · {selected.product.strength} · {selected.description}"
            except (OpakowanieLeku.DoesNotExist, ValueError, TypeError):
                self.selected_label = ""
        self.uporzadkuj_pola_dokumentu()
        self.ustaw_wyglad()

    def clean(self):
        from ..models import OpakowanieLeku

        self.cleaned_data["kind"] = "recepta"
        data = super().clean()
        if data.get("package_id"):
            try:
                package = OpakowanieLeku.objects.select_related("product").get(
                    pk=data["package_id"], product__active=True
                )
            except OpakowanieLeku.DoesNotExist:
                self.add_error(
                    "drug_search", "Wybierz aktualny lek i opakowanie z podpowiedzi."
                )
            else:
                drug = package.product
                self.instance.content = f'Nazwa preparatu: {drug.name}\nPostać: {drug.form}\nMoc: {drug.strength}\nOpakowanie: {package.description}\nGTIN: {package.gtin}\nLiczba opakowań: {data.get("quantity", "")}\nDawkowanie: {data.get("dosage", "")}'
                self.instance.reason = ""
        else:
            self.add_error("drug_search", "Wybierz lek i opakowanie z podpowiedzi.")
        return data


class FormularzZalecen(FormularzDokumentu):
    current_medicines = forms.CharField(
        label="Przyjmowane leki", required=False, max_length=5000,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    recommended_medicines = forms.CharField(
        label="Zalecane leki", required=False, max_length=5000,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    next_slot = forms.ModelChoiceField(
        label="Data następnej wizyty", queryset=None, required=False,
        empty_label="Nie umawiaj kolejnej wizyty",
        help_text="Wybierz wolny termin. Zapisanie dokumentu zarezerwuje go dla pacjenta.",
    )
    other = forms.CharField(
        label="Inne", required=False, max_length=5000,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, doctor, **kwargs):
        super().__init__(*args, doctor=doctor, **kwargs)
        from ..views.wspolne import wolne_terminy

        for name in ["title", "content", "reason", "agreement"]:
            self.fields.pop(name)
        self.fields["next_slot"].queryset = wolne_terminy().filter(doctor=doctor)
        self.fields["next_slot"].label_from_instance = lambda slot: str(slot)
        self.initial["kind"] = "zalecenia"
        self.fields["kind"].required = False
        self.instance.kind = "zalecenia"
        self.instance.title = "Zalecenia"
        self.uporzadkuj_pola_dokumentu()
        self.ustaw_wyglad()

    def clean(self):
        self.cleaned_data["kind"] = "zalecenia"
        data = super().clean()
        if data.get("next_slot") and data.get("patient") and not data["patient"].phone:
            self.add_error("patient", "Przed rezerwacją uzupełnij telefon pacjenta w kartotece.")
        if not any(data.get(name) for name in ["current_medicines", "recommended_medicines", "next_slot", "other"]):
            raise forms.ValidationError("Uzupełnij co najmniej jedno pole zaleceń lub wybierz termin następnej wizyty.")
        self.instance.content = "\n\n".join(
            f"{self.fields[name].label}: {data.get(name) or 'Nie podano'}"
            for name in ["current_medicines", "recommended_medicines", "next_slot", "other"]
        )
        self.instance.reason = ""
        return data

