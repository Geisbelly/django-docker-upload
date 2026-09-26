FROM nginx:1.27-alpine

# openssl nao vem na imagem; e usado uma vez, para gerar o certificado proprio
RUN apk add --no-cache openssl

RUN rm /etc/nginx/conf.d/default.conf

# A imagem traz access.log e error.log como symlink para /dev/stdout e
# /dev/stderr. Um volume vazio montado sobre um diretorio que existe na imagem
# COPIA o conteudo dele — inclusive os symlinks —, e ai escrever no "arquivo"
# continuaria caindo na saida padrao, sem nada no volume. Removendo aqui, o
# diretorio nasce vazio e o nginx cria arquivos de verdade.
RUN rm -f /var/log/nginx/access.log /var/log/nginx/error.log

# templates/ e processado por envsubst pelo entrypoint oficial da imagem
COPY default.conf.template /etc/nginx/templates/default.conf.template
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80 443

ENTRYPOINT ["/entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
