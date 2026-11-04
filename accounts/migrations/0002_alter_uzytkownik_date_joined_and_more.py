import django.contrib.auth.validators
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='uzytkownik',
            name='date_joined',
            field=models.DateTimeField(db_column='data_dolaczenia', default=django.utils.timezone.now, verbose_name='date joined'),
        ),
        migrations.AlterField(
            model_name='uzytkownik',
            name='first_name',
            field=models.CharField(blank=True, db_column='imie', max_length=150, verbose_name='first name'),
        ),
        migrations.AlterField(
            model_name='uzytkownik',
            name='is_active',
            field=models.BooleanField(db_column='aktywny', default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active'),
        ),
        migrations.AlterField(
            model_name='uzytkownik',
            name='is_staff',
            field=models.BooleanField(db_column='dostep_do_panelu', default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status'),
        ),
        migrations.AlterField(
            model_name='uzytkownik',
            name='is_superuser',
            field=models.BooleanField(db_column='pelne_uprawnienia', default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status'),
        ),
        migrations.AlterField(
            model_name='uzytkownik',
            name='last_login',
            field=models.DateTimeField(blank=True, db_column='ostatnie_logowanie', null=True, verbose_name='last login'),
        ),
        migrations.AlterField(
            model_name='uzytkownik',
            name='last_name',
            field=models.CharField(blank=True, db_column='nazwisko', max_length=150, verbose_name='last name'),
        ),
        migrations.AlterField(
            model_name='uzytkownik',
            name='password',
            field=models.CharField(db_column='haslo', max_length=128, verbose_name='password'),
        ),
        migrations.AlterField(
            model_name='uzytkownik',
            name='username',
            field=models.CharField(db_column='nazwa_uzytkownika', error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username'),
        ),
    ]
