# Roteiro de defesa

Material de apoio para a apresentação do projeto. O deck está em
`apresentacao-defesa.html` — abre no navegador, sem instalar nada. As notas do
apresentador estão dentro dele: tecla `N` abre o painel, `O` abre o índice dos
slides e `T` liga o cronômetro.

O **slide 5 é um simulador**: ele toca sozinho quando o slide entra e mostra a
aplicação gravando e lendo no volume, o `down` levando o container e o volume
ficando. `P` repete, `,` e `.` andam passo a passo.

Para estudar com mais detalhe, `fluxo-animado.html` tem a versão longa da mesma
animação, com os 16 passos desde o build da imagem.

---

## 1. Estrutura e tempo

Alvo: **12 a 15 minutos** de fala + demo, deixando espaço para perguntas.

| # | Slide | Tempo | Item do enunciado |
|---|---|---|---|
| 1 | Capa | 0:30 | — |
| 2 | Escopo | 0:30 | — |
| 3 | Arquitetura | 1:45 | **1** · visão geral, portas, rede, volumes |
| 4 | Computação em nuvem | 1:15 | — (conteúdo da disciplina) |
| 5 | Dockerfile | 1:30 | **2** · imagem da aplicação |
| 6 | Docker Compose | 1:30 | **3** · orquestração, serviço a serviço |
| 7 | Nginx | 1:30 | **5** · proxy reverso e trechos da configuração |
| 8 | Simulador | 1:45 | **6** · persistência, animada |
| 9 | Caminho do upload | 1:15 | **7** · fluxo do upload |
| 10 | Banco de dados | 0:45 | **4** e **6** · schema real |
| 11 | Arquivos | 0:45 | **6** e **7** · caminho no disco |
| 12 | Validação | 1:15 | — (segurança) |
| 13 | Demo | 3:00 | — |
| 14 | Análise técnica | 1:30 | **8** · 3 vantagens, 3 limitações, 3 melhorias |

O item **4** (comunicação entre containers, DNS interno, portas internas e
externas) está no slide 3 e volta no 6 e no 10.

Total: **18min45** contando a demo — acima do alvo original de 12 a 15 minutos,
porque o enunciado pede oito seções obrigatórias. Se a banca limitar o tempo, os
que se resumem em uma frase são o **4**, o **11** e o **12**; os que **não** podem
ser pulados são o **3**, o **5**, o **6**, o **7**, o **8** e o **14**, porque cada
um responde diretamente a um item da avaliação.

---

## 2. O trabalho na linguagem da disciplina

A banca é de **Computação em Nuvem**, não de Docker. Tudo que está aqui existe
para responder a uma pergunta da matéria; esta seção é o mapa entre as duas
coisas.

| Conceito da disciplina | Onde ele aparece no projeto |
|---|---|
| Virtualização em nível de SO | Os três containers compartilham o kernel do host — sem hypervisor, sem SO convidado |
| Imagem como artefato imutável | O `Dockerfile` produz uma imagem versionável, distribuível por *registry* |
| Portabilidade / anti *lock-in* | A mesma imagem roda em qualquer provedor; nada no código depende da minha máquina |
| Infraestrutura como código | O `docker-compose.yml` declara serviços, rede e volumes, e está versionado no Git |
| Orquestração | O Compose é a forma local dela; o passo seguinte é Kubernetes ou ECS |
| Aplicação *stateless* | O container não guarda estado: banco no Postgres, arquivos no volume |
| Armazenamento persistente | Dois volumes nomeados, desacoplados do ciclo de vida dos containers |
| Serviços de apoio acoplados | O Postgres é um recurso ligado por variável de ambiente, trocável sem mexer no código |
| Elasticidade / escala horizontal | `--scale web=3` no nível de rede; o que falta está na seção de limitações |
| Disponibilidade / auto-recuperação | `healthcheck` no banco e `restart: unless-stopped` nos três |
| Isolamento de rede | Uma porta publicada; o banco não é alcançável de fora da rede do Compose |
| Configuração por ambiente | `.env` fora do Git — princípio III do 12-Factor |

### Container e máquina virtual não são a mesma coisa

A VM virtualiza **hardware**: um hypervisor apresenta CPU, memória e disco
virtuais, e dentro dela roda um sistema operacional convidado inteiro. O
container virtualiza o **sistema operacional**: os processos usam o kernel do
host, isolados por *namespaces* e limitados por *cgroups*.

A consequência prática é o que interessa na matéria: o container sobe em
segundos em vez de minutos, ocupa megabytes em vez de gigabytes, e cabem dezenas
deles onde caberiam poucas VMs. O preço é o isolamento mais fraco — todos
dependem do mesmo kernel — e a impossibilidade de rodar um SO diferente do host.

> Honestidade que vale ponto: na minha máquina (macOS) o Docker Desktop roda uma
> VM Linux por baixo, então ali existe sim um hypervisor. Em um servidor Linux,
> que é o destino real, não existe.

