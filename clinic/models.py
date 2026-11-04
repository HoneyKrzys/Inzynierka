from django.db import models
from .pola import DaneSlownikowe
from django.conf import settings
from django.db.models import Q
import uuid


class Pacjent(models.Model):
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="lekarz_id")
    first_name = models.CharField("Imię", max_length=80, db_column="imie")
    second_name = models.CharField("Drugie imię", max_length=80, blank=True, db_column="drugie_imie")
    last_name = models.CharField("Nazwisko", max_length=100, db_column="nazwisko")
    birth_date = models.DateField("Data urodzenia", db_column="data_urodzenia")
    pesel = models.CharField("PESEL", max_length=11, db_column="pesel")
    sex = models.CharField(
        'Płeć',
        max_length=1,
        choices=[('K', 'Kobieta'), ('M', 'Mężczyzna'), ('N', 'Nie podano')],
        default='N',
        db_column='plec',
    )
    phone = models.CharField("Telefon", max_length=30, blank=True, db_column="telefon")
    email = models.EmailField("E-mail", blank=True, db_column="email")
    address = models.CharField("Adres", max_length=250, blank=True, db_column="adres")
    created = models.DateTimeField(auto_now_add=True, db_column="data_utworzenia")

    class Meta:
        db_table = "pacjenci"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return " ".join(
            part for part in [self.first_name, self.second_name, self.last_name] if part
        )


class Termin(models.Model):
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column='lekarz_id',
        related_query_name='slot',
    )
    starts = models.DateTimeField( db_column="poczatek")
    ends = models.DateTimeField( db_column="koniec")
    published = models.BooleanField(default=True, db_column="opublikowany")

    class Meta:
        db_table = "terminy"
        ordering = ["starts"]
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "starts"], name="unique_doctor_slot"
            ),
            models.CheckConstraint(
                condition=Q(ends__gt=models.F("starts")), name="positive_slot"
            ),
        ]

    def __str__(self):
        from django.utils import timezone

        return timezone.localtime(self.starts).strftime("%d.%m.%Y, %H:%M")


class Rezerwacja(models.Model):
    STATUSY = [
        ("zaplanowana", "Zaplanowana"),
        ("w_trakcie", "W trakcie"),
        ("zakonczona", "Zakończona"),
        ("odwolana", "Odwołana"),
        ("nieobecnosc", "Nieobecność"),
    ]
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="lekarz_id")
    slot = models.ForeignKey(
        Termin,
        on_delete=models.PROTECT,
        related_name='appointments',
        db_column='termin_id',
    )
    patient = models.ForeignKey(
        Pacjent,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column='pacjent_id',
    )
    birth_date = models.DateField("Data urodzenia", null=True, blank=True, db_column="data_urodzenia")
    name = models.CharField("Imię i nazwisko", max_length=262, db_column="nazwa")
    second_name = models.CharField("Drugie imię", max_length=80, blank=True, db_column="drugie_imie")
    address = models.CharField("Adres", max_length=250, blank=True, db_column="adres")
    phone = models.CharField("Telefon", max_length=30, db_column="telefon")
    email = models.EmailField("E-mail", blank=True, db_column="email")
    status = models.CharField(max_length=12, choices=STATUSY, default="zaplanowana", db_column="status")
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_column="token")
    created = models.DateTimeField(auto_now_add=True, db_column="data_utworzenia")

    class Meta:
        db_table = "rezerwacje"
        ordering = ["slot__starts"]
        constraints = [
            models.UniqueConstraint(
                fields=["slot"],
                condition=~Q(status="odwolana"),
                name="one_booking_per_slot",
            )
        ]


