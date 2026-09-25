# Roteiro de defesa

Material de apoio para a apresentação do projeto. O deck está em
`apresentacao-defesa.pptx` (as notas do apresentador já estão em cada slide).

---

## 1. Estrutura e tempo

Alvo: **12 a 15 minutos** de fala + demo, deixando espaço para perguntas.

| # | Slide | Tempo | A mensagem que precisa passar |
|---|---|---|---|
| 1 | Capa | 0:30 | O que é o projeto, em uma frase |
| 2 | Pedido × entregue | 1:00 | Os quatro requisitos estão cobertos, e onde |
| 3 | Arquitetura | 2:00 | **Slide central.** Caminho da requisição + volume compartilhado |
| 4 | Os três containers | 1:30 | O papel de cada um, com as decisões que não são default |
| 5 | Gunicorn e Nginx | 1:00 | Por que dois servidores, e por que não `runserver` |
| 6 | Dockerfile | 1:30 | Ordem das camadas é cache; usuário sem privilégio |
| 7 | entrypoint.sh | 1:30 | O container prepara o próprio ambiente; `exec` e PID 1 |
| 8 | Persistência | 1:00 | `MEDIA_ROOT` = ponto de montagem do volume |
| 9 | Caminho do upload | 1:30 | Formulário com validação; volume guarda os bytes, banco guarda o caminho |
| 10 | A prova | 1:00 | `down` não é `down -v` |
| 11 | Rede e limites | 1:00 | 100M vs 5MB; timeouts alinhados |
| 12 | Segurança | 1:00 | Configuração por ambiente, processo sem privilégio |
| 13 | Demo | 3:00 | Executar ao vivo |
| 14 | Limitações | 1:00 | Levantar as fraquezas antes da banca |
| 15 | Fechamento | 0:30 | Recapitular e abrir para perguntas |

Se o tempo apertar, os slides que podem ser resumidos em uma frase são o **4**, o
**11** e o **12**. Os que **não** podem ser pulados são o **3**, o **8** e o **10** —
são eles que provam o requisito principal.

---

## 2. Checklist antes de começar

- [ ] Docker Desktop **aberto e rodando** (checar com `docker info`)
- [ ] `docker compose up --build -d` já executado, stack no ar
- [ ] `docker compose ps` mostrando os três serviços, `db` como `healthy`
- [ ] Um arquivo pequeno de teste (PDF ou imagem, < 2 MB) já separado na área de trabalho
- [ ] Um arquivo **inválido** também separado, para mostrar a validação: renomeie
      qualquer coisa para `teste.exe`
- [ ] Um arquivo **já enviado antes** da apresentação, para a home não estar vazia
- [ ] Navegador aberto em `http://localhost:8080/`
- [ ] Terminal aberto na pasta do projeto, com fonte grande
- [ ] Deck aberto no modo apresentador (para ver as notas)

---

## 3. Roteiro da demo

```bash
docker compose ps
```
Três serviços em execução, `db` marcado como `healthy`.

```bash
curl http://localhost:8080/healthz/
```
Retorna `{"status": "ok"}` — a view roda `SELECT 1` no Postgres, então isso prova
que a aplicação está falando com o banco.

**No navegador**, em `http://localhost:8080/`:

1. **Mostrar a validação primeiro.** Escolher o `teste.exe`, enviar, e deixar a
   mensagem de erro na tela: *"Extensão .exe não é aceita. Permitidas: pdf, doc,
   …"*. Dizer que quem barrou foi o validador do model, no servidor — o `accept`
   do input é só conveniência do navegador e não vale como segurança.
2. **Agora o caminho feliz.** Título + arquivo válido → Enviar. A mensagem de
   sucesso aparece e o arquivo entra na lista, com nome, tamanho e data.
3. Clicar no link para baixar — a URL é `/media/uploads/<nome>`, servida
   diretamente pelo nginx, sem passar pelo Django.

Se sobrar tempo, vale rodar os testes na frente da banca:

```bash
docker compose exec web python manage.py test core
```

```bash
docker compose exec web ls -l /vol/media/uploads
```
O arquivo está dentro do container, no caminho de montagem do volume.

```bash
docker volume ls | grep media
docker volume inspect django-docker-upload_media_data
```
Mostra que é um volume nomeado gerenciado pelo Docker, com o seu `Mountpoint`.

