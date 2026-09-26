import unicodedata
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.template.defaultfilters import filesizeformat

from . import security

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


def validate_nome_arquivo(arquivo):
    """Recusa nome com caminho, caractere de controle ou invisivel."""
    motivo = security.nome_de_arquivo_seguro(Path(arquivo.name).name)
    if motivo:
        raise ValidationError(motivo, code="nome_inseguro")


def validate_conteudo_arquivo(arquivo):
    """Confere os primeiros bytes contra o que a extensao promete.

    Extensao e so o sobrenome do arquivo: qualquer um renomeia um executavel
    para .pdf. Aqui o conteudo tem de corresponder.
    """
    extensao = Path(arquivo.name).suffix.lower().lstrip(".")
    if not extensao:
        return  # ja recusado por validate_extensao_arquivo

    try:
        arquivo.seek(0)
        cabecalho = arquivo.read(security.TAMANHO_DO_CABECALHO)
    finally:
        arquivo.seek(0)

    if not cabecalho:
        raise ValidationError("O arquivo está vazio.", code="arquivo_vazio")

    if extensao in security.EXTENSOES_DE_TEXTO:
        if security.parece_binario(cabecalho):
            raise ValidationError(
                "O arquivo diz ser .%(extensao)s mas o conteúdo é binário.",
                code="conteudo_nao_confere",
                params={"extensao": extensao},
            )
        return

    if not security.assinatura_confere(extensao, cabecalho):
        raise ValidationError(
            "O conteúdo do arquivo não corresponde à extensão .%(extensao)s.",
            code="conteudo_nao_confere",
            params={"extensao": extensao},
        )


def validate_texto_seguro(valor):
    """Recusa caractere de controle e invisivel no texto digitado."""
    if any(unicodedata.category(c) in {"Cc", "Cf"} for c in valor):
        raise ValidationError(
            "O texto tem caractere de controle ou invisível.",
            code="texto_inseguro",
        )
