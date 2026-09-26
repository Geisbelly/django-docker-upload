import os

from django.conf import settings
from django.db import models

from .security import pode_exibir_inline
from .validators import (
    validate_conteudo_arquivo,
    validate_extensao_arquivo,
    validate_nome_arquivo,
    validate_tamanho_arquivo,
    validate_texto_seguro,
)


def upload_to(instance, filename):
    return os.path.join("uploads", filename)


class Documento(models.Model):
    titulo = models.CharField("titulo", max_length=200, validators=[validate_texto_seguro])
    arquivo = models.FileField(
        "arquivo",
        upload_to=upload_to,
        # a ordem importa: nome e extensao sao baratos e recusam antes de ler
        # qualquer byte; o conteudo so e lido se o resto passou.
        validators=[
            validate_nome_arquivo,
            validate_extensao_arquivo,
            validate_tamanho_arquivo,
            validate_conteudo_arquivo,
        ],
    )
    enviado_em = models.DateTimeField("enviado em", auto_now_add=True)
    # quem enviou. null porque os registros criados antes do login existir nao
    # tem dono; SET_NULL para apagar um usuario nao levar o documento junto.
    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="enviado por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documentos",
    )

    class Meta:
        verbose_name = "documento"
        verbose_name_plural = "documentos"
        ordering = ["-enviado_em"]

    def __str__(self):
        return self.titulo

    @property
    def nome_arquivo(self):
        return os.path.basename(self.arquivo.name)

    @property
    def extensao(self):
        return os.path.splitext(self.arquivo.name)[1].lower().lstrip(".")

    @property
    def e_imagem(self):
        """Se pode aparecer como miniatura na lista, em vez de so um link."""
        return pode_exibir_inline(self.extensao)

    @property
    def tamanho(self):
        try:
            return self.arquivo.size
        except (OSError, ValueError):
            return 0
