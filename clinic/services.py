import hashlib
import json
import re
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .models import Termin, Rezerwacja, Wizyta, Zdarzenie
from .formularze import POLA_WYWIADU


def zapisz_zdarzenie(doctor, action, obj):
    Zdarzenie.objects.create(doctor=doctor, action=action, object_id=str(obj.pk))


@transaction.atomic
def utworz_terminy(doctor, day, start, end, duration):
    get_user_model().objects.select_for_update().get(pk=doctor.pk)
    cursor = timezone.make_aware(datetime.combine(day, start))
    limit = timezone.make_aware(datetime.combine(day, end))
    count = 0
    while cursor + timedelta(minutes=duration) <= limit:
        finish = cursor + timedelta(minutes=duration)
        if (
            cursor > timezone.now()
            and not Termin.objects.filter(
                doctor=doctor, starts__lt=finish, ends__gt=cursor
            ).exists()
        ):
            Termin.objects.create(doctor=doctor, starts=cursor, ends=finish)
            count += 1
        cursor = finish
    return count


@transaction.atomic
def zarezerwuj_termin(slot_id, data, patient=None, doctor=None):
    slot = Termin.objects.select_for_update().select_related("doctor").get(pk=slot_id)
    if doctor is not None and slot.doctor_id != doctor.pk:
        raise ValidationError("Termin należy do innego lekarza.")
    if (
        not slot.published
        or slot.starts <= timezone.now()
        or not slot.doctor.is_active
        or not slot.doctor.is_staff
    ):
        raise ValidationError("Ten termin nie jest już dostępny.")
    if Rezerwacja.objects.filter(slot=slot).exclude(status="odwolana").exists():
        raise ValidationError("Ten termin został już zarezerwowany. Wybierz inny.")
    if patient and patient.doctor_id != slot.doctor_id:
        raise ValidationError("Pacjent należy do innego lekarza.")
    return Rezerwacja.objects.create(
        second_name=patient.second_name if patient else data.get("second_name", ""),
        doctor=slot.doctor,
        slot=slot,
        patient=patient,
        address=data.get("address", patient.address if patient else ""),
        birth_date=patient.birth_date if patient else data.get("birth_date"),
        name=str(patient) if patient else data["name"],
        **{k: data[k] for k in ["phone", "email"]}
    )


@transaction.atomic
def zmien_status_rezerwacji(appointment, status):
    Termin.objects.select_for_update().get(pk=appointment.slot_id)
    current = Rezerwacja.objects.select_for_update().get(pk=appointment.pk)
    if current.status != "zaplanowana":
        raise ValidationError("Można zmienić tylko wizytę zaplanowaną.")
    if status not in ["odwolana", "nieobecnosc"]:
        raise ValidationError("Nieprawidłowa zmiana statusu.")
    if status == "nieobecnosc" and current.slot.starts > timezone.now():
        raise ValidationError("Nieobecność można zaznaczyć po rozpoczęciu terminu.")
    current.status = status
    current.save(update_fields=["status"])
    return current


@transaction.atomic
def zakoncz_rezerwacje(appointment, revision=None):
    get_user_model().objects.select_for_update().get(pk=appointment.doctor_id)
    Termin.objects.select_for_update().get(pk=appointment.slot_id)
    visit = Wizyta.objects.select_for_update().filter(appointment=appointment).first()
    current = Rezerwacja.objects.select_for_update().get(pk=appointment.pk)
    if current.status == "zakonczona":
        return current
    if current.status not in ["zaplanowana", "w_trakcie"]:
        raise ValidationError("Można zakończyć tylko wizytę zaplanowaną lub rozpoczętą.")
    if visit and visit.status != "zakonczona":
        if str(revision) != str(visit.revision):
            raise ValidationError("Wywiad zmienił się w innej karcie. Sprawdź aktualne dane przed zakończeniem.")
        if visit.complaint.strip().casefold() in ["", "nie podaje"] or not visit.summary.strip():
            raise ValidationError("Przed zakończeniem uzupełnij pola „Objawy ogólne” i „Podsumowanie”.")
        visit.status = "zakonczona"
        visit.completed_at = timezone.now()
        visit.revision += 1
        visit.save(update_fields=["status", "completed_at", "revision"])
        zapisz_zdarzenie(current.doctor, "Zatwierdzenie wizyty z harmonogramu", visit)
    current.status = "zakonczona"
    current.save(update_fields=["status"])
    return current


