from django.db import transaction
from ..services import zarezerwuj_termin, zapisz_zdarzenie


def dane_do_dokumentu(pacjent, lekarz, adres, umowa):
    return {
        "patient": str(pacjent),
        "second_name": pacjent.second_name,
        "birth_date": str(pacjent.birth_date),
        "pesel": pacjent.pesel,
        "address": adres,
        "doctor": lekarz.get_full_name() or lekarz.username,
        "agreement": str(umowa) if umowa else "",
        "subsidy": umowa.subsidy if umowa else 0,
        "scope": umowa.services if umowa else "",
    }


@transaction.atomic
def zapisz_dokument(formularz, lekarz):
    dokument = formularz.save(commit=False)
    dokument.doctor = lekarz
    pacjent = dokument.patient
    dokument.snapshot = dane_do_dokumentu(
        pacjent, lekarz, formularz.cleaned_data["patient_address"], dokument.agreement
    )
    termin = formularz.cleaned_data.get("next_slot")
    if termin:
        rezerwacja = zarezerwuj_termin(
            termin.pk,
            {"name": str(pacjent), "phone": pacjent.phone,
             "email": pacjent.email, "address": pacjent.address},
            patient=pacjent,
            doctor=lekarz,
        )
        dokument.snapshot["next_appointment_id"] = rezerwacja.pk
        zapisz_zdarzenie(lekarz, "Rezerwacja kolejnej wizyty z zaleceń", rezerwacja)
    dokument.save()
    zapisz_zdarzenie(lekarz, "Wystawienie dokumentu", dokument)
    return dokument
