# Django + Gunicorn + Nginx + PostgreSQL com upload em volume

Aplicação Django containerizada em três serviços, com upload de arquivos
persistido em um volume Docker. O upload tem formulário próprio na página
inicial, com validação de extensão e tamanho no model; o admin do Django
continua disponível como caminho alternativo.

## Arquitetura

```
          :8080
 navegador ──► nginx (proxy reverso)
                 │  /static/  ──► volume static_data (servido direto)
                 │  /media/   ──► volume media_data  (servido direto)
                 └─ /*        ──► web (gunicorn :8000) ──► db (postgres :5432)
                                                              │
                                                     volume postgres_data
```

| Serviço | Imagem | Papel |
|---|---|---|
| `db` | `postgres:16-alpine` | banco de dados |
| `web` | build do `Dockerfile` (python:3.12-slim) | Django servido por Gunicorn |
| `nginx` | build de `nginx/Dockerfile` | proxy reverso + arquivos estáticos e de mídia |

### Volumes

| Volume | Montagem | Conteúdo |
|---|---|---|
| `postgres_data` | `/var/lib/postgresql/data` | dados do PostgreSQL |
| `media_data` | `/vol/media` (rw no `web`, ro no `nginx`) | **arquivos enviados pelo upload** |
| `static_data` | `/vol/static` (rw no `web`, ro no `nginx`) | estáticos do `collectstatic` |

Os arquivos enviados vão para `MEDIA_ROOT=/vol/media` (subpasta `uploads/`), que
é um volume nomeado — sobrevive a `docker compose down` e à recriação dos
containers.

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
| http://localhost:8080/ | formulário de upload + lista de arquivos enviados |
| http://localhost:8080/admin/ | admin do Django (caminho alternativo) |
| http://localhost:8080/healthz/ | healthcheck (testa o banco) |

Login padrão do admin: `admin` / `admin123` (definidos no `.env`).

### Enviar um arquivo

1. Acesse http://localhost:8080/.
2. Preencha o título, escolha o arquivo e clique em **Enviar arquivo**.
3. O arquivo aparece na lista abaixo do formulário e é servido pelo nginx em
   `/media/uploads/<nome>`.

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

A lista padrão não inclui `html` nem `svg` de propósito: o nginx serve `/media/`
no mesmo domínio da aplicação, e um desses arquivos enviado por um usuário
poderia executar script nesse domínio.

O `client_max_body_size 100M` do nginx continua sendo o limite externo — ele
barra o corpo gigante antes de chegar na aplicação. O limite de 10 MB é a regra
de negócio, com mensagem de erro para o usuário.

### Testes

```bash
docker compose exec web python manage.py test core
```

15 testes cobrindo validação de extensão e de tamanho, o caminho feliz do
upload, a gravação em `MEDIA_ROOT` e a renderização do formulário.

### Provar que o upload persiste

```bash
docker compose down          # derruba os containers (mantém os volumes)
docker compose up -d
```

Os arquivos continuam lá. Para apagar tudo, inclusive os volumes:

```bash
docker compose down -v
```

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
```

## Notas de configuração

- O container do Django roda como usuário sem privilégio (`appuser`, uid 1000);
  `/vol` é criado e dono dele na imagem, então os volumes nomeados herdam a
  permissão correta na primeira montagem.
- O nginx monta os volumes de mídia e estáticos como somente leitura.
- `client_max_body_size 100M` no nginx é o limite externo. O limite por arquivo
  é `UPLOAD_MAX_SIZE_MB` (10 MB por padrão); para aceitar arquivos maiores,
  aumente os dois.
- Em produção: troque `DJANGO_SECRET_KEY`, mantenha `DJANGO_DEBUG=0`, ajuste
  `DJANGO_ALLOWED_HOSTS` / `DJANGO_CSRF_TRUSTED_ORIGINS` e remova as variáveis
  `DJANGO_SUPERUSER_*` depois do primeiro boot.