### Em que modelo de serviço isso se encaixa

Do jeito que está — containers rodando numa máquina que eu administro — o modelo
é **IaaS**: eu cuido do sistema operacional, das atualizações e do runtime.

Subindo a mesma imagem num serviço gerenciado de containers (ECS, Cloud Run,
Azure Container Apps), passa a ser **CaaS/PaaS**: o provedor cuida do host e eu
entrego só a imagem. **O código não muda** — e é exatamente esse o argumento da
portabilidade.

### O 12-Factor App, aplicado

| Princípio | Como está no projeto |
|---|---|
| III · Configuração no ambiente | `SECRET_KEY`, senhas, hosts e limites vêm do `.env`, nunca do código |
| IV · Serviços de apoio como recursos | O Postgres é endereçado por variável; trocar por um banco gerenciado é trocar o host |
| VI · Processos sem estado | Nada é guardado na memória do worker entre requisições |
| VII · Vínculo de porta | O Gunicorn expõe a própria porta; o nginx só encaminha |
| IX · Descartabilidade | Boot rápido e desligamento limpo: o `exec` faz o Gunicorn receber o `SIGTERM` |
| XI · Logs como fluxo de eventos | Gunicorn escreve no `stdout`, e quem coleta é o Docker |
| X · Paridade dev/produção | A mesma imagem e a mesma stack nos dois lugares |

### "Gado, não bicho de estimação"

Bicho de estimação é o servidor com nome próprio, configurado à mão, que ninguém
pode desligar. Gado é a instância numerada, que se destrói e recria sem
cerimônia.

Os meus containers são gado: qualquer um pode ser destruído e recriado a partir
da imagem, porque **o que precisa sobreviver está fora deles** — nos volumes e no
banco. É o slide 5 da apresentação, e é o mesmo raciocínio que sustenta
*auto-scaling* e substituição de instância defeituosa numa nuvem de verdade.

### O que falta para isso ser "nuvem de verdade"

Está na seção de limitações, mas em vocabulário da matéria:

- **Elasticidade real** exige tirar o `migrate` do boot (várias réplicas subindo
  juntas não podem migrar ao mesmo tempo) e trocar o volume local por
  *object storage* (S3, MinIO) — volume local não é visto por réplicas em nós
  diferentes.
- **Alta disponibilidade** exige mais de um nó e um balanceador de verdade na
  frente, não um nginx num host só.
- **Observabilidade** exige centralizar os logs que hoje ficam no `docker logs`.
- **Segurança de transporte** exige TLS, que entraria no nginx ou no balanceador.

---

## 3. As decisões, uma a uma

Cada escolha abaixo tem um **"em vez de"**. Saber o que foi descartado, e por quê,
é o que separa uma decisão de um acidente — e é exatamente isso que a banca
pergunta. A seção 8 tem as mesmas ideias no formato pergunta/resposta; esta aqui
é a versão corrida, para estudar antes.

### Containers, e três deles

Um container empacota a aplicação junto com as dependências dela. Na prática: a
versão do Python, a lib do Postgres e a do Gunicorn são as mesmas na minha
máquina e na de quem avalia.

Três em vez de um porque **cada container tem um processo e um ciclo de vida
próprios**. Com tudo junto, subir a versão do nginx obrigaria a reconstruir a
imagem do Django; escalar a aplicação arrastaria o banco junto; um processo
travado derrubaria os outros dois.

> Analogia: três containers são três funcionários com crachá próprio. Um
> container com tudo dentro é uma pessoa só acumulando três funções — funciona
> até o dia em que ela falta.

### PostgreSQL em vez de SQLite

SQLite é um arquivo, e escrita concorrente nele serializa. Com 3 workers do
Gunicorn atendendo em paralelo, isso vira gargalo. Postgres também é o que se usa
em produção, então o ambiente do trabalho se parece com o real. O serviço `db`
não publica porta nenhuma: só quem está na rede do Compose alcança o banco.

### Gunicorn em vez de `runserver`

O `runserver` é o servidor de desenvolvimento — a documentação do Django diz
explicitamente para não usar em produção. Ele é processo único, com autoreload, e
não gerencia workers: nada reinicia um processo travado ou vazando memória.

O Gunicorn é um servidor WSGI de verdade: 3 processos atendendo em paralelo,
`--timeout 120`, e logs em stdout — o formato que o Docker coleta.

### Nginx na frente, mesmo já tendo o Gunicorn

É a pergunta que mais cai. Resposta curta: **são papéis diferentes**. O Gunicorn
executa código Python; o nginx cuida da rede — quem entra, com que limite e por
qual porta. Concretamente, o nginx traz três coisas que o Gunicorn sozinho não
daria:

1. **Ponto único de entrada.** Só ele publica porta no host (`8080→80`). O `web`
   usa `expose` e o `db` não declara nada.
