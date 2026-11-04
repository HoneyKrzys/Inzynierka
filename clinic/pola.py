from django.db import models


NAZWY = {
    'patient': 'pacjent',
    'second_name': 'drugie_imie',
    'birth_date': 'data_urodzenia',
    'pesel': 'pesel',
    'address': 'adres',
    'doctor': 'lekarz',
    'agreement': 'umowa',
    'subsidy': 'doplata',
    'scope': 'zakres',
    'next_appointment_id': 'numer_kolejnej_rezerwacji',
    'summary': 'podsumowanie',
    'recommendations': 'zalecenia',
    'missing_information': 'brakujace_informacje',
    'evidence': 'zrodla',
    'fingerprint': 'odcisk_danych',
    'evidence_policy': 'zasady_weryfikacji',
    'title': 'tytul',
    'author': 'autor',
    'edition': 'wydanie',
    'page': 'strona',
    'text': 'tekst',
    'sources': 'numery_zrodel',
    'fever': 'goraczka',
    'cough': 'kaszel',
    'breathlessness': 'dusznosc',
    'pain': 'bol',
    'fatigue': 'oslabienie',
}
ODWROTNE_NAZWY = {wartosc: klucz for klucz, wartosc in NAZWY.items()}


def zmien_klucze(dane, slownik):
    if isinstance(dane, dict):
        return {slownik.get(klucz, klucz): zmien_klucze(wartosc, slownik) for klucz, wartosc in dane.items()}
    if isinstance(dane, list):
        return [zmien_klucze(wartosc, slownik) for wartosc in dane]
    return dane


class DaneSlownikowe(models.JSONField):
    def get_db_prep_value(self, value, connection, prepared=False):
        return super().get_db_prep_value(zmien_klucze(value, NAZWY), connection, prepared)

    def from_db_value(self, value, expression, connection):
        return zmien_klucze(super().from_db_value(value, expression, connection), ODWROTNE_NAZWY)