class Wizyta(models.Model):
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="lekarz_id")
    patient = models.ForeignKey(
        Pacjent,
        on_delete=models.PROTECT,
        related_name='visits',
        db_column='pacjent_id',
    )
    appointment = models.OneToOneField(
        Rezerwacja,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='visit',
        db_column='rezerwacja_id',
    )
    created = models.DateTimeField(auto_now_add=True, db_column="data_utworzenia")
    completed_at = models.DateTimeField(null=True, blank=True, db_column="data_zakonczenia")
    status = models.CharField(
        max_length=12,
        choices=[('w_trakcie', 'W trakcie'), ('zakonczona', 'Zakończona')],
        default='w_trakcie',
        db_column='status',
    )
    complaint = models.TextField("Objawy ogólne", blank=True, default="", db_column="objawy_ogolne")
    duration = models.CharField(
        'Czas trwania dolegliwości',
        max_length=200,
        blank=True,
        db_column='czas_trwania',
    )
    history = models.TextField(
        'Choroby przewlekłe',
        blank=True,
        default='Nie podaje',
        db_column='choroby_przewlekle',
    )
    medication = models.TextField(
        'Dotychczasowe leczenie',
        blank=True,
        default='Nie podaje',
        db_column='dotychczasowe_leczenie',
    )
    allergies = models.TextField("Uczulenia", blank=True, default="Nie podaje", db_column="uczulenia")
    symptoms = DaneSlownikowe(default=dict, blank=True, db_column="objawy")
    examination = models.TextField("Badanie przedmiotowe", blank=True, db_column="badanie_przedmiotowe")
    results = models.TextField(
        'Wyniki badań — wartości, jednostki, zakresy i data',
        blank=True,
        db_column='wyniki_badan',
    )
    pressure = models.CharField("Ciśnienie [mmHg]", max_length=20, blank=True, db_column="cisnienie")
    pulse = models.PositiveSmallIntegerField("Tętno [/min]", null=True, blank=True, db_column="tetno")
    temperature = models.DecimalField(
        'Temperatura [°C]',
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        db_column='temperatura',
    )
    weight = models.DecimalField(
        'Masa [kg]',
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        db_column='masa',
    )
    height = models.PositiveSmallIntegerField("Wzrost [cm]", null=True, blank=True, db_column="wzrost")
    diagnosis = models.TextField("Rozpoznanie lekarza", blank=True, db_column="rozpoznanie")
    summary = models.TextField("Podsumowanie do zatwierdzenia", blank=True, db_column="podsumowanie")
    recommendations = models.TextField("Zalecenia do zatwierdzenia", blank=True, db_column="zalecenia")
    ai_result = DaneSlownikowe(default=dict, blank=True, db_column="odpowiedz_ai")
    revision = models.PositiveIntegerField(default=0, db_column="wersja")
    medicines_reviewed = models.BooleanField(default=False, db_column="leki_sprawdzone")

    past_diseases = models.TextField(
        'Choroby przebyte',
        blank=True,
        default='Nie podaje',
        db_column='choroby_przebyte',
    )
    disability = models.TextField(
        'Niesprawność / stopień',
        blank=True,
        default='Nie podaje',
        db_column='niesprawnosc',
    )
    development = models.TextField(
        'Wywiad rozwojowy',
        blank=True,
        default='Nie podaje',
        db_column='wywiad_rozwojowy',
    )
    family_history = models.TextField(
        'Wywiad rodzinny',
        blank=True,
        default='Nie podaje',
        db_column='wywiad_rodzinny',
    )
    hereditary_burden = models.TextField(
        'Obciążenia dziedziczne',
        blank=True,
        default='Nie podaje',
        db_column='obciazenia_dziedziczne',
    )
    hospitalizations = models.TextField(
        'Pobyty w szpitalu',
        blank=True,
        default='Nie podaje',
        db_column='pobyty_w_szpitalu',
    )
    operations = models.TextField(
        'Zabiegi lub operacje',
        blank=True,
        default='Nie podaje',
        db_column='operacje',
    )
    risk_factors = models.TextField(
        'Czynniki ryzyka',
        blank=True,
        default='Nie podaje',
        db_column='czynniki_ryzyka',
    )
    vaccinations = models.TextField(
        'Szczepienia i stosowane surowice',
        blank=True,
        default='Wg kalendarza szczepień',
        db_column='szczepienia',
    )
    addictions = models.TextField(
        'Uzależnienia',
        blank=True,
        default='Nie podaje',
        db_column='uzaleznienia',
    )
    specialist_care = models.TextField(
        'Opieka poradni specjalistycznej',
        blank=True,
        default='Nie podaje',
        db_column='opieka_specjalistyczna',
    )
    general_condition = models.TextField(
        'Stan ogólny',
        blank=True,
        default='Nie podaje',
        db_column='stan_ogolny',
    )
    lymph_nodes = models.TextField(
        'Węzły chłonne',
        blank=True,
        default='Nie podaje',
        db_column='wezly_chlonne',
    )
    head = models.TextField("Głowa", blank=True, default="Nie podaje", db_column="glowa")
    neck = models.TextField("Szyja", blank=True, default="Nie podaje", db_column="szyja")
    upper_airways = models.TextField(
        'Górne drogi oddechowe',
        blank=True,
        default='Nie podaje',
        db_column='gorne_drogi_oddechowe',
    )
    chest = models.TextField(
        'Klatka piersiowa',
        blank=True,
        default='Nie podaje',
        db_column='klatka_piersiowa',
    )
    lower_airways = models.TextField(
        'Dolne drogi oddechowe',
        blank=True,
        default='Nie podaje',
        db_column='dolne_drogi_oddechowe',
    )
    circulation = models.TextField(
        'Układ krążenia',
        blank=True,
        default='Nie podaje',
        db_column='uklad_krazenia',
    )
    abdomen = models.TextField(
        'Narządy jamy brzusznej',
        blank=True,
        default='Nie podaje',
        db_column='jama_brzuszna',
    )
    urinary_system = models.TextField(
        'Układ moczowy',
        blank=True,
        default='Nie podaje',
        db_column='uklad_moczowy',
    )
    musculoskeletal = models.TextField(
        'Narząd ruchu',
        blank=True,
        default='Nie podaje',
        db_column='narzad_ruchu',
    )
    diet = models.TextField("Dieta", blank=True, default="Nie podaje", db_column="dieta")

    class Meta:
        db_table = "wizyty"
        ordering = ["-created"]

    @property
    def bmi(self):
        return (
            round(float(self.weight) / (self.height / 100) ** 2, 1)
            if self.weight and self.height
            else None
        )


