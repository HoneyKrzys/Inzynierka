from django.contrib.auth.models import AbstractUser


class Uzytkownik(AbstractUser):
    username = AbstractUser._meta.get_field("username").clone()
    username.db_column = "nazwa_uzytkownika"
    password = AbstractUser._meta.get_field("password").clone()
    password.db_column = "haslo"
    first_name = AbstractUser._meta.get_field("first_name").clone()
    first_name.db_column = "imie"
    last_name = AbstractUser._meta.get_field("last_name").clone()
    last_name.db_column = "nazwisko"
    last_login = AbstractUser._meta.get_field("last_login").clone()
    last_login.db_column = "ostatnie_logowanie"
    date_joined = AbstractUser._meta.get_field("date_joined").clone()
    date_joined.db_column = "data_dolaczenia"
    is_staff = AbstractUser._meta.get_field("is_staff").clone()
    is_staff.db_column = "dostep_do_panelu"
    is_active = AbstractUser._meta.get_field("is_active").clone()
    is_active.db_column = "aktywny"
    is_superuser = AbstractUser._meta.get_field("is_superuser").clone()
    is_superuser.db_column = "pelne_uprawnienia"

    class Meta:
        db_table = "konta_uzytkownicy"
        verbose_name = "użytkownik"
        verbose_name_plural = "użytkownicy"
