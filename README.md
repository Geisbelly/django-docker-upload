# Django + Gunicorn + Nginx + PostgreSQL com upload em volume

Aplicação Django containerizada em três serviços, com upload de arquivos
persistido em um volume Docker. O upload tem formulário próprio na página
inicial, **exige sessão** e passa por validação em camadas no model; o admin do
Django continua disponível como caminho alternativo.

## Arquitetura

```
          :8080
 navegador ──► nginx (proxy reverso, e só isso)
                 └─ tudo ──► web (gunicorn :8000) ──► db (postgres :5432)
                               │                          │
                               │                 volume postgres_data
                               ├─ /static/ ──► /vol/static (camada do container)
                               └─ /media/  ──► volume media_data
```

O nginx não monta volume nenhum: ele encaminha **todas** as rotas para a
aplicação. Quem lê e escreve arquivo é o container do Django.

| Serviço | Imagem | Papel |
|---|---|---|
| `db` | `postgres:16-alpine` | banco de dados |
| `web` | build do `Dockerfile` (python:3.12-slim) | Django servido por Gunicorn |
| `nginx` | build de `nginx/Dockerfile` | proxy reverso (única porta publicada) |

### Volumes

| Volume | Montagem | Conteúdo |
|---|---|---|
| `postgres_data` | `/var/lib/postgresql/data` | dados do PostgreSQL |
| `media_data` | `/vol/media` (só no `web`) | **arquivos enviados pelo upload** |

Os arquivos enviados vão para `MEDIA_ROOT=/vol/media` (subpasta `uploads/`), que
é um volume nomeado — sobrevive a `docker compose down` e à recriação dos
containers.

São **dois** volumes de propósito, e não três: `/vol/static` não é volume porque
o `collectstatic` regenera aquele diretório a cada boot, a partir da própria
imagem. Persistir saída derivada só acumularia arquivo de build antigo. E os dois
que existem não se juntam em um só: têm ciclos de vida e formas de backup
diferentes — `pg_dump` para o banco, `tar` para os arquivos —, e o Postgres
precisa mandar sozinho no diretório de dados dele.

## Como rodar

Requisitos: Docker e Docker Compose.

```bash
cp .env.example .env     # ajuste as senhas se quiser
docker compose up --build -d
```

Serviços prontos em alguns segundos. O `entrypoint.sh` espera o Postgres,
roda `migrate`, `collectstatic` e cria o superusuário a partir do `.env`.

| URL | O quê |
|---|---|
| http://localhost:8080/ | formulário de upload + lista de arquivos enviados (**exige login**) |
| http://localhost:8080/accounts/login/ | entrada, com as views prontas do `django.contrib.auth` |
| http://localhost:8080/admin/ | admin do Django (caminho alternativo) |
| http://localhost:8080/healthz/ | healthcheck (testa o banco) |

Login padrão do admin: `admin` / `admin123` (definidos no `.env`).

### Enviar um arquivo

Enviar e baixar exigem sessão: a home e a entrega de `/media/` estão sob
`login_required`, e quem não entrou é redirecionado para `/accounts/login/`. O
superusuário criado pelo `entrypoint.sh` a partir do `.env` já serve para entrar.

1. Acesse http://localhost:8080/ e entre.
2. Preencha o título, escolha o arquivo e clique em **Enviar arquivo**.
3. O arquivo aparece na lista abaixo do formulário e é servido pela aplicação
   em `/media/uploads/<nome>` (rota declarada em `app/config/urls.py`, porque
   com `DEBUG=0` o Django não serve mídia nem estáticos por conta própria).

### Validação do upload

O `FileField` do model carrega dois validadores próprios
(`app/core/validators.py`), que rodam tanto pelo formulário quanto pelo admin:

| Regra | Variável de ambiente | Padrão |
|---|---|---|
| Tamanho máximo | `UPLOAD_MAX_SIZE_MB` | `10` |
| Extensões aceitas | `UPLOAD_ALLOWED_EXTENSIONS` | `pdf,doc,docx,odt,txt,csv,xls,xlsx,ods,png,jpg,jpeg,gif,webp` |

Os validadores leem as configurações **na hora da chamada** em vez de receber os
valores como argumento. Por isso a migração serializa apenas a referência à
função, e mudar qualquer uma das duas variáveis no `.env` passa a valer sem gerar
migração nova.

A lista padrão não inclui `html` nem `svg` de propósito: `/media/` sai no mesmo
domínio da aplicação, e um desses arquivos enviado por um usuário poderia
executar script nesse domínio.

O `client_max_body_size 100M` do nginx continua sendo o limite externo — ele
barra o corpo gigante antes de chegar na aplicação. O limite de 10 MB é a regra
de negócio, com mensagem de erro para o usuário.

