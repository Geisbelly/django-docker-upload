import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from . import security
from .forms import DocumentoForm
from .models import Documento

# Os primeiros bytes que cada formato precisa ter. Sem isso os arquivos de teste
# seriam recusados pela validacao de conteudo — que e justamente o que se quer.
CABECALHOS = {
    "pdf": b"%PDF-1.4\n",
    "png": b"\x89PNG\r\n\x1a\n",
    "jpg": b"\xff\xd8\xff\xe0",
    "jpeg": b"\xff\xd8\xff\xe0",
    "gif": b"GIF89a",
    "webp": b"RIFF\x00\x00\x00\x00WEBP",
    "docx": b"PK\x03\x04",
    "xlsx": b"PK\x03\x04",
    "odt": b"PK\x03\x04",
    "ods": b"PK\x03\x04",
    "doc": b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",
    "xls": b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",
    "zip": b"PK\x03\x04",
}


def conteudo_de(nome, tamanho):
    extensao = nome.rsplit(".", 1)[-1].lower() if "." in nome else ""
    cabecalho = CABECALHOS.get(extensao, b"conteudo de teste\n")
    return cabecalho + b"x" * max(0, tamanho - len(cabecalho))


def arquivo(nome="relatorio.pdf", tamanho=1024, conteudo=None):
    dados = conteudo if conteudo is not None else conteudo_de(nome, tamanho)
    return SimpleUploadedFile(nome, dados, content_type="application/octet-stream")


class AutenticadoMixin:
    """Enviar arquivo exige login, então o cliente de teste entra antes."""

    def setUp(self):
        super().setUp()
        self.usuario = User.objects.create_user("tester", password="senha-de-teste")
        self.client.force_login(self.usuario)


class MediaTempMixin:
    """Um MEDIA_ROOT novo por teste.

    O banco volta atrás sozinho entre os testes, o disco não: sem isolar,
    um arquivo gravado em um teste faria o Django renomear o do teste seguinte
    para evitar colisão, e o resultado passaria a depender da ordem de execução.
    """

    def setUp(self):
        super().setUp()
        media = tempfile.mkdtemp(prefix="test-media-")
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media)
        override.enable()
        self.addCleanup(override.disable)


