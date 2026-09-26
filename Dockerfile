FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# postgresql-client e a unica dependencia de sistema que a aplicacao precisa:
# ela traz o pg_isready, que o entrypoint usa para esperar o banco. O libpq vem
# junto (dependencia do proprio pacote) e nao e usado pelo driver: o
# psycopg[binary] empacota a propria libpq dentro da wheel.
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app/ /app/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# usuario sem privilegio; /vol/media e dono dele para o volume herdar a permissao.
# /vol/static fica na camada do container mesmo: e saida do collectstatic, que roda
# a cada boot, entao nao ha o que persistir.
RUN useradd --uid 1000 --create-home appuser \
    && mkdir -p /vol/static /vol/media \
    && chown -R appuser:appuser /vol /app

USER appuser

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
