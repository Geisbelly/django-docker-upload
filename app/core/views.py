from django.contrib import messages
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .forms import DocumentoForm
from .models import Documento


def home(request):
    if request.method == "POST":
        form = DocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save()
            messages.success(
                request, f"Arquivo de “{documento.titulo}” enviado com sucesso."
            )
            # POST/Redirect/GET: recarregar a pagina nao reenvia o arquivo
            return redirect("home")
        messages.error(request, "Não foi possível enviar. Verifique os campos abaixo.")
    else:
        form = DocumentoForm()

    return render(
        request,
        "core/home.html",
        {"form": form, "documentos": Documento.objects.all()},
    )


def healthz(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok"})
