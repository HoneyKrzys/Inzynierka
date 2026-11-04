import re
from django import forms


class StylFormularza:
    def ustaw_wyglad(self):
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.setdefault("rows", 3)


class WyborWieluPlikow(forms.ClearableFileInput):
    allow_multiple_selected = True


class PolePlikowMedycznych(forms.FileField):
    widget = WyborWieluPlikow

    def clean(self, data, initial=None):
        files = data if isinstance(data, (list, tuple)) else ([data] if data else [])
        if len(files) > 5:
            raise forms.ValidationError("Możesz dołączyć maksymalnie 5 plików.")
        result = []
        for item in files:
            item = super().clean(item, initial)
            if item.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Każdy plik może mieć maksymalnie 5 MB.")
            header = item.read(8)
            item.seek(0)
            ext = item.name.lower().rsplit(".", 1)[-1]
            types = {
                "pdf": ("application/pdf", header.startswith(b"%PDF-")),
                "png": ("image/png", header == b"\x89PNG\r\n\x1a\n"),
                "jpg": ("image/jpeg", header.startswith(b"\xff\xd8\xff")),
                "jpeg": ("image/jpeg", header.startswith(b"\xff\xd8\xff")),
            }
            if ext not in types or not types[ext][1]:
                raise forms.ValidationError(
                    "Dozwolone są pliki PDF, JPG i PNG z poprawnym nagłówkiem."
                )
            item.verified_content_type = types[ext][0]
            result.append(item)
        return result


def uporzadkuj_telefon(value):
    value = re.sub(r"[\s()\-]", "", value)
    if value.startswith("00"):
        value = "+" + value[2:]
    if len(value) == 9 and value.isdigit():
        value = "+48" + value
    if len(value) == 11 and value.startswith("48") and value.isdigit():
        value = "+" + value
    return value


def poczatek_numeru_pesel(birth):
    offsets = {1800: 80, 1900: 0, 2000: 20, 2100: 40, 2200: 60}
    return f"{birth.year%100:02d}{birth.month+offsets[birth.year//100*100]:02d}{birth.day:02d}"


def cyfra_kontrolna_pesel(prefix):
    return str(
        (-sum(int(n) * w for n, w in zip(prefix, [1, 3, 7, 9, 1, 3, 7, 9, 1, 3]))) % 10
    )

