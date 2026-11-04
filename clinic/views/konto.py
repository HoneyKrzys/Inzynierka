from django.contrib.auth.views import LoginView, PasswordChangeView
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.decorators.http import require_safe
from ..models import Zdarzenie

from .wspolne import tylko_lekarz, wyswietl_strone, czy_przekroczono_limit

class LogowanieLekarza(LoginView):
    template_name = "clinic/login.html"
    redirect_authenticated_user = True

    def post(self, request, *args, **kwargs):
        if czy_przekroczono_limit(request, "login", 30):
            return HttpResponse(
                "Zbyt wiele prób. Spróbuj ponownie za 10 minut.", status=429
            )
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        if not form.get_user().is_staff:
            form.add_error(None, "To konto nie ma uprawnień lekarza.")
            return self.form_invalid(form)
        return super().form_valid(form)


class ZmianaHasla(PasswordChangeView):
    template_name = "clinic/form.html"
    success_url = reverse_lazy("dashboard")
    extra_context = {
        "title": "Zmień hasło",
        "subtitle": "Bezpieczeństwo konta",
        "nav": "settings",
        "button": "Zapisz nowe hasło",
    }


@tylko_lekarz
@require_safe
def ustawienia_konta(request):
    return wyswietl_strone(
        request,
        "settings",
        title="Konto lekarza",
        subtitle="Profil i historia działań.",
        nav="settings",
        events=Zdarzenie.objects.filter(doctor=request.user)[:40],
    )

