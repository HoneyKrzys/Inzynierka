from django import forms
from ..models import Material
from .pola import StylFormularza


class FormularzMaterialu(StylFormularza, forms.ModelForm):
    file = forms.FileField(
        label="Plik PDF lub TXT (do 2 MB)",
        widget=forms.ClearableFileInput(attrs={"accept": ".pdf,.txt"}),
    )

    class Meta:
        model = Material
        fields = ["title", "author", "edition", "clinical_scope"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ustaw_wyglad()

    def clean_file(self):
        value = self.cleaned_data["file"]
        if value.size > 2 * 1024 * 1024 or not value.name.lower().endswith(
            (".pdf", ".txt")
        ):
            raise forms.ValidationError("Wybierz plik PDF/TXT do 2 MB.")
        return value


class FormularzZakresuMaterialu(forms.ModelForm):
    class Meta:
        model = Material
        fields = ["clinical_scope"]