class Umowa(models.Model):
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="lekarz_id")
    partner = models.CharField("Placówka", max_length=150, db_column="placowka")
    address = models.CharField("Adres placówki", max_length=250, blank=True, db_column="adres")
    phone = models.CharField("Telefon placówki", max_length=30, blank=True, db_column="telefon")
    number = models.CharField("Numer umowy", max_length=80, db_column="numer")
    kind = models.CharField(
        'Zakres',
        max_length=20,
        choices=[('recepta', 'Leki'), ('skierowanie', 'Badania i konsultacje')],
        db_column='rodzaj',
    )
    services = models.TextField("Zakres świadczeń / katalog", db_column="swiadczenia")
    valid_from = models.DateField("Obowiązuje od", db_column="obowiazuje_od")
    valid_to = models.DateField("Obowiązuje do", db_column="obowiazuje_do")
    subsidy = models.PositiveSmallIntegerField("Dopłata [%]", default=0, db_column="doplata")
    active = models.BooleanField("Aktywna", default=True, db_column="aktywna")

    def __str__(self):
        return f"{self.partner} · {self.number}"

    class Meta:
        db_table = "umowy"


class Dokument(models.Model):
    RODZAJE = [
        ("recepta", "Recepta"),
        ("skierowanie", "Skierowanie"),
        ("zaswiadczenie", "Zaświadczenie"),
        ("zalecenia", "Zalecenia"),
        ("zlecenie_leczenia", "Zlecenie lekarskie"),
    ]
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="lekarz_id")
    patient = models.ForeignKey(
        Pacjent,
        on_delete=models.PROTECT,
        related_name='documents',
        db_column='pacjent_id',
    )
    visit = models.ForeignKey(
        Wizyta,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column='wizyta_id',
    )
    kind = models.CharField(max_length=20, choices=RODZAJE, db_column="rodzaj")
    title = models.CharField("Tytuł / rodzaj badania", max_length=180, db_column="tytul")
    content = models.TextField(
        'Treść — dla leków podaj nazwę, postać, dawkę, ilość i dawkowanie',
        db_column='tresc',
    )
    reason = models.TextField("Uzasadnienie / kontekst wystawienia", db_column="uzasadnienie")
    agreement = models.ForeignKey(
        Umowa,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column='umowa_id',
    )
    eligibility_confirmed = models.BooleanField(default=False, db_column="uprawnienia_potwierdzone")
    snapshot = DaneSlownikowe(default=dict, db_column="dane_z_chwili_wystawienia")
    created = models.DateTimeField(auto_now_add=True, db_column="data_utworzenia")

    class Meta:
        db_table = "dokumenty"
        ordering = ["-created"]