2. **Limite de corpo.** `client_max_body_size 100M` corta um upload gigante no
   perímetro, antes de ocupar um worker do Gunicorn.
3. **Lugar para o TLS.** É nele que o HTTPS entraria, sem a aplicação precisar
   saber disso — ela já lê o esquema pelo `X-Forwarded-Proto`.

O nginx **não serve arquivo** neste projeto: ele não monta volume nenhum e
encaminha todas as rotas para a aplicação. Foi uma decisão deliberada de manter o
proxy com um papel só.

> Analogia: o nginx é a recepção do prédio — filtra quem entra e encaminha todo
> mundo para o andar certo, mas não resolve nada sozinho. Quem faz o trabalho,
> inclusive buscar o arquivo, é o time lá em cima.

### `python:3.12-slim` em vez de `alpine`

A `slim` usa glibc, então as *wheels* pré-compiladas do PyPI instalam direto —
inclusive a do `psycopg[binary]`. A Alpine usa musl, o que normalmente força
compilar as dependências no build: mais lento e mais frágil. E em vez da imagem
completa porque a `slim` traz menos pacote, logo menos superfície de
vulnerabilidade.

### Volume nomeado em vez de bind mount

O bind mount aponta para uma pasta específica da máquina — muda de caminho entre
Windows e Linux e quebra na entrega. O volume nomeado é um objeto gerenciado pelo
Docker, sem caminho de host no compose, e **herda o dono do diretório que já
existe na imagem** na primeira montagem.

Por isso o `Dockerfile` cria `/vol` e faz `chown` para o `appuser` **antes** de
qualquer montagem: se não fizesse, o volume nasceria pertencendo ao root e o
`appuser` não conseguiria gravar o upload.

### Arquivo no volume, caminho no banco

O `FileField` grava os bytes no disco e guarda na coluna apenas uma string com o
caminho relativo a `MEDIA_ROOT`. Binário dentro do banco infla o `pg_dump`, deixa
o restore lento e prende o arquivo ao ciclo de vida do banco. Aqui os dois
escalam separados.

> Analogia: o banco guarda o **endereço**; o volume guarda a **caixa**.

### Validação no model, não no formulário

Os validadores ficam presos ao `FileField` em `app/core/models.py`, definidos em
`app/core/validators.py`. Ficando no model, a regra vale para **qualquer** caminho
de escrita: o formulário da home, o admin do Django, e qualquer código que chame
`full_clean()`. Se estivesse só no form, um upload pelo admin passaria sem
checagem.

### Validadores que leem as settings na hora da chamada

Se fosse `FileExtensionValidator(allowed_extensions=[...])`, a lista ficaria
congelada dentro do arquivo de migração, e trocar uma extensão no `.env` exigiria
migração nova (e `makemigrations --check` acusaria diferença). Como são funções
que consultam `settings` quando rodam, a migração guarda só a referência à função
e o `.env` é a única fonte da verdade.

### Configuração por variável de ambiente

`SECRET_KEY`, senhas, `ALLOWED_HOSTS` e os limites de upload vêm do `.env`, que
está no `.gitignore` e no `.dockerignore`. O repositório versiona só o
`.env.example`. A mesma imagem roda em qualquer ambiente trocando variável, sem
tocar no código.

### Usuário sem privilégio

`USER appuser` (uid 1000) no fim do `Dockerfile`. Se a aplicação for comprometida
por uma falha de execução remota, o atacante cai como `appuser` — sem instalar
pacote, sem alterar binário do sistema, sem escrever fora do que lhe pertence.

---

## 4. Como funciona, do boot ao download

### O boot

O `entrypoint.sh` roda antes do Gunicorn e prepara o ambiente:

```
pg_isready  →  migrate  →  collectstatic  →  createsuperuser  →  exec gunicorn
```

Dois detalhes que viram pergunta:

- **`exec` na última linha.** Sem ele, o shell continuaria sendo o PID 1 e não
  repassaria o `SIGTERM` do Docker; o container morreria por timeout em vez de
  desligar limpo. Com `exec`, o Gunicorn substitui o shell e recebe os sinais.
- **`set -e` no topo.** Derruba o boot se uma migração falhar — melhor falhar na
  subida do que servir com o schema errado.

### Uma requisição comum

```
navegador ──8080──► nginx ──8000──► gunicorn ──5432──► postgres
```

O nginx encontra o `web` pelo **nome do serviço**: o Compose cria uma rede
própria com DNS interno, e cada serviço vira hostname. Por isso o `settings.py`
aponta para `db` e o nginx faz `proxy_pass` para `web:8000`, sem IP fixo em lugar
nenhum.

### Um upload, passo a passo

0. **A sessão é conferida.** Sem login, o `@login_required` redireciona para
   `/accounts/login/` e o upload nem é tentado.