**O momento principal:**

```bash
docker compose down
docker compose up -d
docker compose exec web ls -l /vol/media/uploads
```

Containers destruídos e recriados do zero — o arquivo continua lá. Recarregar a
home no navegador para confirmar que ele ainda aparece e ainda baixa.

### Plano B

Se o Docker travar ou a demo não subir: **ir direto para o slide 10**, que tem o
mesmo teste em texto, e explicar o raciocínio. Não insistir em debugar ao vivo —
isso queima o tempo e a impressão. Uma frase pronta: *"o ambiente não está
colaborando agora; o comportamento é este aqui, e o repositório sobe com um
comando só."*

---

## 4. Perguntas prováveis

### Sobre Docker e as imagens

**Por que três containers e não um só com tudo dentro?**
Separação de responsabilidades: cada container tem um processo e um ciclo de vida.
Posso atualizar a versão do nginx sem reconstruir a imagem do Django, escalar só o
`web` se o gargalo for a aplicação, e trocar o Postgres por um serviço gerenciado
sem mexer no resto. Num container só, qualquer mudança derruba tudo.

**Qual a diferença entre imagem e container?**
A imagem é o template imutável, feito de camadas — é o que o `Dockerfile` produz.
O container é uma instância em execução dessa imagem, com uma camada de escrita
efêmera por cima. É justamente porque essa camada é efêmera que o upload precisa
ir para um volume.

**Por que `python:3.12-slim` e não `alpine`?**
A `slim` usa glibc, então as *wheels* pré-compiladas do PyPI funcionam direto —
inclusive a do `psycopg[binary]`. A Alpine usa musl, o que costuma forçar a
compilação das dependências no build: mais lento e com mais chance de erro. A
`slim` é o meio-termo entre tamanho e compatibilidade.

**Por que copiar o `requirements.txt` antes do código?**
Cada instrução do Dockerfile vira uma camada com cache. Se eu copiasse o código
antes, qualquer alteração em uma view invalidaria a camada do `pip install` e
reinstalaria todas as dependências a cada build. Na ordem atual, o `pip install`
só roda de novo quando o `requirements.txt` muda.

**Para que serve o `.dockerignore`?**
Ele tira arquivos do *build context* — o que é enviado ao daemon do Docker. Além
de acelerar o build, ele garante que `.git`, `.env` e a pasta `media/` não entrem
acidentalmente na imagem. É uma proteção contra vazar segredo dentro da imagem.

**O que acontece se um container cair?**
Os três têm `restart: unless-stopped`, então o Docker sobe de novo. No caso do
`web`, o entrypoint roda `migrate` e `collectstatic` outra vez — as duas operações
são idempotentes — e os dados continuam nos volumes.

### Sobre volumes e persistência

**Qual a diferença entre volume nomeado e bind mount?**
O volume nomeado é gerenciado pelo Docker: não depende de caminho do host, funciona
igual em Windows e Linux, e herda o dono do diretório da imagem na primeira
montagem. O bind mount aponta para uma pasta específica da máquina — prático em
desenvolvimento, frágil para entregar. Por isso usei volume nomeado nos três casos.

**Onde os arquivos ficam fisicamente?**
Em `/var/lib/docker/volumes/django-docker-upload_media_data/_data` no host — no
Docker Desktop, dentro da VM do Docker. `docker volume inspect` mostra o
`Mountpoint` exato.

**Por que não salvar o arquivo dentro do banco?**
Binário em banco infla o tamanho, deixa `pg_dump` e restore lentos, consome
conexão para streaming e não deixa o arquivo ser servido pelo nginx. O padrão é
guardar os bytes no storage e só o caminho na tabela — que é exatamente o que o
`FileField` do Django faz.

**Como você faria o backup?**
Duas coisas separadas. O banco, com `docker compose exec db pg_dump -U appuser appdb`.
Os arquivos, empacotando o volume:
`docker run --rm -v django-docker-upload_media_data:/data -v "$PWD":/backup alpine tar czf /backup/media.tgz /data`.

**E se eu rodar `docker compose down -v`?**
Aí os arquivos somem — é o único comando do fluxo normal que apaga os volumes. É
exatamente a diferença que eu mostrei no slide 10.

### Sobre nginx e rede

