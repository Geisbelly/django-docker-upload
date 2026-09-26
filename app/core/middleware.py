"""Cabecalhos de seguranca que o Django nao coloca sozinho."""

from django.conf import settings

# O template da home usa <style> embutido, por isso 'unsafe-inline' em style-src.
# script-src fica em 'self' porque a pagina nao tem script nenhum embutido.
POLITICA = "; ".join([
    "default-src 'self'",
    "img-src 'self' data: blob:",   # blob: e a previa do arquivo antes de enviar
    # as fontes do tema vem do Google; a folha e o arquivo da fonte precisam
    # estar liberados explicitamente, senao a CSP bloqueia os dois
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "script-src 'self'",
    "object-src 'none'",          # sem plugin, sem <embed>
    "frame-ancestors 'none'",     # ninguem me coloca em iframe
    "base-uri 'self'",            # <base> nao pode ser reescrito
    "form-action 'self'",         # formulario so posta para o proprio site
])


class ContentSecurityPolicyMiddleware:
    """Aplica CSP fora do admin.

    O admin do Django usa script e estilo embutidos em varias telas, e uma
    politica restritiva o quebraria. Como ele nao recebe conteudo de usuario
    anonimo, fica de fora — e isso esta registrado como limitacao conhecida.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        resposta = self.get_response(request)
        if not request.path.startswith("/admin/"):
            resposta.setdefault("Content-Security-Policy", POLITICA)
        return resposta