1. **POST multipart** do formulário da home.
2. **O nginx repassa.** Aceita o corpo até 100M; não guarda nada.
3. **O Django valida** extensão e tamanho. Reprovou, **nada é gravado** e o erro
   volta no formulário.
4. **O `FileField` grava os bytes** em `/vol/media/uploads/<nome>` — que é o ponto
   de montagem do volume `media_data`.
5. **O banco recebe só o caminho**, mais título e data.
6. **Redirect** (POST/Redirect/GET): recarregar a página não reenvia o arquivo.
7. **O download** sai depois por `/media/uploads/<nome>`, servido pela própria
   aplicação: o nginx encaminha, e o Django — depois de conferir a sessão de novo
   — lê do volume e devolve.

### Por que o arquivo sobrevive

Ele nunca esteve na camada de escrita do container. `MEDIA_ROOT` é exatamente o
ponto onde o volume está montado, e o volume é um objeto separado no Docker.
`docker compose down` remove containers e rede; o volume fica e é remontado no
container novo. O único comando do fluxo normal que apaga é `down -v`.

> Analogia: o container é um computador descartável; o volume é o HD externo.
> Jogar o computador fora não apaga o HD — a menos que você jogue o HD junto, que
> é o que o `-v` faz.

### Os três números que parecem o mesmo

| Onde | Valor | O que é de verdade |
|---|---|---|
| nginx | `client_max_body_size 100M` | perímetro: corta corpo gigante antes de gastar worker |
| aplicação | `UPLOAD_MAX_SIZE_MB=10` | regra de negócio, com mensagem em português |
| Django | `FILE_UPLOAD_MAX_MEMORY_SIZE=5MB` | **não é limite**: é onde o Django passa da memória para arquivo temporário |

E os dois timeouts de 120s (`proxy_read_timeout` no nginx, `--timeout` no
Gunicorn) são iguais de propósito: se o do nginx fosse menor, o cliente levaria
504 enquanto o worker ainda estivesse processando o upload.

### O cabeçalho `Host` e o CSRF

O nginx repassa `proxy_set_header Host $http_host`, e **não** `$host`. A diferença
é a porta: `$host` a descarta. Com `$host`, o Django via o host como `localhost`
enquanto o navegador mandava `Origin: http://localhost:8080` — os dois não batiam,
e a verificação de CSRF recusava todo POST com **403**.

Vale como exemplo concreto se a banca perguntar o que um proxy reverso precisa
repassar para a aplicação não se perder.

---

## 5. A camada de validação

Servir arquivo enviado por usuário, no mesmo domínio da aplicação, é o ponto mais
delicado do projeto. A defesa é em camadas, e cada uma é barata o bastante para
recusar antes de a seguinte gastar trabalho.

| # | Camada | O que ela recusa | Onde está |
|---|---|---|---|
| 0 | sessão | quem não está autenticado — vale para a home e para o download | `core/views.py` |
| 1 | nginx | corpo acima de 100M, antes de gastar worker | `nginx/default.conf` |
| 2 | nome do arquivo | separador de caminho, quebra de linha, caractere de controle ou invisível, nome longo demais | `core/security.py` |
| 3 | extensão e tamanho | extensão fora da lista do `.env`, arquivo acima de 10 MB | `core/validators.py` |
| 4 | conteúdo | primeiros bytes que não correspondem à extensão | `core/validators.py` |
| 5 | título | caractere de controle ou invisível | `core/validators.py` |
| 6 | na saída | tipo adivinhado, execução no navegador, enquadramento em iframe | `core/views.py`, `core/middleware.py` |

### Autenticação: a camada zero

Enviar arquivo exige sessão. A home e a view que entrega `/media/` estão sob
`@login_required`, com as views prontas do `django.contrib.auth` — `LoginView` e
`LogoutView`, sem app de terceiros, template próprio em
`core/templates/registration/login.html`.

Quem não entrou é redirecionado para `/accounts/login/?next=…`, e isso vale
também para baixar: não adianta ter a URL de um arquivo, porque a entrega passa
pela mesma verificação. O documento guarda **quem** enviou, numa chave
estrangeira para `auth_user`.

**Limite honesto:** o controle é de autenticação, não de autorização. Qualquer
pessoa autenticada vê e baixa tudo. Um próximo passo natural seria restringir a
lista ao próprio dono, ou usar o sistema de permissões do Django.

### Assinatura em vez de confiança na extensão

Extensão é o sobrenome do arquivo: qualquer um renomeia. `validate_conteudo_arquivo`
lê os primeiros 16 bytes e compara com a assinatura que o formato exige — `%PDF-`
para PDF, `\x89PNG` para PNG, `PK\x03\x04` para os formatos que são ZIP por dentro
(docx, xlsx, odt, ods), `\xd0\xcf\x11\xe0` para os antigos do Office.

