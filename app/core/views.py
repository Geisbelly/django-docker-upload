from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render

from .models import Documento


def home(request):
    return render(request, "core/home.html", {"documentos": Documento.objects.all()})


def healthz(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok"})
