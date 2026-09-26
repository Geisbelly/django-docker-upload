"""Camada de verificacao do conteudo enviado.

O formulario ja recusa extensao fora da lista e arquivo grande demais
(core/validators.py). Aqui fica o que olha o *conteudo* e o *nome*:

- ASSINATURAS: os primeiros bytes que cada formato precisa ter, para pegar um
  executavel renomeado para .pdf;
- nome_de_arquivo_seguro(): recusa caminho, ".." e caractere de controle no nome;
- TIPOS_SEGUROS / EXTENSOES_INLINE: o que o servidor pode devolver, e o que pode
  ser exibido no navegador em vez de baixado.

Nada aqui depende de biblioteca externa: sao comparacoes de bytes.
"""

import re
import unicodedata

# ---------------------------------------------------------------------------
# assinaturas (magic bytes)
# ---------------------------------------------------------------------------

# Cada entrada e uma lista de alternativas; cada alternativa e uma lista de
# pares (deslocamento, bytes esperados). O arquivo passa se bater com uma delas.
ASSINATURAS = {
    "pdf": [[(0, b"%PDF-")]],
    "png": [[(0, b"\x89PNG\r\n\x1a\n")]],
    "jpg": [[(0, b"\xff\xd8\xff")]],
    "jpeg": [[(0, b"\xff\xd8\xff")]],
    "gif": [[(0, b"GIF87a")], [(0, b"GIF89a")]],
    "webp": [[(0, b"RIFF"), (8, b"WEBP")]],
    # OOXML e OpenDocument sao arquivos ZIP
    "docx": [[(0, b"PK\x03\x04")]],
    "xlsx": [[(0, b"PK\x03\x04")]],
    "odt": [[(0, b"PK\x03\x04")]],
    "ods": [[(0, b"PK\x03\x04")]],
    # formatos antigos do Office sao contêineres OLE2
    "doc": [[(0, b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")]],
    "xls": [[(0, b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")]],
}

# Texto nao tem assinatura. Em vez de inventar uma, a regra e negativa: o
# conteudo nao pode ser binario disfarcado.
EXTENSOES_DE_TEXTO = {"txt", "csv"}

# Quantos bytes bastam para decidir.
TAMANHO_DO_CABECALHO = 16


def assinatura_confere(extensao, cabecalho):
    """True se os primeiros bytes correspondem ao que a extensao promete."""
    alternativas = ASSINATURAS.get(extensao)
    if alternativas is None:
        return True  # extensao sem assinatura conhecida: quem decide e o texto
    return any(
        all(cabecalho[desloc : desloc + len(esperado)] == esperado for desloc, esperado in alternativa)
        for alternativa in alternativas
    )


def parece_binario(cabecalho):
    """Heuristica para arquivo de texto: byte nulo ou assinatura binaria conhecida."""
    if b"\x00" in cabecalho:
        return True
    for alternativas in ASSINATURAS.values():
        for alternativa in alternativas:
            if all(
                cabecalho[desloc : desloc + len(esperado)] == esperado
                for desloc, esperado in alternativa
            ):
                return True
    return False


# ---------------------------------------------------------------------------
# nome do arquivo
# ---------------------------------------------------------------------------

# O Django ja usa apenas o basename do que chega, mas a verificacao e explicita
# porque o nome tambem vai para um cabecalho HTTP e para o disco.
NOME_PROIBIDO = re.compile(r"[\x00-\x1f\x7f/\\]")
TAMANHO_MAXIMO_DO_NOME = 80


def nome_de_arquivo_seguro(nome):
    """Devolve o motivo da recusa, ou None se o nome pode ser usado."""
    if not nome:
        return "O arquivo precisa ter um nome."

    # separador de caminho, caractere de controle e quebra de linha (que
    # permitiria injetar cabecalho na resposta do download)
    if NOME_PROIBIDO.search(nome):
        return "O nome do arquivo tem caractere que não é permitido."

    if nome.startswith(".") or ".." in nome:
        return "O nome do arquivo não pode começar com ponto nem conter “..”."

    # caractere invisivel de formatacao (inclui o bidi override, usado para
    # disfarcar a extensao real: "exe.gpj" que aparece como "jpg.exe")
    if any(unicodedata.category(c) in {"Cf", "Cc"} for c in nome):
        return "O nome do arquivo tem caractere invisível."

    if len(nome) > TAMANHO_MAXIMO_DO_NOME:
        return f"O nome do arquivo passa de {TAMANHO_MAXIMO_DO_NOME} caracteres."

    return None


# ---------------------------------------------------------------------------
# o que o servidor devolve
# ---------------------------------------------------------------------------

# O tipo vem desta tabela, nunca de adivinhacao sobre o conteudo e nunca do que
# o navegador declarou no upload.
TIPOS_SEGUROS = {
    "pdf": "application/pdf",
    "txt": "text/plain; charset=utf-8",
    "csv": "text/csv; charset=utf-8",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "odt": "application/vnd.oasis.opendocument.text",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ods": "application/vnd.oasis.opendocument.spreadsheet",
}

# So estas sao exibidas no navegador. Todo o resto baixa, com
# Content-Disposition: attachment. Imagem rasterizada nao executa script;
# svg e html executariam, e por isso nao estao aqui nem na lista de upload.
EXTENSOES_INLINE = {"png", "jpg", "jpeg", "gif", "webp"}


def tipo_de(extensao):
    return TIPOS_SEGUROS.get(extensao, "application/octet-stream")


def pode_exibir_inline(extensao):
    return extensao in EXTENSOES_INLINE
