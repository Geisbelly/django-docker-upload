import os

from django.db import models

from .validators import validate_extensao_arquivo, validate_tamanho_arquivo


def upload_to(instance, filename):
    return os.path.join("uploads", filename)


class Documento(models.Model):
    titulo = models.CharField("titulo", max_length=200)
    arquivo = models.FileField(
        "arquivo",
        upload_to=upload_to,
        validators=[validate_extensao_arquivo, validate_tamanho_arquivo],
    )
    enviado_em = models.DateTimeField("enviado em", auto_now_add=True)

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
    def tamanho(self):
        try:
            return self.arquivo.size
        except (OSError, ValueError):
            return 0
