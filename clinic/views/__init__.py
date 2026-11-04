from .konto import LogowanieLekarza, ZmianaHasla, ustawienia_konta
from .rezerwacje import strona_glowna, rezerwuj, potwierdzenie_rezerwacji, panel_lekarza, dostepnosc, ukryj_termin, rezerwacja_w_gabinecie, status_rezerwacji, kontynuuj_rezerwacje, rozpocznij_rezerwacje
from .pacjenci import pacjenci, edytuj_pacjenta, karta_pacjenta
from .wizyty import nowa_wizyta, edytuj_wizyte, archiwum
from ..dokumenty.widoki import wystaw_dokument, dokumenty, szczegoly_dokumentu, pobierz_dokument_pdf, pobierz_wizyte_pdf, pobierz_zalacznik, pobierz_wynik_badania
from .materialy import umowy, materialy, szczegoly_materialu, baza_lekow, podpowiedzi_lekow
