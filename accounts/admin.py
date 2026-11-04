from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Uzytkownik

admin.site.register(Uzytkownik, UserAdmin)
admin.site.site_header = "Medycyna jak dawniej"
admin.site.site_title = "Medycyna jak dawniej"