**O que é um proxy reverso?**
É um servidor que recebe a requisição do cliente em nome do servidor de aplicação.
O navegador só conversa com o nginx; quem fala com o Gunicorn é o nginx, pela rede
interna. Isso me dá um ponto único de entrada para aplicar limites, servir
arquivos e, no futuro, encerrar o TLS.

**Por que o nginx serve `/static/` e `/media/` em vez do Django?**
Porque entregar arquivo é trabalho de servidor web, não de aplicação. O nginx faz
isso com chamada de sistema direta, sem passar pelo interpretador Python nem
ocupar um worker do Gunicorn. E o Django, com `DEBUG=0`, nem serve estáticos.

**Como os containers se encontram sem IP fixo?**
O Compose cria uma rede própria com DNS interno, e o nome de cada serviço vira
hostname. Por isso o `settings.py` aponta para `db` e o nginx faz `proxy_pass`
para `web:8000`.

**Qual a diferença entre `expose` e `ports`?**
`ports` publica a porta no host — é o que deixa `localhost:8080` funcionar.
`expose` só declara a porta na rede interna, sem publicar. O `web` usa `expose`, e
o `db` não declara nada: nenhum dos dois é alcançável de fora da rede do Compose.

**Qual é o tamanho máximo de upload?**
100 MB, e quem impõe isso é o nginx, com `client_max_body_size`. Vale esclarecer:
o `FILE_UPLOAD_MAX_MEMORY_SIZE = 5MB` do Django **não** é um limite de tamanho — é
o ponto em que o Django para de montar o arquivo na memória e passa a gravar em
arquivo temporário no disco. São coisas diferentes.

**Por que os dois timeouts de 120 segundos?**
Para não brigarem entre si. Se o `proxy_read_timeout` do nginx fosse menor que o
`--timeout` do Gunicorn, o cliente receberia 504 enquanto o worker ainda estivesse
processando o upload. Iguais, os dois desistem no mesmo instante.

### Sobre Django e Gunicorn

**O que é WSGI?**
É a interface padrão entre um servidor e uma aplicação Python. O Gunicorn carrega
o objeto `application` de `config/wsgi.py` e chama a aplicação a cada requisição.
É o contrato que permite trocar o servidor sem mudar o Django.

**Por que 3 workers?**
A regra prática é `2 × núcleos + 1`, mas dentro de container eu prefiro um número
fixo e previsível, e escalar réplicas do serviço em vez de workers no processo.
Três atende bem o volume deste trabalho e cabe folgado nos recursos de uma máquina
de desenvolvimento.

**O que o `collectstatic` faz?**
Junta os arquivos estáticos de todas as apps instaladas — inclusive os do admin —
em `STATIC_ROOT`, que aqui é `/vol/static`. Esse diretório é o volume que o nginx
monta como somente leitura e serve em `/static/`.

**O que o `FileField` guarda no banco?**
Uma string com o caminho relativo a `MEDIA_ROOT`, em coluna `VARCHAR`. Os bytes
ficam no volume. É por isso que o banco não cresce com o tamanho dos uploads.

**Por que `exec` na última linha do entrypoint?**
Sem `exec`, o shell continuaria sendo o PID 1 e o Gunicorn seria um processo
filho. Aí o `SIGTERM` que o Docker manda no `stop` iria para o shell, que não o
repassa — e o container morreria por timeout em vez de desligar limpo. Com `exec`,
o Gunicorn substitui o shell e recebe os sinais direto.

**Rodar `migrate` no boot não é arriscado?**
Com uma réplica do `web`, não: o comando é idempotente e o `set -e` derruba o boot
se falhar, o que é melhor do que servir com o schema errado. Com várias réplicas
subindo juntas, duas poderiam tentar migrar ao mesmo tempo — por isso, ao escalar,
o certo é tirar o `migrate` do entrypoint e rodá-lo como job separado. Está listado
nos próximos passos.

### Sobre segurança

**Onde ficam as senhas?**
No `.env`, que está no `.gitignore` e no `.dockerignore`. O repositório versiona
apenas o `.env.example`, com valores de exemplo. Em produção de verdade, o certo
seria usar o mecanismo de secrets do orquestrador em vez de arquivo.

**Por que rodar como usuário sem privilégio?**
Para limitar o estrago. Se a aplicação for comprometida por uma falha de execução
remota, o atacante cai como `appuser`, sem poder instalar pacote, alterar binário
do sistema ou escrever fora do que lhe pertence.

