from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import HttpResponse, FileResponse
from io import BytesIO
from django.shortcuts import redirect, get_object_or_404
from django.utils import timezone
from ..models import Termin, Wizyta, Dokument, Zalacznik
from ..formularze import FormularzDokumentu
from ..models import WynikBadania
from ..formularze import FormularzDokumentuMedycznego, FormularzRecepty, FormularzZalecen
from .generowanie import utworz_pdf
from .zapis import zapisz_dokument

from ..views.wspolne import tylko_lekarz, wyswietl_strone

@tylko_lekarz
def wystaw_dokument(request):
    initial = {
        key: request.GET[key]
        for key in ["patient", "visit", "kind"]
        if request.GET.get(key)
    }
    kind = request.GET.get("kind") or request.POST.get("kind", "")
    if kind and kind not in dict(Dokument.RODZAJE):
        return HttpResponse("Ten rodzaj dokumentu nie jest dostępny.", status=400)
    structured = kind in ["skierowanie", "zaswiadczenie", "zlecenie_leczenia"]
    form = (
        FormularzDokumentuMedycznego(
            request.POST or None, initial=initial, doctor=request.user, kind=kind
        )
        if structured
        else FormularzDokumentu(request.POST or None, initial=initial, doctor=request.user)
    )
    if kind == "recepta":
        form = FormularzRecepty(
            request.POST or None, initial=initial, doctor=request.user
        )
    elif kind == "zalecenia":
        form = FormularzZalecen(
            request.POST or None, initial=initial, doctor=request.user
        )
    today = timezone.localdate()
    patient_data = {
        str(p.pk): {
            "name": str(p),
            "pesel": p.pesel,
            "birth": p.birth_date.strftime("%d.%m.%Y"),
            "address": p.address,
            "display": f'{dict(K="Pani", M="Pan").get(p.sex, "Pacjent")} {p}, wiek: {today.year-p.birth_date.year-((today.month,today.day)<(p.birth_date.month,p.birth_date.day))} lat',
        }
        for p in form.fields["patient"].queryset
    }
    for v in Wizyta.objects.filter(doctor=request.user, status="zakonczona").order_by(
        "-created"
    ):
        if str(v.patient_id) in patient_data:
            patient_data[str(v.patient_id)].setdefault("visits", []).append(
                {
                    "id": v.pk,
                    "label": f"{timezone.localtime(v.created):%d.%m.%Y} · #{v.pk}",
                }
            )
    facility_data = (
        {
            str(a.pk): {"address": a.address, "phone": a.phone}
            for a in form.fields["agreement"].queryset
        }
        if "agreement" in form.fields
        else {}
    )

    if request.method == "POST" and form.is_valid():
        try:
            document = zapisz_dokument(form, request.user)
        except (ValidationError, IntegrityError, Termin.DoesNotExist):
            form.add_error("next_slot", "Termin jest już niedostępny. Wybierz inny termin i zapisz ponownie.")
        else:
            messages.success(request, "Dokument został zapisany. Możesz pobrać PDF.")
            return redirect("document", pk=document.pk)
    return wyswietl_strone(
        request,
        "document_form",
        document_form=True,
        patient_data=patient_data,
        facility_data=facility_data,
        structured=structured,
        document_kind=kind,
        title="Wystaw dokument",
        subtitle="Wybierz rodzaj dokumentu i pacjenta.",
        nav="documents",
        form=form,
        button="Zapisz dokument",
    )


@tylko_lekarz
def dokumenty(request):
    items = Dokument.objects.filter(doctor=request.user).select_related("patient")
    kind = request.GET.get("kind")
    if kind in dict(Dokument.RODZAJE):
        items = items.filter(kind=kind)
    return wyswietl_strone(
        request,
        "documents",
        title="Dokumenty",
        subtitle="Dokumenty wystawione pacjentom.",
        nav="documents",
        items=Paginator(items, 20).get_page(request.GET.get("page")),
    )


@tylko_lekarz
def szczegoly_dokumentu(request, pk):
    document = get_object_or_404(
        Dokument.objects.select_related("patient"), pk=pk, doctor=request.user
    )
    return wyswietl_strone(
        request,
        "document",
        title=document.get_kind_display(),
        subtitle=f"Dokument DOK/{document.pk:05d}",
        nav="documents",
        document=document,
    )


@tylko_lekarz
def pobierz_dokument_pdf(request, pk):
    doc = get_object_or_404(Dokument, pk=pk, doctor=request.user)
    sections = [
        (
            "Data wystawienia",
            timezone.localtime(doc.created).strftime("%d.%m.%Y %H:%M"),
        ),
        ("Data urodzenia", doc.snapshot["birth_date"]),
        ("PESEL", doc.snapshot.get("pesel") or "Nie zapisano przy wystawieniu"),
        (
            "Adres zamieszkania",
            doc.snapshot.get("address") or "Nie zapisano przy wystawieniu",
        ),
        (doc.title, doc.content),
    ]
    if doc.reason:
        sections.append(("Uzasadnienie", doc.reason))
    if doc.snapshot.get("agreement"):
        sections.append(
            (
                "Finansowanie",
                f"{doc.snapshot['agreement']}\nZakres: {doc.snapshot.get('scope', '')}",
            )
        )
    response = HttpResponse(
        utworz_pdf(
            doc.get_kind_display(),
            doc.snapshot["patient"],
            doc.snapshot["doctor"],
            sections,
            f"DOK/{doc.pk:05d}",
        ),
        content_type="application/pdf",
    )
    response["Content-Disposition"] = f'attachment; filename="dokument-{doc.pk}.pdf"'
    return response


@tylko_lekarz
def pobierz_wizyte_pdf(request, pk):
    visit = get_object_or_404(
        Wizyta.objects.select_related("patient", "doctor"),
        pk=pk,
        doctor=request.user,
        status="zakonczona",
    )
    sections = [
        ("Data wizyty", timezone.localtime(visit.created).strftime("%d.%m.%Y %H:%M")),
        ("Podsumowanie", visit.summary),
        ("Rozpoznanie lekarza", visit.diagnosis),
        ("Zalecenia", visit.recommendations),
    ]
    response = HttpResponse(
        utworz_pdf(
            "Podsumowanie wizyty",
            str(visit.patient),
            visit.doctor.get_full_name() or visit.doctor.username,
            sections,
            f"WIZYTA/{visit.pk:05d}",
        ),
        content_type="application/pdf",
    )
    response["Content-Disposition"] = f'attachment; filename="wizyta-{visit.pk}.pdf"'
    return response


@tylko_lekarz
def pobierz_zalacznik(request, pk):
    attachment = get_object_or_404(Zalacznik, pk=pk, appointment__doctor=request.user)
    response = FileResponse(
        BytesIO(bytes(attachment.content)),
        as_attachment=True,
        filename=attachment.name,
        content_type=attachment.content_type,
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@tylko_lekarz
def pobierz_wynik_badania(request, pk):
    result = get_object_or_404(WynikBadania, pk=pk, patient__doctor=request.user)
    response = FileResponse(
        BytesIO(bytes(result.content)),
        as_attachment=True,
        filename=result.name,
        content_type="application/pdf",
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response

