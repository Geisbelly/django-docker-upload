from django import forms
from django.conf import settings
from django.template.defaultfilters import filesizeformat

from .models import Documento


class DocumentoForm(forms.ModelForm):
    class Meta:
        model = Documento
        fields = ["titulo", "arquivo"]
        widgets = {
            "titulo": forms.TextInput(
                attrs={"placeholder": "Ex.: relatório do primeiro semestre"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        extensoes = [e.lower() for e in settings.UPLOAD_ALLOWED_EXTENSIONS]

        # o accept e conveniencia do navegador; quem decide sao os validadores
        # do model, que rodam no servidor via ModelForm._post_clean()
        self.fields["arquivo"].widget.attrs["accept"] = ",".join(
            f".{e}" for e in extensoes
        )
        self.fields["arquivo"].help_text = (
            f"Até {filesizeformat(settings.UPLOAD_MAX_SIZE_BYTES)}. "
            f"Formatos aceitos: {', '.join(extensoes)}."
        )

    # o titulo nao precisa de clean_titulo(): forms.CharField ja usa strip=True,
    # entao um titulo so de espacos vira "" e cai na validacao de obrigatorio