**Que riscos existem nesse upload?**
O principal é servir conteúdo do usuário no mesmo domínio da aplicação: um HTML
ou um SVG enviado por alguém poderia executar script nesse domínio. Por isso a
lista de extensões aceitas não inclui `html` nem `svg`. A defesa completa seria
forçar `Content-Disposition: attachment` na location `/media/` do nginx, ou
servir a mídia de um domínio separado — está nos próximos passos.

Vale ser honesta sobre o limite do que eu validei: eu checo **extensão**, não o
conteúdo do arquivo. Alguém pode renomear um executável para `.pdf` e ele passa.
Validar de verdade exigiria inspecionar os bytes iniciais, com `python-magic` ou
equivalente. Para o escopo deste trabalho, extensão e tamanho cobrem o caso de
uso; em produção eu acrescentaria a checagem de conteúdo.

**O que faltaria para isso ir a produção?**
TLS no nginx, segredos fora de arquivo, backup automatizado dos dois volumes,
centralização de logs, e um pipeline de CI rodando os testes antes do deploy.

### Sobre escala

**Como você escalaria isso?**
`docker compose up --scale web=3` já funciona no nível de rede, porque o
`upstream` do nginx resolve o nome do serviço e balanceia entre as réplicas. Mas
duas coisas teriam de mudar antes: tirar o `migrate` do entrypoint, e trocar o
volume local por um storage compartilhado (S3 ou MinIO), porque um volume local
não é visto por réplicas em nós diferentes.

---

## 5. Perguntas sobre o formulário e a validação

**Onde fica a validação, e por que aí?**
Nos validadores do `FileField`, em `app/core/validators.py`. Ficando no model,
ela vale para **qualquer** caminho de escrita — o formulário da home, o admin do
Django e qualquer código que chame `full_clean()`. Se estivesse só no formulário,
um upload pelo admin passaria sem checagem.

**O `accept` no input não resolve?**
Não. O `accept` só filtra o que aparece na janela de seleção do navegador —
qualquer pessoa desabilita isso ou manda a requisição direto. Ele é conveniência
de interface; quem decide é o servidor. Eu deixo os dois: o `accept` para o
usuário comum e o validador para valer.

**Por que os validadores leem as configurações em vez de receber os valores?**
Se eu usasse `FileExtensionValidator(allowed_extensions=[...])`, a lista seria
congelada dentro do arquivo de migração. Trocar uma extensão no `.env` passaria a
exigir uma migração nova, e `makemigrations --check` acusaria diferença. Como as
minhas funções leem `settings` na hora da chamada, a migração guarda só a
referência à função, e a variável de ambiente é a única fonte da verdade.

**Por que 10 MB se o nginx aceita 100 MB?**
São camadas diferentes. O nginx é o perímetro: ele corta um corpo gigante antes
de gastar worker do Gunicorn, e não sabe nada sobre regra de negócio. Os 10 MB
são a regra da aplicação, e é ela que devolve uma mensagem em português dizendo o
tamanho enviado e o limite. Os dois são configuráveis.

**Como você testou?**
São 15 testes em `app/core/tests.py`, rodando com
`docker compose exec web python manage.py test core`. Eles cobrem o caminho
feliz, a rejeição por extensão, a rejeição por tamanho, o limite exato, extensão
em maiúsculas, arquivo sem extensão, o `full_clean()` do model direto, e o POST
na home com redirect e mensagem. Cada teste usa um `MEDIA_ROOT` temporário
próprio, porque o banco volta atrás entre os testes mas o disco não.

**O que acontece se dois arquivos tiverem o mesmo nome?**
O storage do Django detecta a colisão e acrescenta um sufixo aleatório — nada é
sobrescrito. Tem um teste cobrindo isso.

---

## 6. Frases de segurança

Para quando travar ou vier uma pergunta fora do previsto:

- *"Não testei esse cenário específico, mas pelo que está configurado, o
  comportamento esperado seria X — e dá para verificar com Y."*
  Honesto, e mostra raciocínio em vez de chute.
- *"Essa é uma limitação consciente, está no slide de próximos passos."*
- *"Deixa eu mostrar no código."* — abrir o arquivo é sempre mais forte do que
  descrever de memória.

Nunca inventar um número ou um comportamento. Se não souber, dizer que não sabe e
explicar como descobriria.