Um executável do Windows começa com `MZ`. Renomeado para `relatorio.pdf`, ele passa
pela camada 3 e morre na 4.

Para `txt` e `csv`, que não têm assinatura, a regra é negativa: o conteúdo não pode
ter byte nulo nem começar com assinatura binária conhecida.

**Limite honesto:** eu confiro o começo do arquivo, não o arquivo inteiro. Um PDF
com cabeçalho correto e conteúdo malicioso passaria. Uma biblioteca dedicada
(`python-magic`) cobriria mais formatos — está nos próximos passos.

### Na saída: tudo baixa, menos imagem

A view `servir_media` (em `core/views.py`) substituiu o `django.views.static.serve`
justamente para poder decidir isso:

1. o caminho é resolvido e tem de cair dentro de `MEDIA_ROOT` — **path traversal**;
2. a extensão tem de estar na lista aceita, senão é 404, mesmo que o arquivo exista
   no volume;
3. o `Content-Type` vem de uma **tabela fixa**, nunca de adivinhação e nunca do que
   o navegador declarou no upload;
4. só imagem rasterizada (`png`, `jpg`, `jpeg`, `gif`, `webp`) sai com
   `Content-Disposition: inline`. Todo o resto sai como `attachment` e **baixa**;
5. `X-Content-Type-Options: nosniff` impede o navegador de ignorar o tipo declarado.

`svg` não está na lista de upload nem na de exibição: SVG é XML e pode carregar
script.

### Cabeçalhos da resposta

- **Content-Security-Policy** (`core/middleware.py`): `default-src 'self'`,
  `object-src 'none'`, `frame-ancestors 'none'`, `form-action 'self'`.
- **X-Frame-Options: DENY** e **Referrer-Policy: same-origin**.
- Cookies de sessão e CSRF com `HttpOnly` e `SameSite=Lax`; as versões `Secure` e o
  HSTS ficam por variável de ambiente, porque só fazem sentido com TLS.

**Limite honesto:** a CSP não se aplica ao `/admin/`. Os templates do admin usam
script e estilo embutidos, e a política o quebraria. Como o admin exige login, o
risco é menor — mas é uma exceção consciente, não um esquecimento.

### E o banco

- **Injeção de SQL:** o ORM do Django parametriza toda consulta. O único SQL escrito
  à mão no projeto é o `SELECT 1` do `healthz`, que é constante e não recebe entrada.
  Tem teste guardando isso: um título com `'); DROP TABLE core_documento; --` é
  gravado como texto literal, e a tabela continua de pé.
- **Superfície de rede:** o serviço `db` não publica porta nenhuma. Só quem está na
  rede do Compose alcança o banco.
- **Consulta presa:** `statement_timeout` de 15s e `connect_timeout` de 5s nas
  `OPTIONS` da conexão. Uma consulta que passe disso é derrubada pelo próprio
  Postgres, em vez de prender um worker do Gunicorn.
- **Credenciais:** vêm do `.env`, que está no `.gitignore` e no `.dockerignore`.

**Limite honesto:** a aplicação conecta com o usuário dono do banco. O certo em
produção seria um papel separado, com permissão só nas tabelas que ela usa.

### E prompt injection?

**Não se aplica a este projeto.** Prompt injection é um ataque contra sistemas que
colocam texto não confiável dentro do prompt de um modelo de linguagem — o texto
chega como dado e é interpretado como instrução. Aqui não existe LLM em lugar
nenhum do fluxo: nada lê o conteúdo dos arquivos enviados.

Se o projeto ganhasse, por exemplo, um resumo automático dos documentos, aí a
superfície passaria a existir, e a defesa seria a mesma ideia das camadas acima:
tratar o conteúdo extraído como **dado não confiável**, nunca como instrução —
separando a instrução do sistema do conteúdo do usuário, limitando o que o modelo
pode acionar, e validando a saída antes de usá-la.

Vale dizer isso em voz alta se perguntarem: reconhecer que o ataque existe, e
explicar por que ele não tem onde acontecer aqui, é melhor do que inventar uma
defesa para um risco que o projeto não tem.

---

## 6. Checklist antes de começar

- [ ] Docker Desktop **aberto e rodando** (checar com `docker info`)
- [ ] `docker compose up --build -d` já executado, stack no ar
- [ ] `docker compose ps` mostrando os três serviços, `db` como `healthy`
- [ ] Um arquivo pequeno de teste (PDF ou imagem, < 2 MB) já separado na área de trabalho
- [ ] Um arquivo **inválido** também separado, para mostrar a validação: renomeie
      qualquer coisa para `teste.exe`
- [ ] Um arquivo **já enviado antes** da apresentação, para a home não estar vazia
- [ ] Navegador aberto em `http://localhost:8080/`
- [ ] Terminal aberto na pasta do projeto, com fonte grande
- [ ] `apresentacao-defesa.html` aberto no navegador, em tela cheia (`F`) e com as notas à mão (`N`)

