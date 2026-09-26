from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_safe

from . import security
from .forms import DocumentoForm
from .models import Documento


@login_required
def home(request):
    if request.method == "POST":
        form = DocumentoForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)
            documento.enviado_por = request.user
            documento.save()
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


@login_required
@require_safe
def servir_media(request, caminho):
    """Entrega um arquivo enviado, com as defesas explicitas.

    O nginx e proxy reverso e nao monta volume, entao quem serve /media/ e a
    aplicacao. Servir conteudo de usuario no mesmo dominio e o ponto mais
    delicado do projeto, e por isso aqui nada e adivinhado:

    0. so quem tem sessao valida chega ate aqui (login_required);
    1. o caminho e resolvido e tem de cair dentro de MEDIA_ROOT (path traversal);
    2. a extensao tem de estar na lista aceita, senao e 404;
    3. o Content-Type vem de uma tabela fixa, nunca do conteudo nem do que o
       navegador declarou no upload;
    4. so imagem rasterizada abre no navegador; todo o resto baixa;
    5. nosniff impede o navegador de ignorar o tipo que eu declarei.
    """
    base = Path(settings.MEDIA_ROOT).resolve()
    try:
        alvo = (base / caminho).resolve()
    except (OSError, ValueError):
        raise Http404

    # 1 · nao pode escapar de MEDIA_ROOT
    if base != alvo and base not in alvo.parents:
        raise Http404
    if not alvo.is_file():
        raise Http404

    # 2 · so extensao aceita
    extensao = alvo.suffix.lower().lstrip(".")
    permitidas = [e.lower() for e in settings.UPLOAD_ALLOWED_EXTENSIONS]
    if extensao not in permitidas:
        raise Http404

    # 3, 4 e 5
    inline = security.pode_exibir_inline(extensao)
    resposta = FileResponse(
        alvo.open("rb"),
        as_attachment=not inline,
        filename=alvo.name,
        content_type=security.tipo_de(extensao),
    )
    resposta["X-Content-Type-Options"] = "nosniff"
    return resposta