class Material(models.Model):
    ZAKRESY_KLINICZNE = {
        "przeziebienie": ("Przeziębienie", ["katar", "kichanie", "przeziebienie"]),
        "zapalenie_gardla": ("Wirusowe zapalenie gardła", ["bol gardla", "drapanie w gardle", "zapalenie gardla"]),
        "zapalenie_oskrzeli": ("Ostre zapalenie oskrzeli", ["kaszel", "zapalenie oskrzeli"]),
        "stany_nagle": ("Stany nagłe i stany zagrożenia życia", [
            "stan nagly", "stan zagrozenia zycia", "bol w klatce piersiowej", "ostra dusznosc",
            "omdlenie", "majaczenie", "zaburzenia swiadomosci", "jednostronny obrzek konczyny dolnej",
        ]),
        "zywienie_ogolne": ("Żywienie ogólne i ocena stanu odżywienia", [
            "ocena stanu odzywienia", "oceny stanu odzywienia", "niedozywienie", "niedozywienia",
            "zdrowe odzywianie", "zasady zywienia", "dieta zbilansowana",
        ]),
        "edukacja_zywieniowa": ("Edukacja żywieniowa i zmiana nawyków", [
            "edukacja zywieniowa", "edukacji zywieniowej", "dzienniczek zywieniowy",
            "zmiana nawykow zywieniowych", "zmiany nawykow zywieniowych",
        ]),
        "zywienie_neurologia": ("Żywienie w chorobach układu nerwowego", [
            "zywienie w chorobach ukladu nerwowego", "choroba parkinsona", "choroby parkinsona",
            "choroba alzheimera", "choroby alzheimera", "dysfagia", "dysfagii", "po udarze",
        ]),
        "zywienie_endokrynologia": ("Żywienie w chorobach układu hormonalnego", [
            "cukrzyca", "cukrzycy", "cukrzyce", "niedoczynnosc tarczycy", "niedoczynnosci tarczycy",
            "nadczynnosc tarczycy", "nadczynnosci tarczycy", "zywienie w chorobach hormonalnych",
        ]),
        "zywienie_hematologia": ("Żywienie w chorobach układu krwiotwórczego", [
            "niedokrwistosc", "niedokrwistosci", "anemia", "anemii", "niedobor zelaza",
            "niedoboru zelaza", "niedobor witaminy b12", "niedobor kwasu foliowego",
        ]),
        "zywienie_kardiologia": ("Żywienie w chorobach sercowo-naczyniowych", [
            "nadcisnienie", "nadcisnienia", "miazdzyca", "miazdzycy", "hipercholesterolemia",
            "hipercholesterolemii", "choroba wiencowa", "choroby wiencowej",
            "niewydolnosc serca", "niewydolnosci serca", "dieta dash",
        ]),
        "zywienie_pulmonologia": ("Żywienie w chorobach układu oddechowego", [
            "pochp", "astma", "astmy", "astmie", "przewlekla obturacyjna choroba pluc",
            "zywienie w chorobach pluc",
        ]),
        "zywienie_nefrologia": ("Żywienie w chorobach nerek i układu moczowego", [
            "przewlekla choroba nerek", "przewleklej choroby nerek", "pchn", "niewydolnosc nerek",
            "niewydolnosci nerek", "kamica nerkowa", "kamicy nerkowej", "dieta nerkowa",
        ]),
        "zywienie_gastroenterologia": ("Żywienie w chorobach układu pokarmowego", [
            "refluks", "refluksu", "celiakia", "celiakii", "choroba lesniowskiego crohna",
            "choroby lesniowskiego crohna", "wrzodziejace zapalenie jelita grubego",
            "zaparcia", "zaparciami", "biegunka", "biegunki", "zywienie w chorobach przewodu pokarmowego",
        ]),
        "zywienie_narzad_ruchu": ("Żywienie w chorobach kości, mięśni i skóry", [
            "osteoporoza", "osteoporozy", "osteoporozie", "sarkopenia", "sarkopenii",
            "odlezyny", "odlezyn", "zywienie w chorobach skory",
        ]),
        "niewydolnosc_serca_edukacja": ("Niewydolność serca — edukacja i samokontrola", [
            "niewydolnosc serca", "niewydolnosci serca", "samokontrola w niewydolnosci serca",
        ]),
        "bezpieczenstwo_lekow": ("Bezpieczeństwo farmakoterapii i koncyliacja lekowa", [
            "bezpieczenstwo farmakoterapii", "koncyliacja lekowa", "koncyliacji lekowej",
            "wielolekowosc", "polipragmazja", "polipragmazji", "bledy lekowe", "przeglad lekowy",
            "interakcje lekow",
        ]),
    }
    ZAKRESY_POMOCNICZE = {
        "pomocnicze_wstep": "Strony wstępne, autorzy i spis treści — materiał pomocniczy",
        "pomocnicze_bibliografia": "Bibliografia i piśmiennictwo — materiał pomocniczy",
        "pomocnicze_zadania": "Zadania i odpowiedzi — materiał pomocniczy",
        "pomocnicze_skorowidz": "Skorowidz rzeczowy — materiał pomocniczy",
    }
    DOSTEPNE_ZAKRESY = [("", "Nieokreślony — bez zaleceń AI")] + [
        (key, label) for key, (label, _) in ZAKRESY_KLINICZNE.items()
    ] + list(ZAKRESY_POMOCNICZE.items())
    clinical_scope = models.CharField(
        'Zakres kliniczny',
        max_length=30,
        choices=DOSTEPNE_ZAKRESY,
        blank=True,
        default='',
        db_column='zakres_kliniczny',
    )
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="lekarz_id")
    title = models.CharField("Tytuł", max_length=200, db_column="tytul")
    author = models.CharField("Autor", max_length=180, db_column="autor")
    edition = models.CharField("Rok / wydanie", max_length=80, db_column="wydanie")
    approved = models.BooleanField("Dopuszczone do wyszukiwania", default=False, db_column="dopuszczony")
    embedding_model = models.CharField(max_length=100, blank=True, db_column="model_wektorowy")
    created = models.DateTimeField(auto_now_add=True, db_column="data_utworzenia")

    @property
    def czy_pomocniczy(self):
        return self.clinical_scope in self.ZAKRESY_POMOCNICZE

    class Meta:
        db_table = "materialy"