---

## 7. Roteiro da demo

```bash
docker compose ps
```
Três serviços em execução, `db` marcado como `healthy`.

```bash
curl http://localhost:8080/healthz/
```
Retorna `{"status": "ok"}` — a view roda `SELECT 1` no Postgres, então isso prova
que a aplicação está falando com o banco.

**No navegador**, em `http://localhost:8080/`. A primeira tela é o login — vale
mostrar de propósito, porque prova o controle de acesso em dois segundos. Depois
de entrar:

1. **Mostrar a validação primeiro.** Escolher o `teste.exe`, enviar, e deixar a
   mensagem de erro na tela: *"Extensão .exe não é aceita. Permitidas: pdf, doc,
   …"*. Dizer que quem barrou foi o validador do model, no servidor — o `accept`
   do input é só conveniência do navegador e não vale como segurança.
2. **Agora o caminho feliz.** Título + arquivo válido → Enviar. A mensagem de
   sucesso aparece e o arquivo entra na lista, com nome, tamanho e data.
3. Clicar no link para baixar — a URL é `/media/uploads/<nome>`. O nginx
   encaminha para a aplicação, que lê o arquivo do volume e devolve.

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

Se o Docker travar ou a demo não subir: **ir direto para o slide 5**, que tem o
mesmo teste em texto, e explicar o raciocínio. Não insistir em debugar ao vivo —
isso queima o tempo e a impressão. Uma frase pronta: *"o ambiente não está
colaborando agora; o comportamento é este aqui, e o repositório sobe com um
comando só."*

---

## 8. Perguntas prováveis

### Sobre computação em nuvem

**Isso é IaaS, PaaS ou SaaS?**
Do jeito que está, **IaaS**: os containers rodam numa máquina cujo sistema
operacional eu administro. Subindo a mesma imagem num serviço gerenciado de
containers, vira CaaS/PaaS — e o código não muda. É esse o ponto da
portabilidade.

**Qual a diferença entre container e máquina virtual?**
A VM virtualiza hardware: um hypervisor entrega CPU, memória e disco virtuais, e
dentro roda um SO convidado inteiro. O container virtualiza o sistema
operacional: os processos usam o kernel do host, isolados por *namespaces* e
limitados por *cgroups*. Container sobe em segundos e ocupa megabytes; VM sobe em
minutos e ocupa gigabytes. Em troca, a VM isola melhor e pode rodar um SO
diferente do host.

**Isso é elástico?**
Escala **horizontalmente** no nível de rede — `docker compose up --scale web=3`
funciona, porque o `upstream` do nginx resolve o nome do serviço e balanceia.
Elasticidade automática, não: não há métrica disparando criação de réplica. E
antes de escalar de verdade, duas coisas mudam: o `migrate` sai do boot, e o
volume local vira *object storage*, porque volume local não é visto por réplicas
em nós diferentes.

**O que é vendor lock-in, e como o projeto se protege?**
É ficar preso a um fornecedor por depender de serviços proprietários dele. Aqui a
unidade de entrega é uma imagem OCI e um arquivo declarativo — nada no código
conhece provedor nenhum. Trocar de nuvem é subir a mesma imagem em outro lugar.

**O que é orquestração, e onde ela está aqui?**
É quem decide o que roda, onde, quantas réplicas, e o que fazer quando algo cai.
O Compose faz a versão de um host só: ordem de subida com `depends_on`,
reinício com `restart: unless-stopped`, rede e volumes. Kubernetes e ECS fazem o
mesmo em escala de cluster, com agendamento entre nós.

**Por que a aplicação precisa ser stateless?**
Porque em nuvem a instância é descartável: ela pode ser substituída por uma
atualização, por auto-scaling ou por falha de hardware. Se o estado morasse
dentro dela, cada troca perderia dados. Por isso o banco está em serviço
separado e o upload em volume — a analogia de gado, não bicho de estimação.

**Como o custo entra nessa conta?**
O modelo de nuvem é pagamento por uso. Container ajuda porque a densidade é maior
(mais aplicações por máquina) e porque escalar é adicionar réplica pequena em vez
de comprar uma máquina maior — escala horizontal em vez de vertical.

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

**Por que só uma dependência de sistema, e por que essa?**
O `postgresql-client` entra pelo `pg_isready`, que o `entrypoint.sh` usa para
esperar o banco. O driver não precisa de nada do sistema: o `requirements.txt`
pede `psycopg[binary]`, e o extra `binary` empacota a própria `libpq` dentro da
wheel — é o que dispensa compilador no build. Dá para provar ao vivo:

```bash
docker compose exec web python -c "import psycopg; print(psycopg.pq.__impl__)"
```

Devolve `binary`. A `libpq5` do sistema até é instalada, mas como dependência do
`postgresql-client`, e o driver não a usa. Eu cheguei a declará-la explicitamente
no `Dockerfile` e removi depois de verificar isso.

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

