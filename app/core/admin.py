from django.contrib import admin

from .models import Documento


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "nome_arquivo", "enviado_em")
    search_fields = ("titulo",)
    readonly_fields = ("enviado_em",)
