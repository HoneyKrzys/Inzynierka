from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Exists, OuterRef
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone
from ..models import Termin, Rezerwacja


def tylko_lekarz(view):
    @wraps(view)
    @login_required
    def sprawdz_uprawnienia(request, *args, **kwargs):
        if not request.user.is_staff:
            return HttpResponseForbidden("To konto nie ma dostępu do panelu lekarza.")
        return view(request, *args, **kwargs)

    return sprawdz_uprawnienia


def wyswietl_strone(request, template, **context):
    return render(request, f"clinic/{template}.html", context)


def czy_przekroczono_limit(request, category, limit):
    key = f'{category}:{request.META.get("REMOTE_ADDR", "local")}'
    count = cache.get(key, 0)
    cache.set(key, count + 1, 600)
    return count >= limit


def wolne_terminy():
    occupied = Rezerwacja.objects.filter(slot=OuterRef("pk")).exclude(
        status="odwolana"
    )
    return (
        Termin.objects.filter(
            published=True,
            starts__gt=timezone.now(),
            doctor__is_active=True,
            doctor__is_staff=True,
        )
        .annotate(occupied=Exists(occupied))
        .filter(occupied=False)
    )

