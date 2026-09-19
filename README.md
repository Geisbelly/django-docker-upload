# Django + Gunicorn + Nginx + PostgreSQL com upload em volume

Aplicação Django containerizada em três serviços, com upload de arquivos
persistido em um volume Docker. A interface de upload é o **admin padrão do
Django** (sem front-end customizado).

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
| http://localhost:8080/ | lista de arquivos enviados |
| http://localhost:8080/admin/ | admin do Django (upload) |
| http://localhost:8080/healthz/ | healthcheck (testa o banco) |

Login padrão do admin: `admin` / `admin123` (definidos no `.env`).

### Enviar um arquivo

1. Acesse http://localhost:8080/admin/ e faça login.
2. **Documentos → Documentos → Adicionar documento**.
3. Preencha o título, escolha o arquivo e salve.
4. O arquivo aparece na home e é servido pelo nginx em `/media/uploads/<nome>`.

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
    └── core/               # model Documento (FileField), admin, views
```

## Notas de configuração

- O container do Django roda como usuário sem privilégio (`appuser`, uid 1000);
  `/vol` é criado e dono dele na imagem, então os volumes nomeados herdam a
  permissão correta na primeira montagem.
- O nginx monta os volumes de mídia e estáticos como somente leitura.
- `client_max_body_size 100M` no nginx; ajuste junto com os limites do Django em
  `app/config/settings.py` se precisar de arquivos maiores.
- Em produção: troque `DJANGO_SECRET_KEY`, mantenha `DJANGO_DEBUG=0`, ajuste
  `DJANGO_ALLOWED_HOSTS` / `DJANGO_CSRF_TRUSTED_ORIGINS` e remova as variáveis
  `DJANGO_SUPERUSER_*` depois do primeiro boot.
