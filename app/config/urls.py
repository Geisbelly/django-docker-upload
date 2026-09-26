from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from core import views

urlpatterns = [
    path("admin/", admin.site.urls),
    # login e logout prontos do Django; o template fica em
    # core/templates/registration/login.html
    path("accounts/", include("django.contrib.auth.urls")),
    path("", views.home, name="home"),
    path("healthz/", views.healthz, name="healthz"),
]

# O nginx e proxy reverso e nada mais: nao monta volume e nao serve arquivo.
# Entao e a aplicacao que entrega /media/ e /static/, inclusive com DEBUG=0 —
# django.contrib.staticfiles so serve com DEBUG ligado, e MEDIA_URL nunca e
# servido automaticamente.
urlpatterns += [
    # /media/ e conteudo enviado por usuario: vai por uma view propria, que
    # forca download, fixa o Content-Type e barra path traversal.
    re_path(r"^media/(?P<caminho>.*)$", views.servir_media, name="media"),
    # /static/ e conteudo meu, gerado pelo collectstatic a partir da imagem.
    re_path(
        r"^static/(?P<path>.*)$",
        serve,
        {"document_root": settings.STATIC_ROOT},
        name="static",
    ),
]
