from datetime import date, timedelta
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.db.models import Exists, OuterRef, Count
from django.db.models.functions import TruncDate
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from ..models import Pacjent, Termin, Rezerwacja, Wizyta, Zalacznik
from ..formularze import FormularzRezerwacji, FormularzRezerwacjiPacjenta, FormularzDostepnosci
from ..services import zarezerwuj_termin, utworz_terminy, rozpocznij_wizyte, zmien_status_rezerwacji, zakoncz_rezerwacje, zapisz_zdarzenie

from .wspolne import tylko_lekarz, wyswietl_strone, czy_przekroczono_limit, wolne_terminy

def strona_glowna(request):
    doctors = (
        get_user_model()
        .objects.filter(
            is_staff=True,
            is_active=True,
            slot__published=True,
        )
        .distinct()
        .order_by("id")
    )
    selected = (
        (doctors.filter(pk=request.GET.get("doctor")).first() or doctors.first())
        if request.GET.get("doctor", "").isdigit()
        else doctors.first()
    )
    try:
        day = date.fromisoformat(request.GET.get("day", ""))
    except ValueError:
        day = timezone.localdate()
    day = max(
        timezone.localdate(), min(day, timezone.localdate() + timedelta(days=365))
    )
    slots = wolne_terminy().filter(doctor=selected, starts__date=day)
    upcoming = wolne_terminy().filter(doctor=selected).first()
    return wyswietl_strone(
        request,
        "home",
        doctors=doctors,
        selected=selected,
        day=day,
        slots=slots,
        upcoming=upcoming,
        previous_day=day - timedelta(days=1) if day > timezone.localdate() else None,
        next_day=(
            day + timedelta(days=1)
            if day < timezone.localdate() + timedelta(days=365)
            else None
        ),
        days=[
            day + timedelta(days=i)
            for i in range(7)
            if day + timedelta(days=i) <= timezone.localdate() + timedelta(days=365)
        ],
    )


