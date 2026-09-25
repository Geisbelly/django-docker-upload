from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.template.defaultfilters import filesizeformat

# Os validadores leem as configuracoes na hora da chamada, em vez de receber a
# lista/limite como argumento. Assim a migracao serializa apenas a referencia a
# funcao, e mudar UPLOAD_ALLOWED_EXTENSIONS ou UPLOAD_MAX_SIZE_MB no .env passa a
# valer sem gerar uma migracao nova.


def validate_extensao_arquivo(arquivo):
    """Aceita apenas as extensoes listadas em UPLOAD_ALLOWED_EXTENSIONS."""
    permitidas = [e.lower() for e in settings.UPLOAD_ALLOWED_EXTENSIONS]
    extensao = Path(arquivo.name).suffix.lower().lstrip(".")

    if not extensao:
        raise ValidationError(
            "O arquivo precisa ter uma extensão. Permitidas: %(permitidas)s.",
            code="extensao_ausente",
            params={"permitidas": ", ".join(permitidas)},
        )

    if extensao not in permitidas:
        raise ValidationError(
            "Extensão .%(extensao)s não é aceita. Permitidas: %(permitidas)s.",
            code="extensao_nao_permitida",
            params={"extensao": extensao, "permitidas": ", ".join(permitidas)},
        )


def validate_tamanho_arquivo(arquivo):
    """Recusa arquivos acima de UPLOAD_MAX_SIZE_MB."""
    limite = settings.UPLOAD_MAX_SIZE_BYTES

    if arquivo.size > limite:
        raise ValidationError(
            "O arquivo tem %(tamanho)s e o limite é %(limite)s.",
            code="arquivo_muito_grande",
            params={
                "tamanho": filesizeformat(arquivo.size),
                "limite": filesizeformat(limite),
            },
        )
