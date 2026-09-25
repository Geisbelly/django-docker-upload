import shutil
import tempfile

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import DocumentoForm
from .models import Documento

def arquivo(nome="relatorio.pdf", tamanho=1024):
    return SimpleUploadedFile(nome, b"x" * tamanho, content_type="application/pdf")


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


class UploadTests(MediaTempMixin, TestCase):
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


class HomeTests(MediaTempMixin, TestCase):
    def test_get_home_responde_com_o_formulario(self):
        resposta = self.client.get(reverse("home"))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'enctype="multipart/form-data"')
        self.assertContains(resposta, "csrfmiddlewaretoken")

    def test_home_sem_documentos_mostra_aviso(self):
        resposta = self.client.get(reverse("home"))
        self.assertContains(resposta, "Nenhum arquivo enviado ainda")
