from datetime import date
import json
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, get_object_or_404
from django.utils import timezone
from ..models import Pacjent, Rezerwacja, Wizyta
from ..formularze import FormularzWizyty, ETAPY_WIZYTY
from ..services import rozpocznij_wizyte, zapisz_zdarzenie, dane_dla_asystenta, odcisk_danych
from .. import ai

from .wspolne import tylko_lekarz, wyswietl_strone

@tylko_lekarz
def nowa_wizyta(request):
    appointment = (
        get_object_or_404(
            Rezerwacja, pk=request.GET.get("appointment"), doctor=request.user
        )
        if request.GET.get("appointment")
        else None
    )
    if appointment and hasattr(appointment, "visit"):
        return redirect("visit", pk=appointment.visit.pk)
    if appointment and appointment.status != "zaplanowana":
        messages.info(request, "Ta rezerwacja jest zamknięta. Nowy wywiad rozpocznij jako osobną wizytę.")
        return redirect("dashboard")
    items = Pacjent.objects.filter(doctor=request.user)
    selected = (
        str(appointment.patient_id or request.GET.get("patient", ""))
        if appointment
        else request.GET.get("patient", "")
    )
    if request.method == "POST":
        patient = get_object_or_404(items, pk=request.POST.get("patient"))
        try:
            selected = str(patient.pk)
            visit = rozpocznij_wizyte(
                request.user,
                patient,
                appointment,
                finish_previous=request.POST.get("finish_previous"),
                previous_revision=request.POST.get("previous_revision"),
            )
            if visit is not None:
                return redirect("visit", pk=visit.pk)
            messages.success(
                request,
                "Zatwierdzono wywiad. Pozostały wcześniejsze otwarte wywiady — zatwierdź kolejny, aby przejść do nowej wizyty.",
            )
        except ValidationError as error:
            messages.error(request, error.message)
    candidates = items.order_by("last_name", "first_name", "-birth_date", "pk")
    drafts = list(
        Wizyta.objects.filter(doctor=request.user, status="w_trakcie").select_related(
            "patient"
        )
    )
    return wyswietl_strone(
        request,
        "visit_start",
        drafts=drafts,
        previous=drafts[0] if drafts else None,
        title="Rozpocznij wywiad",
        subtitle="Wybierz pacjenta i potwierdź jego tożsamość.",
        nav="visit",
        patients=candidates,
        selected=selected,
        appointment=appointment,
    )


