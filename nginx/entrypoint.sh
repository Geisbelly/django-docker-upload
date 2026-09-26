#!/bin/sh
# Gera um certificado proprio na primeira subida, dentro do volume, e entrega o
# controle ao entrypoint original da imagem (que faz o envsubst dos templates).
set -e

CERTS=/etc/nginx/certs
CN=${TLS_CN:-localhost}

if [ ! -f "$CERTS/server.crt" ]; then
  echo "gerando certificado proprio para CN=${CN}..."
  mkdir -p "$CERTS"
  openssl req -x509 -nodes -newkey rsa:2048 -days 825 \
    -keyout "$CERTS/server.key" \
    -out    "$CERTS/server.crt" \
    -subj   "/C=BR/O=Defesa Computacao em Nuvem/CN=${CN}" \
    -addext "subjectAltName=DNS:${CN},DNS:localhost,IP:127.0.0.1" \
    >/dev/null 2>&1
  chmod 600 "$CERTS/server.key"
  echo "certificado gerado; ele fica no volume e sobrevive ao container."
else
  echo "certificado ja existe no volume, reaproveitando."
fi

exec /docker-entrypoint.sh "$@"