### Testes

```bash
docker compose exec web python manage.py test core
```

41 testes cobrindo o controle de acesso (anônimo barrado na home e no
download), a validação em camadas (nome, extensão, tamanho, assinatura
do conteúdo), o caminho feliz do upload, a gravação em `MEDIA_ROOT`, a entrega
de `/media/` com os cabeçalhos certos, path traversal na URL e a renderização do
formulário.

### Camada de validação

O upload atravessa cinco verificações antes de tocar o volume, e a resposta sai
com mais três cabeçalhos de defesa:

| Camada | Recusa | Arquivo |
|---|---|---|
| sessão | quem não está autenticado, na home e no download | `core/views.py` |
| nome | caminho, quebra de linha, caractere de controle ou invisível | `core/security.py` |
| extensão | fora da lista do `.env` | `core/validators.py` |
| tamanho | acima de `UPLOAD_MAX_SIZE_MB` | `core/validators.py` |
| conteúdo | primeiros bytes que não batem com a extensão | `core/validators.py` |
| título | caractere de controle ou invisível | `core/validators.py` |

A verificação de conteúdo compara a assinatura do arquivo com o que a extensão
promete (`%PDF-`, `\x89PNG`, `PK\x03\x04`…). Um executável renomeado para
`.pdf` passa pela checagem de extensão e é barrado aqui.

Na saída, `/media/` é servido pela view `servir_media`, que resolve o caminho
dentro de `MEDIA_ROOT` (barrando path traversal), define o `Content-Type` a
partir de uma tabela fixa, e devolve **tudo como download** — só imagem
rasterizada abre no navegador, com `X-Content-Type-Options: nosniff`. A resposta
carrega ainda `Content-Security-Policy`, `X-Frame-Options: DENY` e
`Referrer-Policy: same-origin`.

No banco: o ORM parametriza toda consulta, o serviço não publica porta, e a
conexão tem `statement_timeout` de 15s para uma consulta presa não segurar um
worker.

### Provar que o upload persiste

```bash
docker compose down          # derruba os containers (mantém os volumes)
docker compose up -d
```

Os arquivos continuam lá. Para apagar tudo, inclusive os volumes:

```bash
docker compose down -v
```

## Material de apresentação

| Arquivo | O quê |
|---|---|
| `apresentacao-defesa.html` | deck da defesa, 8 slides, com simulador animado no slide 5 (`N` notas, `O` índice, `P` simulador, `T` cronômetro, `F` tela cheia) |
| `DEFESA.md` | roteiro, decisões, funcionamento e perguntas prováveis |

Os dois primeiros abrem direto no navegador, sem instalar nada.

## Comandos úteis

```bash
docker compose logs -f web            # logs do gunicorn
docker compose exec web python manage.py createsuperuser
docker compose exec db psql -U appuser -d appdb
docker volume inspect django-docker-upload_media_data
```

## Estrutura

```
.
├── Dockerfile              # imagem do Django + Gunicorn
├── entrypoint.sh           # espera o banco, migra, collectstatic, cria admin
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── nginx/
│   ├── Dockerfile
│   └── default.conf        # proxy reverso + /static/ e /media/
└── app/
    ├── manage.py
    ├── config/             # settings, urls, wsgi
    └── core/               # model, validators, form, views, testes
        ├── security.py     # assinaturas, nome seguro, tipos que podem ser servidos
        ├── middleware.py   # Content-Security-Policy
        └── static/core/    # previa do arquivo escolhido (JS separado, por causa da CSP)
```

## Notas de configuração

- O container do Django roda como usuário sem privilégio (`appuser`, uid 1000);
  `/vol` é criado e dono dele na imagem, então os volumes nomeados herdam a
  permissão correta na primeira montagem.
- O nginx é **apenas** proxy reverso: não monta volume e não serve arquivo.
  Estáticos e mídia saem pela aplicação, pelas rotas em `app/config/urls.py`.
  O custo dessa escolha é que cada download ocupa um worker do Gunicorn.
- `client_max_body_size 100M` no nginx é o limite externo. O limite por arquivo
  é `UPLOAD_MAX_SIZE_MB` (10 MB por padrão); para aceitar arquivos maiores,
  aumente os dois.
- Em produção: troque `DJANGO_SECRET_KEY`, mantenha `DJANGO_DEBUG=0`, ajuste
  `DJANGO_ALLOWED_HOSTS` / `DJANGO_CSRF_TRUSTED_ORIGINS` e remova as variáveis
  `DJANGO_SUPERUSER_*` depois do primeiro boot.
