from django.contrib import admin
from .models import (
    Pacjent,
    Termin,
    Rezerwacja,
    Wizyta,
    Umowa,
    Dokument,
    Material,
    FragmentMaterialu,
    Zdarzenie,
)

for model in [
    Pacjent,
    Termin,
    Rezerwacja,
    Wizyta,
    Umowa,
    Dokument,
    Material,
    FragmentMaterialu,
    Zdarzenie,
]:
    admin.site.register(model)