@tylko_lekarz
def edytuj_wizyte(request, pk):
    visit = get_object_or_404(
        Wizyta.objects.select_related("patient"), pk=pk, doctor=request.user
    )
    action = request.POST.get("action", "save")
    form = FormularzWizyty(instance=visit)
    run_ai = False
    if request.method == "POST":
        with transaction.atomic():
            visit = get_object_or_404(
                Wizyta.objects.select_for_update().select_related("patient"),
                pk=pk,
                doctor=request.user,
            )
            if visit.status == "zakonczona":
                messages.error(request, "Zatwierdzona wizyta jest tylko do odczytu.")
                return redirect("visit", pk=pk)
            before = odcisk_danych(visit)
            form = FormularzWizyty(request.POST, instance=visit)
            if form.is_valid():
                if form.cleaned_data["revision"] != visit.revision:
                    form.add_error(
                        None,
                        "Wizyta zmieniła się w innej karcie. Odśwież stronę przed ponowną edycją.",
                    )
                elif action == "complete" and (
                    form.cleaned_data["complaint"].strip().casefold()
                    in ["", "nie podaje"]
                    or not form.cleaned_data["summary"].strip()
                ):
                    form.add_error(
                        None,
                        "Przed zakończeniem uzupełnij pola „Objawy ogólne” i „Podsumowanie”.",
                    )
                elif action == "ai" and not form.cleaned_data["privacy_checked"]:
                    form.add_error(
                        "privacy_checked",
                        "Najpierw zapisz formularz i sprawdź podgląd danych dla AI.",
                    )
                elif action == "ai" and before != odcisk_danych(visit):
                    form.add_error(
                        None,
                        "Najpierw zapisz zmieniony formularz i sprawdź nowy podgląd AI.",
                    )
                else:
                    after = odcisk_danych(visit)
                    if before != after:
                        visit.ai_result = {}
                    if action == "ai" and before != after:
                        form.add_error(
                            None, "Zmieniono objawy. Zapisz formularz przed analizą AI."
                        )
                    elif action == "accept_ai":
                        if (
                            not visit.ai_result
                            or visit.ai_result.get("fingerprint") != after
                        ):
                            form.add_error(
                                None,
                                "Propozycja jest nieaktualna. Przygotuj ją ponownie.",
                            )
                        else:
                            visit.summary = visit.ai_result["summary"]
                            visit.recommendations = "\n".join(
                                item["text"]
                                for item in visit.ai_result["recommendations"]
                            )
                    if not form.errors:
                        visit.revision += 1
                        if action == "complete":
                            visit.status = "zakonczona"
                            visit.completed_at = timezone.now()
                            if visit.appointment_id:
                                Rezerwacja.objects.filter(
                                    pk=visit.appointment_id
                                ).update(status="zakonczona")
                        visit.save()
                        zapisz_zdarzenie(
                            request.user,
                            (
                                "Zatwierdzenie wizyty"
                                if action == "complete"
                                else "Zapis wywiadu"
                            ),
                            visit,
                        )
                        run_ai = action == "ai"
                        if not run_ai:
                            messages.success(
                                request,
                                (
                                    "Wizyta zakończona. Historia pacjenta została zaktualizowana."
                                    if action == "complete"
                                    else "Zapisano dane wizyty."
                                ),
                            )
                            return redirect("visit", pk=pk)
        if run_ai:
            revision = visit.revision
            try:
                result = ai.przygotuj_propozycje(visit)
                with transaction.atomic():
                    current = Wizyta.objects.select_for_update().get(
                        pk=pk, doctor=request.user
                    )
                    if current.revision != revision or current.status != "w_trakcie":
                        messages.warning(
                            request,
                            "Dane zmieniły się podczas analizy. Wynik AI nie został zapisany.",
                        )
                    else:
                        current.ai_result = result
                        current.revision += 1
                        current.save(update_fields=["ai_result", "revision"])
                        zapisz_zdarzenie(request.user, "Przygotowanie propozycji AI", current)
                        messages.success(
                            request, "Propozycja gotowa. Sprawdź treść i jej źródła."
                        )
            except Exception:
                messages.error(
                    request,
                    "AI nie zwróciło poprawnej odpowiedzi. Sprawdź, czy Ollama działa i modele są pobrane. Dane wizyty są zapisane; możesz pracować ręcznie.",
                )
            return redirect("visit", pk=pk)
    stored = Wizyta.objects.select_related("patient").get(pk=pk)
    return wyswietl_strone(
        request,
        "visit",
        title=f"Wizyta · {visit.patient}",
        subtitle="Wywiad, badanie i plan dalszego postępowania.",
        nav="visit",
        visit=visit,
        form=form,
        stages=[
            {"title": title, "fields": [form[name] for name in names]}
            for title, names in ETAPY_WIZYTY
        ],
        payload=json.dumps(dane_dla_asystenta(stored), ensure_ascii=False, indent=2),
        clinical_fields=[
            form[name]
            for name in form.Meta.fields
            if name not in ["summary", "recommendations", "medicines_reviewed"]
        ],
    )


@tylko_lekarz
def archiwum(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    visits = Wizyta.objects.filter(
        doctor=request.user, status="zakonczona"
    ).select_related("patient")
    appointments = Rezerwacja.objects.filter(doctor=request.user).filter(
        Q(status__in=["odwolana", "nieobecnosc"])
        | Q(status="zakonczona", visit__isnull=True)
    ).select_related("slot", "patient")
    if query:
        visits = visits.filter(
            Q(patient__first_name__icontains=query)
            | Q(patient__second_name__icontains=query)
            | Q(patient__last_name__icontains=query)
        )
        appointments = appointments.filter(name__icontains=query)
    for key, lookup in [("from", "gte"), ("to", "lte")]:
        try:
            value = date.fromisoformat(request.GET.get(key, ""))
            visits = visits.filter(**{f"created__date__{lookup}": value})
            appointments = appointments.filter(
                **{f"slot__starts__date__{lookup}": value}
            )
        except ValueError:
            pass
    if status in ["odwolana", "nieobecnosc"]:
        visits = visits.none()
        appointments = appointments.filter(status=status)
    elif status == "zakonczona":
        appointments = appointments.filter(status="zakonczona")
    return wyswietl_strone(
        request,
        "archive",
        title="Archiwum wizyt",
        subtitle="Historia spotkań i rezerwacji.",
        nav="archive",
        visits=Paginator(visits, 20).get_page(request.GET.get("page")),
        appointments=Paginator(appointments.order_by("-slot__starts"), 20).get_page(
            request.GET.get("appointments_page")
        ),
        query=query,
        status=status,
    )

