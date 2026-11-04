from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from ..models import Pacjent, Rezerwacja, Zalacznik
from ..formularze import FormularzPacjenta
from ..services import zapisz_zdarzenie
from ..models import WynikBadania
from ..formularze import FormularzWynikuBadania

from .wspolne import tylko_lekarz, wyswietl_strone
from .rezerwacje import kontynuuj_rezerwacje

@tylko_lekarz
def pacjenci(request):
    query = request.GET.get("q", "").strip()
    items = Pacjent.objects.filter(doctor=request.user)
    for word in query.split():
        items = items.filter(
            Q(first_name__icontains=word)
            | Q(second_name__icontains=word)
            | Q(last_name__icontains=word)
            | Q(phone__icontains=word)
        )
    return wyswietl_strone(
        request,
        "patients",
        title="Pacjenci",
        subtitle="Kartoteka i historia opieki w jednym miejscu.",
        nav="patients",
        items=Paginator(items, 20).get_page(request.GET.get("page")),
        query=query,
    )


@tylko_lekarz
def edytuj_pacjenta(request, pk=None):
    appointment = (
        get_object_or_404(
            Rezerwacja, pk=request.GET["appointment"], doctor=request.user
        )
        if not pk and request.GET.get("appointment")
        else None
    )
    if appointment:
        if hasattr(appointment, "visit"):
            return redirect("visit", pk=appointment.visit.pk)
        if appointment.patient_id:
            return redirect(f"{reverse('visit_start')}?appointment={appointment.pk}")
        if appointment.status != "zaplanowana":
            messages.error(request, "Rezerwacja nie jest już aktywna.")
            return redirect("dashboard")
    patient = (
        get_object_or_404(Pacjent, pk=pk, doctor=request.user)
        if pk
        else Pacjent(doctor=request.user)
    )
    initial = {}
    if appointment:
        names = appointment.name.strip().split(maxsplit=1)
        last_name = names[1] if len(names) > 1 else ""
        if appointment.second_name and last_name.startswith(
            appointment.second_name + " "
        ):
            last_name = last_name[len(appointment.second_name) + 1 :]
        initial = {
            "first_name": names[0] if names else "",
            "second_name": appointment.second_name,
            "last_name": last_name,
            "phone": appointment.phone,
            "email": appointment.email,
            "birth_date": appointment.birth_date,
            "address": appointment.address,
        }
    form = FormularzPacjenta(request.POST or None, instance=patient, initial=initial)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            if appointment:
                appointment = Rezerwacja.objects.select_for_update().get(
                    pk=appointment.pk
                )
                if appointment.patient_id:
                    return kontynuuj_rezerwacje(request, appointment, appointment.patient)
                if appointment.status != "zaplanowana":
                    messages.error(request, "Rezerwacja nie jest już aktywna.")
                    return redirect("dashboard")
            patient = form.save()
            zapisz_zdarzenie(request.user, "Zapis karty pacjenta", patient)
            if appointment:
                appointment.patient = patient
                appointment.save(update_fields=["patient"])
                return kontynuuj_rezerwacje(request, appointment, patient)
        messages.success(request, "Zapisano dane pacjenta.")
        return redirect("patient", pk=patient.pk)
    return wyswietl_strone(
        request,
        "form",
        title="Edytuj pacjenta" if pk else "Nowy pacjent",
        subtitle=(
            "Sprawdź dane z rezerwacji i uzupełnij datę urodzenia. Imię i nazwisko możesz poprawić."
            if appointment
            else "Dane pacjenta."
        ),
        button="Zapisz i rozpocznij wywiad" if appointment else "Zapisz",
        nav="patients",
        form=form,
    )


@tylko_lekarz
def karta_pacjenta(request, pk):
    patient = get_object_or_404(Pacjent, pk=pk, doctor=request.user)
    result_form = FormularzWynikuBadania(
        request.POST if request.method == "POST" else None,
        request.FILES if request.method == "POST" else None,
    )
    if request.method == "POST" and result_form.is_valid():
        upload = result_form.cleaned_data["result"]
        with transaction.atomic():
            result = WynikBadania.objects.create(
                patient=patient, name=upload.name, content=upload.read()
            )
            zapisz_zdarzenie(request.user, "Dodanie wyniku badania PDF", result)
        messages.success(request, "Wynik badania został dodany do kartoteki.")
        return redirect(reverse("patient", args=[patient.pk]) + "#wyniki-badan")
    visits = patient.visits.all()
    latest = visits.filter(status="zakonczona").first()
    return wyswietl_strone(
        request,
        "patient",
        title=str(patient),
        subtitle="Karta pacjenta",
        nav="patients",
        patient=patient,
        result_form=result_form,
        test_results=patient.test_results.defer("content"),
        visits=visits,
        latest=latest,
        documents=patient.documents.all(),
        attachments=Zalacznik.objects.filter(
            appointment__patient=patient, appointment__doctor=request.user
        ).defer("content"),
    )

