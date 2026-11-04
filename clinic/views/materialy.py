from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.http import require_safe
from ..models import Umowa, Material
from ..formularze import FormularzMaterialu, FormularzZakresuMaterialu
from ..services import zapisz_zdarzenie
from .. import ai

from .wspolne import tylko_lekarz, wyswietl_strone

@tylko_lekarz
@require_safe
def umowy(request):
    return wyswietl_strone(
        request,
        "agreements",
        title="Partnerzy i umowy",
        subtitle="Placówki współpracujące i umowy.",
        nav="agreements",
        items=Umowa.objects.filter(doctor=request.user),
    )


@tylko_lekarz
def materialy(request):
    form = FormularzMaterialu(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            parts = ai.odczytaj_material(form.cleaned_data["file"])
            source = form.save(commit=False)
            source.doctor = request.user
            ai.zapisz_fragmenty(source, parts)
            zapisz_zdarzenie(request.user, "Import źródła", source)
            messages.success(
                request,
                "Źródło zaimportowane. Sprawdź odczytany tekst, następnie zatwierdź je do RAG.",
            )
            return redirect("source", pk=source.pk)
        except Exception:
            form.add_error(
                None,
                "Import nie powiódł się. Sprawdź plik (tekstowy PDF/TXT UTF-8, do 100 stron i 120 000 znaków) oraz działanie Ollama i EmbeddingGemma.",
            )
    return wyswietl_strone(
        request,
        "sources",
        title="Baza wiedzy AI",
        subtitle="Twoje materiały, jawne źródła odpowiedzi.",
        nav="sources",
        form=form,
        items=Material.objects.filter(doctor=request.user).order_by("-created"),

    )


@tylko_lekarz
def szczegoly_materialu(request, pk):
    source = get_object_or_404(Material, pk=pk, doctor=request.user)
    scope_form = FormularzZakresuMaterialu(request.POST or None, instance=source)
    if request.method == "POST" and request.POST.get("action") == "scope":
        if scope_form.is_valid():
            scope_form.save()
            messages.success(request, "Zapisano zakres materiału.")
            return redirect("source", pk=pk)
    elif request.method == "POST":
        if source.czy_pomocniczy:
            messages.info(request, "Materiał pomocniczy jest dostępny w bibliotece, ale nie jest źródłem zaleceń AI.")
            return redirect("source", pk=pk)
        source.approved = not source.approved
        source.save(update_fields=["approved"])
        zapisz_zdarzenie(request.user, "Zmiana dopuszczenia źródła", source)
        messages.success(request, "Zmieniono status źródła.")
        return redirect("source", pk=pk)
    return wyswietl_strone(
        request,
        "source",
        title=source.title,
        subtitle=f"{source.author} · {source.edition}",
        nav="sources",
        source=source,
        scope_form=scope_form,
        chunks=Paginator(source.chunks.order_by("id"), 10).get_page(
            request.GET.get("page")
        ),
    )


@tylko_lekarz
@require_safe
def baza_lekow(request):
    from ..models import ProduktLeczniczy

    query = request.GET.get("q", "").strip()[:200]
    products = ProduktLeczniczy.objects.filter(active=True)
    total = products.count()
    source_date = (
        products.order_by("-source_date").values_list("source_date", flat=True).first()
    )
    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(substance__icontains=query)
            | Q(packages__gtin__icontains=query)
        ).distinct()
    items = Paginator(products.prefetch_related("packages"), 25).get_page(
        request.GET.get("page")
    )
    return wyswietl_strone(
        request,
        "drug_database",
        title="Baza leków",
        subtitle="Preparaty dla ludzi z Rejestru Produktów Leczniczych.",
        nav="drugs",
        items=items,
        query=query,
        total=total,
        source_date=source_date,
    )


@tylko_lekarz
@require_safe
def podpowiedzi_lekow(request):
    from django.http import JsonResponse
    from ..models import OpakowanieLeku

    query = request.GET.get("q", "").strip()[:100]
    matches = []
    if len(query) >= 2:
        rows = (
            OpakowanieLeku.objects.filter(product__active=True)
            .filter(
                Q(product__name__icontains=query)
                | Q(product__substance__icontains=query)
                | Q(gtin__icontains=query)
            )
            .select_related("product")
            .order_by("product__name", "product__strength", "pk")[:30]
        )
        matches = [
            {
                "id": p.pk,
                "label": f"{p.product.name} · {p.product.form} · {p.product.strength} · {p.description} · GTIN: {p.gtin}",
            }
            for p in rows
        ]
    response = JsonResponse({"results": matches})
    response["Cache-Control"] = "private, no-store"
    return response