class UploadTests(AutenticadoMixin, MediaTempMixin, TestCase):
    """Validação e gravação do upload, sem tocar no /vol/media real."""

    # --- caminho feliz ---

    def test_upload_valido_grava_o_arquivo_e_cria_o_registro(self):
        form = DocumentoForm(
            {"titulo": "Relatório"}, {"arquivo": arquivo("relatorio.pdf")}
        )
        self.assertTrue(form.is_valid(), form.errors)

        documento = form.save()

        self.assertEqual(Documento.objects.count(), 1)
        self.assertTrue(documento.arquivo.name.startswith("uploads/"))
        self.assertEqual(documento.nome_arquivo, "relatorio.pdf")
        self.assertEqual(documento.tamanho, 1024)

    def test_post_na_home_redireciona_e_lista_o_documento(self):
        # follow=True porque a mensagem de sucesso é consumida na primeira
        # renderização depois do redirect
        resposta = self.client.post(
            reverse("home"),
            {"titulo": "Contrato", "arquivo": arquivo("contrato.pdf")},
            follow=True,
        )

        self.assertRedirects(resposta, reverse("home"))
        self.assertContains(resposta, "Contrato")
        self.assertContains(resposta, "enviado com sucesso")

    def test_arquivos_de_mesmo_nome_nao_se_sobrescrevem(self):
        for _ in range(2):
            form = DocumentoForm({"titulo": "Ata"}, {"arquivo": arquivo("ata.pdf")})
            self.assertTrue(form.is_valid(), form.errors)
            form.save()

        nomes = {d.nome_arquivo for d in Documento.objects.all()}
        self.assertEqual(len(nomes), 2, "o storage do Django deve gerar um sufixo")
        self.assertTrue(all(n.endswith(".pdf") for n in nomes))

    def test_extensao_aceita_independe_de_caixa(self):
        form = DocumentoForm({"titulo": "Foto"}, {"arquivo": arquivo("FOTO.PNG")})
        self.assertTrue(form.is_valid(), form.errors)

    # --- validação de extensão ---

    def test_rejeita_extensao_fora_da_lista(self):
        form = DocumentoForm({"titulo": "Script"}, {"arquivo": arquivo("payload.exe")})

        self.assertFalse(form.is_valid())
        self.assertIn("arquivo", form.errors)
        self.assertIn("não é aceita", form.errors["arquivo"][0])
        self.assertEqual(Documento.objects.count(), 0)

    def test_rejeita_html_para_nao_servir_script_no_mesmo_dominio(self):
        form = DocumentoForm({"titulo": "Página"}, {"arquivo": arquivo("x.html")})
        self.assertFalse(form.is_valid())

    def test_rejeita_arquivo_sem_extensao(self):
        form = DocumentoForm({"titulo": "Sem ext"}, {"arquivo": arquivo("arquivo")})

        self.assertFalse(form.is_valid())
        self.assertIn("precisa ter uma extensão", form.errors["arquivo"][0])

    # --- validação de tamanho ---

    @override_settings(UPLOAD_MAX_SIZE_BYTES=2048)
    def test_rejeita_arquivo_acima_do_limite(self):
        form = DocumentoForm(
            {"titulo": "Grande"}, {"arquivo": arquivo("grande.pdf", tamanho=4096)}
        )

        self.assertFalse(form.is_valid())
        self.assertIn("limite", form.errors["arquivo"][0])
        self.assertEqual(Documento.objects.count(), 0)

    @override_settings(UPLOAD_MAX_SIZE_BYTES=2048)
    def test_aceita_arquivo_exatamente_no_limite(self):
        form = DocumentoForm(
            {"titulo": "No limite"}, {"arquivo": arquivo("ok.pdf", tamanho=2048)}
        )
        self.assertTrue(form.is_valid(), form.errors)

    @override_settings(UPLOAD_ALLOWED_EXTENSIONS=["zip"])
    def test_lista_de_extensoes_vem_das_settings_em_tempo_de_execucao(self):
        """Mudar a variável de ambiente vale na hora, sem migração nova."""
        self.assertTrue(
            DocumentoForm({"titulo": "Zip"}, {"arquivo": arquivo("a.zip")}).is_valid()
        )
        self.assertFalse(
            DocumentoForm({"titulo": "Pdf"}, {"arquivo": arquivo("a.pdf")}).is_valid()
        )

    # --- validação do título ---

    def test_rejeita_titulo_so_com_espacos(self):
        form = DocumentoForm({"titulo": "   "}, {"arquivo": arquivo()})

        self.assertFalse(form.is_valid())
        self.assertIn("titulo", form.errors)

    def test_titulo_e_gravado_sem_espacos_nas_pontas(self):
        form = DocumentoForm({"titulo": "  Ata  "}, {"arquivo": arquivo()})

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().titulo, "Ata")

    # --- o model valida mesmo fora do form ---

    def test_full_clean_do_model_tambem_barra_extensao_invalida(self):
        documento = Documento(titulo="Direto", arquivo=arquivo("payload.exe"))

        with self.assertRaises(ValidationError) as ctx:
            documento.full_clean()

        self.assertIn("arquivo", ctx.exception.message_dict)


class HomeTests(AutenticadoMixin, MediaTempMixin, TestCase):
    def test_get_home_responde_com_o_formulario(self):
        resposta = self.client.get(reverse("home"))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'enctype="multipart/form-data"')
        self.assertContains(resposta, "csrfmiddlewaretoken")

    def test_home_sem_documentos_mostra_aviso(self):
        resposta = self.client.get(reverse("home"))
        self.assertContains(resposta, "Nenhum arquivo enviado ainda")


class ConteudoDoArquivoTests(MediaTempMixin, TestCase):
    """A extensão é só o sobrenome: o conteúdo tem de corresponder."""

    def test_rejeita_executavel_renomeado_para_pdf(self):
        # "MZ" é o início de um executável do Windows
        form = DocumentoForm(
            {"titulo": "Disfarçado"},
            {"arquivo": arquivo("relatorio.pdf", conteudo=b"MZ\x90\x00" + b"\x00" * 500)},
        )

        self.assertFalse(form.is_valid())
        self.assertIn("não corresponde à extensão", form.errors["arquivo"][0])
        self.assertEqual(Documento.objects.count(), 0)

    def test_aceita_pdf_de_verdade(self):
        form = DocumentoForm({"titulo": "Real"}, {"arquivo": arquivo("relatorio.pdf")})
        self.assertTrue(form.is_valid(), form.errors)

    def test_rejeita_png_que_nao_e_png(self):
        form = DocumentoForm(
            {"titulo": "Falso"}, {"arquivo": arquivo("foto.png", conteudo=b"%PDF-1.4\n")}
        )
        self.assertFalse(form.is_valid())

    def test_rejeita_txt_com_conteudo_binario(self):
        form = DocumentoForm(
            {"titulo": "Binário"},
            {"arquivo": arquivo("nota.txt", conteudo=b"\x00\x01\x02\x03 binario")},
        )

        self.assertFalse(form.is_valid())
        self.assertIn("binário", form.errors["arquivo"][0])

    def test_rejeita_arquivo_vazio(self):
        form = DocumentoForm({"titulo": "Vazio"}, {"arquivo": arquivo("x.pdf", conteudo=b"")})
        self.assertFalse(form.is_valid())