**Como funciona a autenticação?**
Com as views prontas do `django.contrib.auth`: `LoginView` e `LogoutView`,
apontadas em `config/urls.py` por `include("django.contrib.auth.urls")`. Só o
template é meu. A home e a entrega de `/media/` usam o decorador
`@login_required`, e o `LOGIN_URL` no `settings.py` diz para onde mandar quem não
tem sessão. A senha vai para o banco com o hasher padrão do Django (PBKDF2), e o
cookie de sessão é `HttpOnly` e `SameSite=Lax`.

**Quem pode ver os arquivos dos outros?**
Hoje, qualquer pessoa autenticada. É autenticação, não autorização — e está
listado como limite consciente. Para separar por dono bastaria filtrar a lista
por `request.user` e checar o dono na view que serve a mídia.

**Por que dois volumes, e não um só?**
Porque eles guardam coisas com ciclos de vida diferentes. O `postgres_data` é
escrito pelo processo do Postgres, que precisa mandar sozinho naquele diretório,
e se recupera com `pg_dump`/`restore`. O `media_data` guarda arquivo de usuário,
que se copia com `tar`. Juntar os dois num volume só misturaria permissões e
tornaria o backup de um dependente do outro.

O que eu **removi** foi o terceiro: havia um `static_data` para a saída do
`collectstatic`, e ele era redundante. Aquele diretório é regenerado a cada boot
a partir da própria imagem — não é estado, é resultado derivado. Persistir isso
só acumula arquivo de build antigo. Hoje `/vol/static` é um diretório comum na
camada do container.

**Se o container do banco morrer, eu perco os dados?**
Não, e é a mesma história do upload. O container do Postgres é tão descartável
quanto o da aplicação: o que persiste é o volume `postgres_data`, montado em
`/var/lib/postgresql/data`. Container novo, mesmo volume, mesmos dados.

Vale explicitar a simetria, porque é o que mostra que a regra é geral e não um
truque para o upload: **os três containers são descartáveis**. O `web` e o `db`
têm cada um o seu volume; o `nginx` não tem nenhum, porque não há nada nele que
precise sobreviver — ele só encaminha requisição.

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
conexão para streaming e prende o arquivo ao ciclo de vida do banco. O padrão é
guardar os bytes no storage e só o caminho na tabela — que é exatamente o que o
`FileField` do Django faz.

**Como você faria o backup?**
Duas coisas separadas. O banco, com `docker compose exec db pg_dump -U appuser appdb`.
Os arquivos, empacotando o volume:
`docker run --rm -v django-docker-upload_media_data:/data -v "$PWD":/backup alpine tar czf /backup/media.tgz /data`.

**E se eu rodar `docker compose down -v`?**
Aí os arquivos somem — é o único comando do fluxo normal que apaga os volumes. É
exatamente a diferença que eu mostrei no slide 5.

### Sobre nginx e rede

**O que é um proxy reverso?**
É um servidor que recebe a requisição do cliente em nome do servidor de aplicação.
O navegador só conversa com o nginx; quem fala com o Gunicorn é o nginx, pela rede
interna. Isso me dá um ponto único de entrada para aplicar limites e, no futuro,
encerrar o TLS.

**Quem serve `/static/` e `/media/`?**
A aplicação. O nginx aqui é proxy reverso e nada mais: não monta volume e não lê
arquivo. Como o `django.contrib.staticfiles` só serve com `DEBUG` ligado, e a
`MEDIA_URL` nunca é servida automaticamente, as duas rotas são declaradas à mão
em `app/config/urls.py`, com a view `django.views.static.serve` apontando para
`STATIC_ROOT` e `MEDIA_ROOT`.

**E qual é o custo disso?** Cada download ocupa um worker do Gunicorn enquanto
dura, e o arquivo passa pelo interpretador Python em vez de sair por chamada de
sistema. Em troca, o proxy tem um papel só e os volumes ficam num container
único. Se o volume de download crescesse, o caminho seria devolver `/static/` e
`/media/` ao nginx, ou usar WhiteNoise na aplicação.

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

### Sobre o schema e os arquivos

**Qual é o schema da tabela?**
Cinco colunas em `core_documento`: `id` (`bigint`, chave primária gerada),
`titulo` (`varchar(200)`), `arquivo` (`varchar(100)`), `enviado_em`
(`timestamptz`) e `enviado_por_id` (`integer`, chave estrangeira para
`auth_user`). As quatro primeiras são `NOT NULL`; a última aceita nulo, porque os
registros criados antes de o login existir não têm dono. Dá para conferir ao
vivo:

```bash
docker compose exec db psql -U appuser -d appdb -c "\d core_documento"
```