def rezerwuj(request, pk):
    slot = get_object_or_404(Termin.objects.select_related("doctor"), pk=pk)
    form = FormularzRezerwacjiPacjenta(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        if czy_przekroczono_limit(request, "booking", 20):
            form.add_error(None, "Limit rezerwacji. Spróbuj ponownie za 10 minut.")
        else:
            try:
                with transaction.atomic():
                    appointment = zarezerwuj_termin(slot.pk, form.cleaned_data)
                    for upload in form.cleaned_data["attachments"]:
                        Zalacznik.objects.create(
                            appointment=appointment,
                            name=upload.name,
                            content_type=upload.verified_content_type,
                            content=upload.read(),
                        )
                return redirect("booking_confirmation", token=appointment.token)
            except (ValidationError, IntegrityError, Termin.DoesNotExist) as error:
                form.add_error(
                    None,
                    (
                        str(error.message)
                        if isinstance(error, ValidationError)
                        else "Termin jest już niedostępny."
                    ),
                )
    return wyswietl_strone(request, "booking", form=form, slot=slot)


def potwierdzenie_rezerwacji(request, token):
    appointment = get_object_or_404(
        Rezerwacja.objects.select_related("slot"), token=token
    )
    if request.method == "POST":
        if appointment.slot.starts <= timezone.now():
            messages.error(
                request, "Ten termin już się rozpoczął. Skontaktuj się z gabinetem."
            )
        else:
            try:
                zmien_status_rezerwacji(appointment, "odwolana")
                messages.success(request, "Rezerwacja została odwołana.")
            except ValidationError as error:
                messages.error(request, error.message)
        return redirect("booking_confirmation", token=token)
    response = wyswietl_strone(request, "confirmation", appointment=appointment)
    response["Referrer-Policy"] = "no-referrer"
    response["Cache-Control"] = "no-store"
    return response


@tylko_lekarz
def panel_lekarza(request):
    try:
        day = date.fromisoformat(request.GET.get("day", ""))
    except ValueError:
        day = timezone.localdate()
    future_appointments = Rezerwacja.objects.filter(
        doctor=request.user, status="zaplanowana", slot__starts__gt=timezone.now()
    )
    appointments = Rezerwacja.objects.filter(
        doctor=request.user, slot__starts__date=day
    ).select_related("patient", "slot", "visit")
    previous = Wizyta.objects.filter(
        patient=OuterRef("patient_id"), doctor=request.user, status="zakonczona"
    ).exclude(appointment_id=OuterRef("pk"))
    appointments = appointments.annotate(returning=Exists(previous))
    walkins = Wizyta.objects.filter(
        doctor=request.user, appointment__isnull=True, created__date=day
    ).select_related("patient")
    return wyswietl_strone(
        request,
        "dashboard",
        title="Harmonogram wizyt",
        subtitle="Twój gabinet, spokojnie zaplanowany.",
        nav="dashboard",
        day=day,
        appointments=appointments,
        appointment_days=(
            future_appointments
            .annotate(day=TruncDate("slot__starts"))
            .values("day")
            .annotate(total=Count("pk"))
            .order_by("-day")
        ),
        count=appointments.exclude(status="odwolana").count() + walkins.count(),
        completed=appointments.filter(status="zakonczona").count() + walkins.filter(status="zakonczona").count(),
        walkins=walkins,
        patients_count=Pacjent.objects.filter(doctor=request.user).count(),
        drafts=Wizyta.objects.filter(doctor=request.user, status="w_trakcie").select_related(
            "patient"
        )[:5],
    )


@tylko_lekarz
def dostepnosc(request):
    form = FormularzDostepnosci(
        request.POST or None, initial={"day": timezone.localdate() + timedelta(days=1)}
    )
    if request.method == "POST" and form.is_valid():
        count = utworz_terminy(request.user, **form.cleaned_data)
        messages.success(
            request, f"Dodano {count} terminów. Istniejące terminy i kolizje pominięto."
        )
        return redirect("availability")
    slots = Termin.objects.filter(
        doctor=request.user, starts__gte=timezone.now()
    ).annotate(
        occupied=Exists(
            Rezerwacja.objects.filter(slot=OuterRef("pk")).exclude(status="odwolana")
        )
    )[
        :120
    ]
    return wyswietl_strone(
        request,
        "availability",
        title="Dostępność gabinetu",
        subtitle="Publikuj godziny dostępne dla pacjentów.",
        nav="dashboard",
        form=form,
        slots=slots,
    )


@tylko_lekarz
@require_POST
def ukryj_termin(request, pk):
    with transaction.atomic():
        slot = get_object_or_404(
            Termin.objects.select_for_update(), pk=pk, doctor=request.user
        )
        if Rezerwacja.objects.filter(slot=slot).exclude(status="odwolana").exists():
            messages.error(
                request, "Termin ma rezerwację. Najpierw odwołaj ją w harmonogramie."
            )
        else:
            slot.published = not slot.published
            slot.save(update_fields=["published"])
    return redirect("availability")


@tylko_lekarz
def rezerwacja_w_gabinecie(request):
    form = FormularzRezerwacji(request.POST or None)
    patients = Pacjent.objects.filter(doctor=request.user).order_by(
        "last_name", "first_name", "-birth_date", "pk"
    )
    slots = wolne_terminy().filter(doctor=request.user)[:150]
    if request.method == "POST" and form.is_valid():
        patient = (
            get_object_or_404(patients, pk=request.POST["patient"])
            if request.POST.get("patient")
            else None
        )
        slot = get_object_or_404(Termin, pk=request.POST.get("slot"), doctor=request.user)
        try:
            appointment = zarezerwuj_termin(slot.pk, form.cleaned_data, patient, request.user)
            zapisz_zdarzenie(request.user, "Dodanie rezerwacji", appointment)
            messages.success(request, "Wizyta została zaplanowana.")
            return redirect("dashboard")
        except (ValidationError, IntegrityError) as error:
            form.add_error(
                None,
                (
                    error.message
                    if isinstance(error, ValidationError)
                    else "Termin zajęty."
                ),
            )
    return wyswietl_strone(
        request,
        "manual_booking",
        title="Dodaj wizytę",
        subtitle="Rezerwacja w imieniu pacjenta.",
        nav="dashboard",
        form=form,
        patients=patients,
        slots=slots,
    )


@tylko_lekarz
@require_POST
def status_rezerwacji(request, pk):
    appointment = get_object_or_404(Rezerwacja, pk=pk, doctor=request.user)
    try:
        if request.POST.get("status") == "zakonczona":
            current = zakoncz_rezerwacje(appointment, request.POST.get("revision"))
        else:
            current = zmien_status_rezerwacji(appointment, request.POST.get("status"))
        zapisz_zdarzenie(
            request.user, f"Status rezerwacji: {current.get_status_display()}", current
        )
        messages.success(request, "Zmieniono status wizyty.")
    except ValidationError as error:
        messages.error(request, error.message)
        if request.POST.get("status") == "zakonczona" and hasattr(appointment, "visit"):
            return redirect("visit", pk=appointment.visit.pk)
    return redirect(reverse("dashboard") + "?day=" + timezone.localdate(appointment.slot.starts).isoformat())


def kontynuuj_rezerwacje(request, appointment, patient):
    try:
        visit = rozpocznij_wizyte(request.user, patient, appointment)
        return redirect("visit", pk=visit.pk)
    except ValidationError as error:
        messages.warning(request, error.message)
        return redirect(
            f"{reverse('visit_start')}?appointment={appointment.pk}&patient={patient.pk}"
        )


@tylko_lekarz
@require_POST
def rozpocznij_rezerwacje(request, pk):
    appointment = get_object_or_404(Rezerwacja, pk=pk, doctor=request.user)
    if hasattr(appointment, "visit"):
        return redirect("visit", pk=appointment.visit.pk)
    if appointment.status != "zaplanowana":
        messages.error(request, "Ta rezerwacja nie może zostać rozpoczęta.")
        return redirect("dashboard")
    if appointment.patient_id:
        return kontynuuj_rezerwacje(request, appointment, appointment.patient)
    uprosc_tekst = lambda value: " ".join(value.casefold().split())
    from ..formularze import uporzadkuj_telefon

    phone = uporzadkuj_telefon
    booking_names = appointment.name.strip().split(maxsplit=1)
    booking_surname = booking_names[1] if len(booking_names) > 1 else ""
    if appointment.second_name and booking_surname.startswith(
        appointment.second_name + " "
    ):
        booking_surname = booking_surname[len(appointment.second_name) + 1 :]
    primary_name = f"{booking_names[0]} {booking_surname}" if booking_names else ""
    same_name = [
        p
        for p in Pacjent.objects.filter(doctor=request.user)
        if uprosc_tekst(str(p)) == uprosc_tekst(appointment.name)
        or uprosc_tekst(f"{p.first_name} {p.last_name}") == uprosc_tekst(primary_name)
    ]
    matches = [
        p
        for p in same_name
        if appointment.birth_date
        and uprosc_tekst(p.second_name) == uprosc_tekst(appointment.second_name)
        and p.birth_date == appointment.birth_date
        and phone(p.phone)
        and phone(p.phone) == phone(appointment.phone)
        and (
            not appointment.email
            or not p.email
            or uprosc_tekst(p.email) == uprosc_tekst(appointment.email)
        )
    ]
    if len(matches) == 1:
        return kontynuuj_rezerwacje(request, appointment, matches[0])
    if same_name:
        messages.warning(
            request,
            "Dane nie wskazują jednoznacznie pacjenta. Potwierdź jego tożsamość i wybierz właściwą kartę.",
        )
        return redirect(f"{reverse('visit_start')}?appointment={appointment.pk}")
    return redirect(f"{reverse('patient_new')}?appointment={appointment.pk}")