class NomeDoArquivoTests(MediaTempMixin, TestCase):
    """O nome vai para o disco e para um cabeçalho HTTP — é entrada hostil."""

    def test_caminho_no_nome_nao_escapa_da_pasta(self):
        """Duas camadas: o Django reduz ao basename, e o upload_to fixa a pasta.

        Por isso o formulário aceita — mas o arquivo cai em uploads/ mesmo assim.
        """
        form = DocumentoForm(
            {"titulo": "Traversal"}, {"arquivo": arquivo("../../etc/passwd.pdf")}
        )
        self.assertTrue(form.is_valid(), form.errors)
        documento = form.save()

        self.assertTrue(documento.arquivo.name.startswith("uploads/"))
        self.assertNotIn("..", documento.arquivo.name)
        self.assertEqual(documento.nome_arquivo, "passwd.pdf")

    def test_validador_de_nome_recusa_separador_de_caminho(self):
        """A terceira camada, para quando o nome chega por outro caminho."""
        self.assertIsNotNone(security.nome_de_arquivo_seguro("../../etc/passwd"))
        self.assertIsNotNone(security.nome_de_arquivo_seguro("pasta/nota.pdf"))
        self.assertIsNotNone(security.nome_de_arquivo_seguro("pasta\\nota.pdf"))
        self.assertIsNone(security.nome_de_arquivo_seguro("relatorio.pdf"))

    def test_rejeita_quebra_de_linha_no_nome(self):
        # serviria para injetar cabeçalho na resposta do download
        form = DocumentoForm(
            {"titulo": "Cabeçalho"}, {"arquivo": arquivo("nota\r\nX-Evil: 1.pdf")}
        )
        self.assertFalse(form.is_valid())

    def test_rejeita_caractere_invisivel_no_nome(self):
        # bidi override disfarça a extensão real na interface
        form = DocumentoForm(
            {"titulo": "Invisível"}, {"arquivo": arquivo("nota‮gpj.pdf")}
        )
        self.assertFalse(form.is_valid())

    def test_rejeita_nome_muito_longo(self):
        form = DocumentoForm({"titulo": "Longo"}, {"arquivo": arquivo("a" * 90 + ".pdf")})
        self.assertFalse(form.is_valid())


class TituloTests(AutenticadoMixin, MediaTempMixin, TestCase):
    def test_rejeita_caractere_de_controle_no_titulo(self):
        form = DocumentoForm({"titulo": "Ata\x07\x1b[31m"}, {"arquivo": arquivo()})
        self.assertFalse(form.is_valid())
        self.assertIn("titulo", form.errors)

    def test_titulo_com_sql_e_guardado_literalmente(self):
        """O ORM parametriza: a string entra como dado, nunca como comando."""
        malicioso = "Ata'); DROP TABLE core_documento; --"
        form = DocumentoForm({"titulo": malicioso}, {"arquivo": arquivo()})
        self.assertTrue(form.is_valid(), form.errors)
        documento = form.save()

        self.assertEqual(Documento.objects.get(pk=documento.pk).titulo, malicioso)
        self.assertEqual(Documento.objects.count(), 1)  # a tabela continua de pé

    def test_titulo_com_html_sai_escapado_na_pagina(self):
        form = DocumentoForm({"titulo": "<script>alert(1)</script>"}, {"arquivo": arquivo()})
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        resposta = self.client.get(reverse("home"))
        self.assertNotContains(resposta, "<script>alert(1)</script>")
        self.assertContains(resposta, "&lt;script&gt;")