**Por que `varchar(100)` no `arquivo`?**
É o `max_length` padrão do `FileField` do Django. Ele guarda o **caminho relativo
a `MEDIA_ROOT`** — no banco que está no ar, por exemplo, `uploads/prova.txt`. Se
os caminhos fossem ficar longos, bastaria aumentar o `max_length` e gerar uma
migração.

**Por que `timestamptz` e não `timestamp`?**
Porque `USE_TZ = True`: o Postgres guarda em UTC e o Django converte para
`America/Sao_Paulo` na hora de exibir. Assim a data não muda de significado se o
servidor mudar de fuso.

**Quantas tabelas o banco tem?**
Onze. Uma é minha (`core_documento`) — e ela aponta para `auth_user` pela chave
estrangeira `enviado_por_id`. As outras dez vêm das migrações do próprio
Django — autenticação (`auth_user`, `auth_group`, `auth_permission` e as de
relacionamento), `django_session`, `django_admin_log`, `django_content_type` e
`django_migrations`, que é o controle das migrações já aplicadas.

**Como o caminho do arquivo é montado?**
Em três pedaços: o `MEDIA_ROOT` do `settings.py` (`/vol/media`, que é o ponto de
montagem do volume), o `upload_to` do model (`uploads/`) e o nome do arquivo. No
disco vira `/vol/media/uploads/prova.txt`; no banco fica só `uploads/prova.txt`.
É por isso que mudar o `MEDIA_ROOT` não invalida os registros.

**E se dois arquivos tiverem o mesmo nome?**
O storage do Django detecta a colisão e acrescenta um sufixo aleatório ao nome —
nada é sobrescrito. Tem teste cobrindo:
`test_arquivos_de_mesmo_nome_nao_se_sobrescrevem`.

**O usuário pode escolher o caminho e escapar da pasta?**
Não. O `upload_to` fixa a subpasta, e o Django trata o nome recebido antes de
gravar. O que chega do navegador é usado como nome, não como caminho.

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
em `STATIC_ROOT`, que aqui é `/vol/static`, e é a aplicação que serve `/static/`.

Repare que `/vol/static` **não é um volume**: é um diretório comum na camada de
escrita do container. Não precisa persistir, porque o `collectstatic` roda a cada
boot e refaz tudo a partir da imagem. Guardar saída derivada em volume só
acumularia arquivo de build antigo que ninguém remove.

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
devolver `Content-Disposition: attachment` na resposta da view que serve
`/media/`, ou servir a mídia de um domínio separado — está nos próximos passos.

Vale ser honesta sobre o limite do que eu validei: eu checo **extensão**, não o
conteúdo do arquivo. Alguém pode renomear um executável para `.pdf` e ele passa.
Validar de verdade exigiria inspecionar os bytes iniciais, com `python-magic` ou
equivalente. Para o escopo deste trabalho, extensão e tamanho cobrem o caso de
uso; em produção eu acrescentaria a checagem de conteúdo.

**O que faltaria para isso ir a produção?**
TLS no nginx, segredos fora de arquivo, backup automatizado dos dois volumes
(`pg_dump` para o banco, `tar` para a mídia),
centralização de logs, e um pipeline de CI rodando os testes antes do deploy.

### Sobre escala

**Como você escalaria isso?**
`docker compose up --scale web=3` já funciona no nível de rede, porque o
`upstream` do nginx resolve o nome do serviço e balanceia entre as réplicas. Mas
duas coisas teriam de mudar antes: tirar o `migrate` do entrypoint, e trocar o
volume local por um storage compartilhado (S3 ou MinIO), porque um volume local
não é visto por réplicas em nós diferentes.

---

## 9. Perguntas sobre o formulário e a validação

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
São 41 testes em `app/core/tests.py`, rodando com
`docker compose exec web python manage.py test core`. Eles cobrem o caminho
feliz, a rejeição por extensão, a rejeição por tamanho, o limite exato, extensão
em maiúsculas, arquivo sem extensão, o `full_clean()` do model direto, e o POST
na home com redirect e mensagem. Cada teste usa um `MEDIA_ROOT` temporário
próprio, porque o banco volta atrás entre os testes mas o disco não.

**O que acontece se dois arquivos tiverem o mesmo nome?**
O storage do Django detecta a colisão e acrescenta um sufixo aleatório — nada é
sobrescrito. Tem um teste cobrindo isso.

---

## 10. Frases de segurança

Para quando travar ou vier uma pergunta fora do previsto:

- *"Não testei esse cenário específico, mas pelo que está configurado, o
  comportamento esperado seria X — e dá para verificar com Y."*
  Honesto, e mostra raciocínio em vez de chute.
- *"Essa é uma limitação consciente, está no slide de próximos passos."*
- *"Deixa eu mostrar no código."* — abrir o arquivo é sempre mais forte do que
  descrever de memória.

Nunca inventar um número ou um comportamento. Se não souber, dizer que não sabe e
explicar como descobriria.