class FragmentMaterialu(models.Model):
    source = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name='chunks',
        db_column='material_id',
    )
    page = models.PositiveIntegerField( db_column="strona")
    text = models.TextField( db_column="tekst")
    embedding = DaneSlownikowe(default=list, db_column="wektor")

    class Meta:
        db_table = "fragmenty_materialow"


class Zdarzenie(models.Model):
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, db_column="lekarz_id")
    action = models.CharField(max_length=100, db_column="czynnosc")
    object_id = models.CharField(max_length=60, db_column="identyfikator_obiektu")
    created = models.DateTimeField(auto_now_add=True, db_column="data_utworzenia")

    class Meta:
        db_table = "zdarzenia"
        ordering = ["-created"]


class Zalacznik(models.Model):
    appointment = models.ForeignKey(
        Rezerwacja,
        on_delete=models.CASCADE,
        related_name='attachments',
        db_column='rezerwacja_id',
    )
    name = models.CharField(max_length=255, db_column="nazwa")
    content_type = models.CharField(max_length=40, db_column="typ_zawartosci")
    content = models.BinaryField( db_column="tresc")
    created = models.DateTimeField(auto_now_add=True, db_column="data_utworzenia")

    class Meta:
        db_table = "zalaczniki"


class WynikBadania(models.Model):
    patient = models.ForeignKey(
        Pacjent,
        on_delete=models.CASCADE,
        related_name='test_results',
        db_column='pacjent_id',
    )
    name = models.CharField(max_length=255, db_column="nazwa")
    content = models.BinaryField( db_column="tresc")
    created = models.DateTimeField(auto_now_add=True, db_column="data_utworzenia")

    class Meta:
        db_table = "wyniki_badan"
        ordering = ["-created", "-pk"]


class ProduktLeczniczy(models.Model):
    rpl_id = models.CharField(max_length=40, unique=True, db_column="rpl_id")
    name = models.TextField(db_index=True, db_column="nazwa")
    form = models.TextField(blank=True, db_column="postac")
    strength = models.TextField(blank=True, db_column="moc")
    substance = models.TextField(blank=True, db_column="substancja")
    source_date = models.DateField( db_column="data_rejestru")
    active = models.BooleanField(default=True, db_column="aktywna")

    class Meta:
        db_table = "produkty_lecznicze"
        ordering = ["name", "strength", "pk"]


class OpakowanieLeku(models.Model):
    product = models.ForeignKey(
        ProduktLeczniczy,
        on_delete=models.CASCADE,
        related_name='packages',
        db_column='produkt_id',
    )
    rpl_id = models.CharField(max_length=40, db_column="rpl_id")
    description = models.TextField( db_column="opis")
    gtin = models.CharField(max_length=30, blank=True, db_index=True, db_column="gtin")
    availability = models.CharField(max_length=30, blank=True, db_column="dostepnosc")

    class Meta:
        db_table = "opakowania_lekow"
        constraints = [
            models.UniqueConstraint(
                fields=["product", "rpl_id"], name="unique_rpl_package"
            )
        ]