class ServirMediaTests(AutenticadoMixin, MediaTempMixin, TestCase):
    """Servir conteúdo de usuário é o ponto mais delicado do projeto."""

    def enviar(self, nome="relatorio.pdf"):
        form = DocumentoForm({"titulo": "Doc"}, {"arquivo": arquivo(nome)})
        self.assertTrue(form.is_valid(), form.errors)
        return form.save()

    def test_pdf_baixa_em_vez_de_abrir(self):
        documento = self.enviar("relatorio.pdf")
        resposta = self.client.get(documento.arquivo.url)

        self.assertEqual(resposta.status_code, 200)
        self.assertIn("attachment", resposta["Content-Disposition"])
        self.assertEqual(resposta["Content-Type"], "application/pdf")
        self.assertEqual(resposta["X-Content-Type-Options"], "nosniff")

    def test_imagem_abre_no_navegador(self):
        documento = self.enviar("foto.png")
        resposta = self.client.get(documento.arquivo.url)

        self.assertIn("inline", resposta["Content-Disposition"])
        self.assertEqual(resposta["Content-Type"], "image/png")

    def test_path_traversal_devolve_404(self):
        for caminho in ["/media/../../etc/passwd", "/media/uploads/../../../etc/passwd"]:
            with self.subTest(caminho=caminho):
                self.assertEqual(self.client.get(caminho).status_code, 404)

    def test_extensao_fora_da_lista_no_disco_nao_e_servida(self):
        """Mesmo que um arquivo apareça no volume, só extensão aceita sai."""
        intruso = Path(settings.MEDIA_ROOT) / "uploads" / "intruso.html"
        intruso.parent.mkdir(parents=True, exist_ok=True)
        intruso.write_text("<script>alert(1)</script>")

        self.assertEqual(self.client.get("/media/uploads/intruso.html").status_code, 404)

    def test_arquivo_inexistente_devolve_404(self):
        self.assertEqual(self.client.get("/media/uploads/nao-existe.pdf").status_code, 404)


class CabecalhosTests(AutenticadoMixin, TestCase):
    def test_home_tem_content_security_policy(self):
        resposta = self.client.get(reverse("home"))
        politica = resposta["Content-Security-Policy"]

        self.assertIn("default-src 'self'", politica)
        self.assertIn("object-src 'none'", politica)
        self.assertIn("frame-ancestors 'none'", politica)

    def test_home_tem_nosniff_e_antiframe(self):
        resposta = self.client.get(reverse("home"))
        self.assertEqual(resposta["X-Content-Type-Options"], "nosniff")
        self.assertEqual(resposta["X-Frame-Options"], "DENY")

    def test_admin_fica_fora_da_csp(self):
        """O admin usa script e estilo embutidos; a política o quebraria."""
        resposta = self.client.get("/admin/", follow=True)
        self.assertNotIn("Content-Security-Policy", resposta)


class AutenticacaoTests(MediaTempMixin, TestCase):
    """Sem sessão não se envia, não se lista e não se baixa."""

    def setUp(self):
        super().setUp()
        self.usuario = User.objects.create_user("tester", password="senha-de-teste")

    def test_anonimo_e_mandado_para_o_login(self):
        resposta = self.client.get(reverse("home"))

        self.assertEqual(resposta.status_code, 302)
        self.assertIn(reverse("login"), resposta["Location"])

    def test_anonimo_nao_consegue_enviar(self):
        resposta = self.client.post(
            reverse("home"), {"titulo": "Invasor", "arquivo": arquivo("x.pdf")}
        )

        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(Documento.objects.count(), 0)

    def test_anonimo_nao_baixa_arquivo_de_outra_pessoa(self):
        self.client.force_login(self.usuario)
        form = DocumentoForm({"titulo": "Privado"}, {"arquivo": arquivo("segredo.pdf")})
        self.assertTrue(form.is_valid(), form.errors)
        documento = form.save()
        self.client.logout()

        resposta = self.client.get(documento.arquivo.url)

        self.assertEqual(resposta.status_code, 302)
        self.assertIn(reverse("login"), resposta["Location"])

    def test_upload_guarda_quem_enviou(self):
        self.client.force_login(self.usuario)

        self.client.post(
            reverse("home"),
            {"titulo": "Com dono", "arquivo": arquivo("relatorio.pdf")},
            follow=True,
        )

        documento = Documento.objects.get()
        self.assertEqual(documento.enviado_por, self.usuario)

    def test_pagina_de_login_responde(self):
        resposta = self.client.get(reverse("login"))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "csrfmiddlewaretoken")