@transaction.atomic
def rozpocznij_wizyte(
    doctor, patient, appointment=None, *, finish_previous=None, previous_revision=None
):
    get_user_model().objects.select_for_update().get(pk=doctor.pk)
    if patient.doctor_id != doctor.pk:
        raise ValidationError("Nieprawidłowy pacjent.")
    if appointment:
        appointment = Rezerwacja.objects.select_for_update().get(
            pk=appointment.pk, doctor=doctor
        )
        existing = Wizyta.objects.filter(appointment=appointment).first()
        if existing:
            return existing
        if appointment.status != "zaplanowana":
            raise ValidationError("Ta rezerwacja nie może zostać rozpoczęta.")
        if appointment.patient_id and appointment.patient_id != patient.pk:
            raise ValidationError("Wybrano pacjenta innego niż w rezerwacji.")
    drafts = list(
        Wizyta.objects.select_for_update().filter(doctor=doctor, status="w_trakcie")
    )
    if drafts:
        previous = drafts[0]
        if str(previous.pk) != str(finish_previous) or str(previous.revision) != str(
            previous_revision
        ):
            raise ValidationError(
                "Poprzedni wywiad nie został zatwierdzony lub zmienił się w innej karcie. Sprawdź komunikat przed przejściem dalej."
            )
        previous.status = "zakonczona"
        previous.completed_at = timezone.now()
        previous.revision += 1
        previous.save(update_fields=["status", "completed_at", "revision"])
        if previous.appointment_id:
            Rezerwacja.objects.filter(pk=previous.appointment_id).update(
                status="zakonczona"
            )
        zapisz_zdarzenie(
            doctor,
            "Zatwierdzenie poprzedniej wizyty przy przejściu do kolejnej",
            previous,
        )
        if len(drafts) > 1:
            return None
    elif finish_previous:
        raise ValidationError(
            "Poprzednia wizyta została już zakończona. Sprawdź aktualny stan i ponów rozpoczęcie."
        )
    if appointment:
        appointment.patient = patient
        appointment.status = "w_trakcie"
        appointment.save(update_fields=["patient", "status"])
    visit = Wizyta.objects.create(
        doctor=doctor, patient=patient, appointment=appointment
    )
    zapisz_zdarzenie(doctor, "Rozpoczęcie wizyty", visit)
    return visit


def dane_dla_asystenta(visit):
    patient = visit.patient
    day = timezone.localdate(visit.created) if visit.created else timezone.localdate()
    age = (
        day.year
        - patient.birth_date.year
        - ((day.month, day.day) < (patient.birth_date.month, patient.birth_date.day))
    )
    payload = {
        "wiek": age,
        "plec": patient.get_sex_display(),
        "weryfikacja_lekow_przez_lekarza": visit.medicines_reviewed,
    }
    for name in POLA_WYWIADU:
        field = Wizyta._meta.get_field(name)
        value = getattr(visit, name)
        if value in ["Nie podaje", "Wg kalendarza szczepień"]:
            value = "Nie ustalono — domyślna treść formularza, nie potwierdzony fakt"
        payload[str(field.verbose_name)] = (
            str(value) if value is not None and value != "" else "Nie ustalono"
        )
    identifiers = [
        patient.first_name,
        patient.second_name,
        patient.last_name,
        patient.phone,
        patient.email,
        patient.address,
        patient.pesel,
    ]

    def usun_dane_osobowe(value):
        if isinstance(value, dict):
            return {key: usun_dane_osobowe(item) for key, item in value.items()}
        if not isinstance(value, str):
            return value
        for identifier in identifiers:
            if identifier and len(identifier.strip()) >= 3:
                value = re.sub(
                    re.escape(identifier.strip()),
                    "[USUNIĘTO]",
                    value,
                    flags=re.IGNORECASE,
                )
        value = re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "[EMAIL]", value)
        value = re.sub(r"(?<!\d)\d{11}(?!\d)", "[IDENTYFIKATOR]", value)
        value = re.sub(r"(?<!\d)(?:\+48[ -]?)?(?:\d[ -]?){9}(?!\d)", "[TELEFON]", value)
        return value

    return usun_dane_osobowe(payload)


def odcisk_danych(visit):
    return hashlib.sha256(
        json.dumps(dane_dla_asystenta(visit), sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
