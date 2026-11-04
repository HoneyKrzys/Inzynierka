import clinic.pola
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ProduktLeczniczy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rpl_id', models.CharField(db_column='rpl_id', max_length=40, unique=True)),
                ('name', models.TextField(db_column='nazwa', db_index=True)),
                ('form', models.TextField(blank=True, db_column='postac')),
                ('strength', models.TextField(blank=True, db_column='moc')),
                ('substance', models.TextField(blank=True, db_column='substancja')),
                ('source_date', models.DateField(db_column='data_rejestru')),
                ('active', models.BooleanField(db_column='aktywna', default=True)),
            ],
            options={
                'db_table': 'produkty_lecznicze',
                'ordering': ['name', 'strength', 'pk'],
            },
        ),
        migrations.CreateModel(
            name='Material',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('clinical_scope', models.CharField(blank=True, choices=[('', 'Nieokreślony — bez zaleceń AI'), ('przeziebienie', 'Przeziębienie'), ('zapalenie_gardla', 'Wirusowe zapalenie gardła'), ('zapalenie_oskrzeli', 'Ostre zapalenie oskrzeli'), ('stany_nagle', 'Stany nagłe i stany zagrożenia życia'), ('zywienie_ogolne', 'Żywienie ogólne i ocena stanu odżywienia'), ('edukacja_zywieniowa', 'Edukacja żywieniowa i zmiana nawyków'), ('zywienie_neurologia', 'Żywienie w chorobach układu nerwowego'), ('zywienie_endokrynologia', 'Żywienie w chorobach układu hormonalnego'), ('zywienie_hematologia', 'Żywienie w chorobach układu krwiotwórczego'), ('zywienie_kardiologia', 'Żywienie w chorobach sercowo-naczyniowych'), ('zywienie_pulmonologia', 'Żywienie w chorobach układu oddechowego'), ('zywienie_nefrologia', 'Żywienie w chorobach nerek i układu moczowego'), ('zywienie_gastroenterologia', 'Żywienie w chorobach układu pokarmowego'), ('zywienie_narzad_ruchu', 'Żywienie w chorobach kości, mięśni i skóry'), ('niewydolnosc_serca_edukacja', 'Niewydolność serca — edukacja i samokontrola'), ('bezpieczenstwo_lekow', 'Bezpieczeństwo farmakoterapii i koncyliacja lekowa'), ('pomocnicze_wstep', 'Strony wstępne, autorzy i spis treści — materiał pomocniczy'), ('pomocnicze_bibliografia', 'Bibliografia i piśmiennictwo — materiał pomocniczy'), ('pomocnicze_zadania', 'Zadania i odpowiedzi — materiał pomocniczy'), ('pomocnicze_skorowidz', 'Skorowidz rzeczowy — materiał pomocniczy')], db_column='zakres_kliniczny', default='', max_length=30, verbose_name='Zakres kliniczny')),
                ('title', models.CharField(db_column='tytul', max_length=200, verbose_name='Tytuł')),
                ('author', models.CharField(db_column='autor', max_length=180, verbose_name='Autor')),
                ('edition', models.CharField(db_column='wydanie', max_length=80, verbose_name='Rok / wydanie')),
                ('approved', models.BooleanField(db_column='dopuszczony', default=False, verbose_name='Dopuszczone do wyszukiwania')),
                ('embedding_model', models.CharField(blank=True, db_column='model_wektorowy', max_length=100)),
                ('created', models.DateTimeField(auto_now_add=True, db_column='data_utworzenia')),
                ('doctor', models.ForeignKey(db_column='lekarz_id', on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'materialy',
            },
        ),
        migrations.CreateModel(
            name='FragmentMaterialu',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('page', models.PositiveIntegerField(db_column='strona')),
                ('text', models.TextField(db_column='tekst')),
                ('embedding', clinic.pola.DaneSlownikowe(db_column='wektor', default=list)),
                ('source', models.ForeignKey(db_column='material_id', on_delete=django.db.models.deletion.CASCADE, related_name='chunks', to='clinic.material')),
            ],
            options={
                'db_table': 'fragmenty_materialow',
            },
        ),
        migrations.CreateModel(
            name='Pacjent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(db_column='imie', max_length=80, verbose_name='Imię')),
                ('second_name', models.CharField(blank=True, db_column='drugie_imie', max_length=80, verbose_name='Drugie imię')),
                ('last_name', models.CharField(db_column='nazwisko', max_length=100, verbose_name='Nazwisko')),
                ('birth_date', models.DateField(db_column='data_urodzenia', verbose_name='Data urodzenia')),
                ('pesel', models.CharField(db_column='pesel', max_length=11, verbose_name='PESEL')),
                ('sex', models.CharField(choices=[('K', 'Kobieta'), ('M', 'Mężczyzna'), ('N', 'Nie podano')], db_column='plec', default='N', max_length=1, verbose_name='Płeć')),
                ('phone', models.CharField(blank=True, db_column='telefon', max_length=30, verbose_name='Telefon')),
                ('email', models.EmailField(blank=True, db_column='email', max_length=254, verbose_name='E-mail')),
                ('address', models.CharField(blank=True, db_column='adres', max_length=250, verbose_name='Adres')),
                ('created', models.DateTimeField(auto_now_add=True, db_column='data_utworzenia')),
                ('doctor', models.ForeignKey(db_column='lekarz_id', on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'pacjenci',
                'ordering': ['last_name', 'first_name'],
            },
        ),
        migrations.CreateModel(
            name='Termin',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('starts', models.DateTimeField(db_column='poczatek')),
                ('ends', models.DateTimeField(db_column='koniec')),
                ('published', models.BooleanField(db_column='opublikowany', default=True)),
                ('doctor', models.ForeignKey(db_column='lekarz_id', on_delete=django.db.models.deletion.PROTECT, related_query_name='slot', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'terminy',
                'ordering': ['starts'],
            },
        ),
        migrations.CreateModel(
            name='Rezerwacja',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('birth_date', models.DateField(blank=True, db_column='data_urodzenia', null=True, verbose_name='Data urodzenia')),
                ('name', models.CharField(db_column='nazwa', max_length=262, verbose_name='Imię i nazwisko')),
                ('second_name', models.CharField(blank=True, db_column='drugie_imie', max_length=80, verbose_name='Drugie imię')),
                ('address', models.CharField(blank=True, db_column='adres', max_length=250, verbose_name='Adres')),
                ('phone', models.CharField(db_column='telefon', max_length=30, verbose_name='Telefon')),
                ('email', models.EmailField(blank=True, db_column='email', max_length=254, verbose_name='E-mail')),
                ('status', models.CharField(choices=[('zaplanowana', 'Zaplanowana'), ('w_trakcie', 'W trakcie'), ('zakonczona', 'Zakończona'), ('odwolana', 'Odwołana'), ('nieobecnosc', 'Nieobecność')], db_column='status', default='zaplanowana', max_length=12)),
                ('token', models.UUIDField(db_column='token', default=uuid.uuid4, editable=False, unique=True)),
                ('created', models.DateTimeField(auto_now_add=True, db_column='data_utworzenia')),
                ('doctor', models.ForeignKey(db_column='lekarz_id', on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('patient', models.ForeignKey(blank=True, db_column='pacjent_id', null=True, on_delete=django.db.models.deletion.PROTECT, to='clinic.pacjent')),
                ('slot', models.ForeignKey(db_column='termin_id', on_delete=django.db.models.deletion.PROTECT, related_name='appointments', to='clinic.termin')),
            ],
            options={
                'db_table': 'rezerwacje',
                'ordering': ['slot__starts'],
            },
        ),
        migrations.CreateModel(
            name='Umowa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('partner', models.CharField(db_column='placowka', max_length=150, verbose_name='Placówka')),
                ('address', models.CharField(blank=True, db_column='adres', max_length=250, verbose_name='Adres placówki')),
                ('phone', models.CharField(blank=True, db_column='telefon', max_length=30, verbose_name='Telefon placówki')),
                ('number', models.CharField(db_column='numer', max_length=80, verbose_name='Numer umowy')),
                ('kind', models.CharField(choices=[('recepta', 'Leki'), ('skierowanie', 'Badania i konsultacje')], db_column='rodzaj', max_length=20, verbose_name='Zakres')),
                ('services', models.TextField(db_column='swiadczenia', verbose_name='Zakres świadczeń / katalog')),
                ('valid_from', models.DateField(db_column='obowiazuje_od', verbose_name='Obowiązuje od')),
                ('valid_to', models.DateField(db_column='obowiazuje_do', verbose_name='Obowiązuje do')),
                ('subsidy', models.PositiveSmallIntegerField(db_column='doplata', default=0, verbose_name='Dopłata [%]')),
                ('active', models.BooleanField(db_column='aktywna', default=True, verbose_name='Aktywna')),
                ('doctor', models.ForeignKey(db_column='lekarz_id', on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'umowy',
            },
        ),
        migrations.CreateModel(
            name='Wizyta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, db_column='data_utworzenia')),
                ('completed_at', models.DateTimeField(blank=True, db_column='data_zakonczenia', null=True)),
                ('status', models.CharField(choices=[('w_trakcie', 'W trakcie'), ('zakonczona', 'Zakończona')], db_column='status', default='w_trakcie', max_length=12)),
                ('complaint', models.TextField(blank=True, db_column='objawy_ogolne', default='', verbose_name='Objawy ogólne')),
                ('duration', models.CharField(blank=True, db_column='czas_trwania', max_length=200, verbose_name='Czas trwania dolegliwości')),
                ('history', models.TextField(blank=True, db_column='choroby_przewlekle', default='Nie podaje', verbose_name='Choroby przewlekłe')),
                ('medication', models.TextField(blank=True, db_column='dotychczasowe_leczenie', default='Nie podaje', verbose_name='Dotychczasowe leczenie')),
                ('allergies', models.TextField(blank=True, db_column='uczulenia', default='Nie podaje', verbose_name='Uczulenia')),
                ('symptoms', clinic.pola.DaneSlownikowe(blank=True, db_column='objawy', default=dict)),
                ('examination', models.TextField(blank=True, db_column='badanie_przedmiotowe', verbose_name='Badanie przedmiotowe')),
                ('results', models.TextField(blank=True, db_column='wyniki_badan', verbose_name='Wyniki badań — wartości, jednostki, zakresy i data')),
                ('pressure', models.CharField(blank=True, db_column='cisnienie', max_length=20, verbose_name='Ciśnienie [mmHg]')),
                ('pulse', models.PositiveSmallIntegerField(blank=True, db_column='tetno', null=True, verbose_name='Tętno [/min]')),
                ('temperature', models.DecimalField(blank=True, db_column='temperatura', decimal_places=1, max_digits=4, null=True, verbose_name='Temperatura [°C]')),
                ('weight', models.DecimalField(blank=True, db_column='masa', decimal_places=1, max_digits=5, null=True, verbose_name='Masa [kg]')),
                ('height', models.PositiveSmallIntegerField(blank=True, db_column='wzrost', null=True, verbose_name='Wzrost [cm]')),
                ('diagnosis', models.TextField(blank=True, db_column='rozpoznanie', verbose_name='Rozpoznanie lekarza')),
                ('summary', models.TextField(blank=True, db_column='podsumowanie', verbose_name='Podsumowanie do zatwierdzenia')),
                ('recommendations', models.TextField(blank=True, db_column='zalecenia', verbose_name='Zalecenia do zatwierdzenia')),
                ('ai_result', clinic.pola.DaneSlownikowe(blank=True, db_column='odpowiedz_ai', default=dict)),
                ('revision', models.PositiveIntegerField(db_column='wersja', default=0)),
                ('medicines_reviewed', models.BooleanField(db_column='leki_sprawdzone', default=False)),
                ('past_diseases', models.TextField(blank=True, db_column='choroby_przebyte', default='Nie podaje', verbose_name='Choroby przebyte')),
                ('disability', models.TextField(blank=True, db_column='niesprawnosc', default='Nie podaje', verbose_name='Niesprawność / stopień')),
                ('development', models.TextField(blank=True, db_column='wywiad_rozwojowy', default='Nie podaje', verbose_name='Wywiad rozwojowy')),
                ('family_history', models.TextField(blank=True, db_column='wywiad_rodzinny', default='Nie podaje', verbose_name='Wywiad rodzinny')),
                ('hereditary_burden', models.TextField(blank=True, db_column='obciazenia_dziedziczne', default='Nie podaje', verbose_name='Obciążenia dziedziczne')),
                ('hospitalizations', models.TextField(blank=True, db_column='pobyty_w_szpitalu', default='Nie podaje', verbose_name='Pobyty w szpitalu')),
                ('operations', models.TextField(blank=True, db_column='operacje', default='Nie podaje', verbose_name='Zabiegi lub operacje')),
                ('risk_factors', models.TextField(blank=True, db_column='czynniki_ryzyka', default='Nie podaje', verbose_name='Czynniki ryzyka')),
                ('vaccinations', models.TextField(blank=True, db_column='szczepienia', default='Wg kalendarza szczepień', verbose_name='Szczepienia i stosowane surowice')),
                ('addictions', models.TextField(blank=True, db_column='uzaleznienia', default='Nie podaje', verbose_name='Uzależnienia')),
                ('specialist_care', models.TextField(blank=True, db_column='opieka_specjalistyczna', default='Nie podaje', verbose_name='Opieka poradni specjalistycznej')),
                ('general_condition', models.TextField(blank=True, db_column='stan_ogolny', default='Nie podaje', verbose_name='Stan ogólny')),
                ('lymph_nodes', models.TextField(blank=True, db_column='wezly_chlonne', default='Nie podaje', verbose_name='Węzły chłonne')),
                ('head', models.TextField(blank=True, db_column='glowa', default='Nie podaje', verbose_name='Głowa')),
                ('neck', models.TextField(blank=True, db_column='szyja', default='Nie podaje', verbose_name='Szyja')),
                ('upper_airways', models.TextField(blank=True, db_column='gorne_drogi_oddechowe', default='Nie podaje', verbose_name='Górne drogi oddechowe')),
                ('chest', models.TextField(blank=True, db_column='klatka_piersiowa', default='Nie podaje', verbose_name='Klatka piersiowa')),
                ('lower_airways', models.TextField(blank=True, db_column='dolne_drogi_oddechowe', default='Nie podaje', verbose_name='Dolne drogi oddechowe')),
                ('circulation', models.TextField(blank=True, db_column='uklad_krazenia', default='Nie podaje', verbose_name='Układ krążenia')),
                ('abdomen', models.TextField(blank=True, db_column='jama_brzuszna', default='Nie podaje', verbose_name='Narządy jamy brzusznej')),
                ('urinary_system', models.TextField(blank=True, db_column='uklad_moczowy', default='Nie podaje', verbose_name='Układ moczowy')),
                ('musculoskeletal', models.TextField(blank=True, db_column='narzad_ruchu', default='Nie podaje', verbose_name='Narząd ruchu')),
                ('diet', models.TextField(blank=True, db_column='dieta', default='Nie podaje', verbose_name='Dieta')),
                ('appointment', models.OneToOneField(blank=True, db_column='rezerwacja_id', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='visit', to='clinic.rezerwacja')),
                ('doctor', models.ForeignKey(db_column='lekarz_id', on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('patient', models.ForeignKey(db_column='pacjent_id', on_delete=django.db.models.deletion.PROTECT, related_name='visits', to='clinic.pacjent')),
            ],
            options={
                'db_table': 'wizyty',
                'ordering': ['-created'],
            },
        ),
        migrations.CreateModel(
            name='Dokument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('recepta', 'Recepta'), ('skierowanie', 'Skierowanie'), ('zaswiadczenie', 'Zaświadczenie'), ('zalecenia', 'Zalecenia'), ('zlecenie_leczenia', 'Zlecenie lekarskie')], db_column='rodzaj', max_length=20)),
                ('title', models.CharField(db_column='tytul', max_length=180, verbose_name='Tytuł / rodzaj badania')),
                ('content', models.TextField(db_column='tresc', verbose_name='Treść — dla leków podaj nazwę, postać, dawkę, ilość i dawkowanie')),
                ('reason', models.TextField(db_column='uzasadnienie', verbose_name='Uzasadnienie / kontekst wystawienia')),
                ('eligibility_confirmed', models.BooleanField(db_column='uprawnienia_potwierdzone', default=False)),
                ('snapshot', clinic.pola.DaneSlownikowe(db_column='dane_z_chwili_wystawienia', default=dict)),
                ('created', models.DateTimeField(auto_now_add=True, db_column='data_utworzenia')),
                ('doctor', models.ForeignKey(db_column='lekarz_id', on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('patient', models.ForeignKey(db_column='pacjent_id', on_delete=django.db.models.deletion.PROTECT, related_name='documents', to='clinic.pacjent')),
                ('agreement', models.ForeignKey(blank=True, db_column='umowa_id', null=True, on_delete=django.db.models.deletion.PROTECT, to='clinic.umowa')),
                ('visit', models.ForeignKey(blank=True, db_column='wizyta_id', null=True, on_delete=django.db.models.deletion.PROTECT, to='clinic.wizyta')),
            ],
            options={
                'db_table': 'dokumenty',
                'ordering': ['-created'],
            },
        ),
        migrations.CreateModel(
            name='WynikBadania',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_column='nazwa', max_length=255)),
                ('content', models.BinaryField(db_column='tresc')),
                ('created', models.DateTimeField(auto_now_add=True, db_column='data_utworzenia')),
                ('patient', models.ForeignKey(db_column='pacjent_id', on_delete=django.db.models.deletion.CASCADE, related_name='test_results', to='clinic.pacjent')),
            ],
            options={
                'db_table': 'wyniki_badan',
                'ordering': ['-created', '-pk'],
            },
        ),
        migrations.CreateModel(
            name='Zalacznik',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_column='nazwa', max_length=255)),
                ('content_type', models.CharField(db_column='typ_zawartosci', max_length=40)),
                ('content', models.BinaryField(db_column='tresc')),
                ('created', models.DateTimeField(auto_now_add=True, db_column='data_utworzenia')),
                ('appointment', models.ForeignKey(db_column='rezerwacja_id', on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='clinic.rezerwacja')),
            ],
            options={
                'db_table': 'zalaczniki',
            },
        ),
        migrations.CreateModel(
            name='Zdarzenie',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(db_column='czynnosc', max_length=100)),
                ('object_id', models.CharField(db_column='identyfikator_obiektu', max_length=60)),
                ('created', models.DateTimeField(auto_now_add=True, db_column='data_utworzenia')),
                ('doctor', models.ForeignKey(db_column='lekarz_id', on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'zdarzenia',
                'ordering': ['-created'],
            },
        ),
        migrations.CreateModel(
            name='OpakowanieLeku',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rpl_id', models.CharField(db_column='rpl_id', max_length=40)),
                ('description', models.TextField(db_column='opis')),
                ('gtin', models.CharField(blank=True, db_column='gtin', db_index=True, max_length=30)),
                ('availability', models.CharField(blank=True, db_column='dostepnosc', max_length=30)),
                ('product', models.ForeignKey(db_column='produkt_id', on_delete=django.db.models.deletion.CASCADE, related_name='packages', to='clinic.produktleczniczy')),
            ],
            options={
                'db_table': 'opakowania_lekow',
                'constraints': [models.UniqueConstraint(fields=('product', 'rpl_id'), name='unique_rpl_package')],
            },
        ),
        migrations.AddConstraint(
            model_name='termin',
            constraint=models.UniqueConstraint(fields=('doctor', 'starts'), name='unique_doctor_slot'),
        ),
        migrations.AddConstraint(
            model_name='termin',
            constraint=models.CheckConstraint(condition=models.Q(('ends__gt', models.F('starts'))), name='positive_slot'),
        ),
        migrations.AddConstraint(
            model_name='rezerwacja',
            constraint=models.UniqueConstraint(condition=models.Q(('status', 'odwolana'), _negated=True), fields=('slot',), name='one_booking_per_slot'),
        ),
    ]
