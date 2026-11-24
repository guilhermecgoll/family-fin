# Plano de implementação — Fase 1

Plano de execução da especificação em `docs/spec.md`. Cada etapa é entregue em uma branch própria e um PR com testes, cobertura ≥ 90%, `ruff check` e `ruff format --check` limpos. Quando uma decisão mudar durante a implementação, atualizar a spec e este plano no mesmo PR.

Legenda: **Entregas** (o que é produzido), **Testes** (o que precisa estar coberto), **Pronto quando** (critério de aceite).

---

## Etapa 1 — Esqueleto do projeto

**Entregas**

- `pyproject.toml` gerenciado por `uv`: Python 3.12+, pacote `financas` em `src/`, dependências de runtime e grupo `dev` (pytest, pytest-cov, ruff). Nada instalado no host: `Dockerfile` com estágio `dev` (uv dentro da imagem, venv em volume) e `scripts/criar-env.sh` para gerar o `.env` com senha aleatória do banco.
- Estrutura de pastas do `CLAUDE.md`, com `__init__.py` vazios.
- `src/financas/config.py` com `pydantic-settings`: `DATABASE_URL`, `TELEGRAM_BOT_TOKEN`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `TELEGRAM_ALLOWED_IDS`, `ACCESS_ALLOWED_EMAILS`, `TIMEZONE` (padrão `America/Sao_Paulo`), `APP_ENV` (`dev`/`prod`). Nenhum valor padrão para segredos.
- `docker-compose.yml` com `db` (Postgres 16, volume nomeado, healthcheck) e, no profile `dev`, o serviço `dev` (ferramentas) e o `db-test` (Postgres em memória para os testes de integração). Os demais serviços entram nas etapas em que forem necessários.
- Alembic configurado (`alembic.ini`, `migrations/env.py` lendo `DATABASE_URL` de `config.py`, metadata do SQLAlchemy). Sem migrações ainda.
- `ruff` configurado no `pyproject.toml` (regras: E, F, I, UP, B, SIM, S para segurança; linha 100).
- `pytest` configurado: `testpaths`, marcador `integration`, `--strict-markers`.
- `.pre-commit-config.yaml` (opcional, exige pre-commit no host): ruff e ruff-format via container, `gitleaks` via Docker (repositório público) e checagens básicas.
- `.gitignore` incluindo `.env`, `config/seed.local.yaml`, `.venv`, caches.
- `.env.example` e `config/seed.example.yaml` com dados fictícios.
- `.github/workflows/ci.yml`: gatilhos `push` e `pull_request`; `runs-on: ubuntu-latest` (nunca self-hosted); jobs `lint` (ruff + gitleaks) e `test` (unitários e integração contra o `db-test`, cobertura combinada com `--cov-fail-under=90`). Permissões mínimas (`contents: read`).
- README com os comandos de desenvolvimento.

**Testes**

- `config.py`: leitura de variáveis, parsing das listas de IDs/e-mails, erro quando segredo obrigatório falta.
- Teste de integração de fumaça: roda `alembic upgrade head` e `downgrade base` contra o `db-test`.

**Pronto quando** o CI passa no GitHub, `docker compose run --rm dev uv run pytest tests/unit` roda sem banco nem rede e `docker compose up -d db` sobe o banco saudável.

---

## Etapa 2 — Domínio, banco e seed

### 2.1 Domínio puro (`domain/`)

- `tipos.py`: enums `TipoLancamento` (despesa/receita), `TipoForma` (dinheiro, pix, débito, vale-refeição, crédito), `StatusLancamento` (ativo/antecipada); dataclasses imutáveis `Pessoa`, `Categoria`, `FormaPagamento`, `Lancamento`, `CompraParcelada`. Valores em `Decimal`; mês de competência representado como `date` no dia 1.
- `competencia.py`:
  - `data_fechamento(ano, mes, forma)`: dia fixo limitado ao último dia do mês, ou último dia quando `fecha_ultimo_dia`.
  - `mes_competencia(data_real, forma)`: não crédito → mês da data real; crédito → descobre o mês de fechamento (compra até o fechamento → fecha no mês; depois → mês seguinte) e aplica a regra do vencimento (mesmo mês se `dia_vencimento > dia_fechamento`, senão mês seguinte; com `fecha_ultimo_dia`, sempre mês seguinte).
- `parcelamento.py`:
  - `gerar_parcelas(data_real, forma, n, valor_total=None, valor_parcela=None)`: exatamente um dos dois valores; resto de centavos na primeira parcela; parcela k = competência da 1ª + (k−1) meses. Só para crédito; n ≥ 2.
  - `antecipar(parcelas, quantidade, valor_pago, data_solicitacao, forma)`: elegíveis são as parcelas ativas com competência posterior à competência da data de solicitação; abate as de maior número; devolve parcelas a marcar como `antecipada` e o lançamento de adiantamento (competência pela regra da fatura na data da solicitação). Erros: quantidade maior que as elegíveis, valor pago ≤ 0 ou maior que a soma abatida.
  - `economia(compra)`: soma das parcelas antecipadas − soma dos adiantamentos.
- `regras.py`: validações de um lançamento — categoria do mesmo tipo do lançamento; receita sem forma de pagamento; despesa com forma que a pessoa pode usar; valor > 0.

### 2.2 Persistência (`adapters/db/`)

- Modelos SQLAlchemy 2.x (tipados, `Mapped[...]`): `pessoa`, `categoria`, `forma_pagamento`, `forma_pagamento_usuario` (N:N dos usuários permitidos), `lancamento`, `compra_parcelada`, `comprovante` (criada aqui, usada na etapa 4). `NUMERIC(12,2)`, `DATE` para datas reais e competência, `TIMESTAMPTZ` em UTC para `registrado_em`/`criado_em`.
- Restrições no banco: `CHECK` de valor > 0, de campos de fatura só no crédito, de `numero_parcela` com `compra_parcelada`; índice em `(mes_competencia, status)`.
- Migração `0001_inicial` gerada e revisada à mão.
- Repositórios com interface `Protocol` em `services/` e implementação SQLAlchemy aqui; conversão modelo ↔ dataclass de domínio.

### 2.3 Seed

- `python -m financas.seed config/seed.local.yaml`: pessoas, formas de pagamento (com usuários permitidos e datas do cartão) e categorias iniciais da spec. Idempotente (upsert por nome/e-mail); não apaga o que foi criado pela família.
- Categorias iniciais ficam no código (não são dado pessoal); pessoas e formas só no YAML.

**Testes**

- Unitários com tabela de casos para `mes_competencia`: os dois exemplos da spec, compra no dia do fechamento, virada de ano, fevereiro com fechamento 30/31, ano bissexto, vencimento antes/depois do fechamento.
- Parcelamento: divisão exata e com resto, valor da parcela informado, parcelas atravessando o ano; antecipação do exemplo da spec (10x, na parcela 3, adianta 5 → abate 6–10), quantidade inválida, data de solicitação após um fechamento.
- Integração (contra o `db-test`): migração aplica e reverte; repositórios gravam e leem; seed rodado duas vezes não duplica.

**Pronto quando** o domínio está coberto por testes de tabela e `alembic upgrade head` + seed populam um banco vazio.

---

## Etapa 3 — Bot: lançamento por texto

### 3.1 Extração (`adapters/llm/`)

- Interface `Extrator(Protocol)` com `interpretar_texto(texto, contexto) -> Interpretacao`. O `contexto` traz data de hoje, pessoa autora, membros, categorias por tipo e formas que a pessoa pode usar.
- `Interpretacao` (Pydantic) com `intencao` (`lancamento`, `adiantamento`, `item_lista`, `consulta`, `desconhecido`) e os campos do rascunho (valor como string decimal, descrição, data, categoria, forma, pessoa, parcelas/valor da parcela; ou itens da lista).
- Implementação Gemini com `google-genai`, saída estruturada (`response_schema`), modelo em `GEMINI_MODEL`, timeout e uma nova tentativa. Nomes devolvidos pela IA são casados com os cadastrados; nome desconhecido vira campo ausente.
- Dublê `ExtratorFalso` para testes.

### 3.2 Rascunho e fluxo (`domain/rascunho.py`, `services/lancar.py`)

- `Rascunho`: campos preenchidos, campos faltantes na ordem em que serão perguntados (valor → forma → categoria), aplicação de correção por campo, conversão em `Lancamento`(s) já com competência calculada (e parcelas, se houver).
- Rascunhos pendentes persistidos em tabela `rascunho` (JSONB, autor, chat, expiração de 24 h), para sobreviver a reinício do bot no deploy.
- `services/lancar.py`: interpretar → criar rascunho → aplicar respostas → confirmar (grava) → desfazer.
- Adiantamento de parcelas no mesmo fluxo: escolha da compra parcelada em aberto, pergunta obrigatória da data da solicitação (hoje / ontem / outra), quantidade e valor pago, resumo e confirmação.

### 3.3 Telegram (`adapters/telegram/`)

- `python-telegram-bot` em modo polling; serviço `bot` entra no Compose.
- Filtro de acesso aplicado antes de qualquer handler: usuário fora de `TELEGRAM_ALLOWED_IDS` é ignorado sem resposta; o mesmo para chats de grupo não autorizados.
- Resumo do lançamento em mensagem com teclado inline: Confirmar, um botão por campo para corrigir, Cancelar. `callback_data` curto (`id do rascunho:ação`).
- Corrigir campo: lista de opções para categoria, forma, pessoa e data (hoje/ontem/outra); texto digitado para valor e descrição.
- Após gravar: mensagem final com botão "Desfazer" válido por 10 minutos e só para o autor (prazo verificado no serviço, com o relógio injetado). Depois do prazo, o botão responde que o lançamento deve ser desfeito pela web.
- Interface `Mensageiro(Protocol)` para o envio, para os serviços (e o aviso de backup) não dependerem do Telegram diretamente.

**Testes**

- Rascunho: ordem das perguntas, correções, conversão com e sem parcelas.
- Serviço com `ExtratorFalso` e repositórios em memória: fluxo feliz, campo faltando, desfazer, adiantamento.
- Handlers com objetos `Update` falsos: usuário não autorizado ignorado, montagem dos teclados, roteamento dos callbacks.
- Cliente Gemini: montagem do prompt/schema e parsing da resposta com resposta gravada (sem rede).

**Pronto quando** "mercado 230,50 no VR" no Telegram vira um lançamento confirmado no banco com competência correta, e uma compra "geladeira 3000 em 10x no crédito" gera 10 parcelas.

---

## Etapa 4 — Lançamento por foto do comprovante

- Extrator ganha `interpretar_imagem(bytes, mime, contexto)`; mesmo `Interpretacao` e mesmo fluxo de rascunho.
- `domain/comprovante.py` (puro, sobre bytes): redimensionar para lado maior ≤ 1600 px e recomprimir em JPEG com Pillow; recusar se > 1 MB após compressão.
- Aceitar foto e imagem enviada como arquivo (documento). PDF fica para depois.
- O comprovante é gravado junto com o lançamento confirmado; rascunho guarda a referência temporária.
- Rotina diária (JobQueue do bot) apaga comprovantes com `criado_em` > 12 meses.

**Testes**: compressão (imagem grande, pequena, PNG, acima do limite), fluxo com foto via dublê, rotina de limpeza com data injetada.

**Pronto quando** a foto de um cupom vira rascunho com valor e data extraídos e o comprovante fica no banco com ≤ 1 MB.

---

## Etapa 5 — Página web: fluxo de caixa

### 5.1 Infraestrutura

- Serviço `web` (FastAPI + Uvicorn) e `cloudflared` no Compose; `web` sem porta publicada no host em produção.
- Autenticação: middleware lê `Cf-Access-Authenticated-User-Email`, valida o JWT `Cf-Access-Jwt-Assertion` (assinatura pelas chaves públicas em `https://<ACCESS_TEAM_DOMAIN>/cdn-cgi/access/certs`, com cache; `aud` igual a `ACCESS_AUD`; expiração; e-mail do token igual ao do cabeçalho) e resolve a `Pessoa`; token ausente ou inválido → 401; e-mail fora de `ACCESS_ALLOWED_EMAILS` → 403. Biblioteca: `PyJWT` com `PyJWKClient`. Em `APP_ENV=dev`, `DEV_USER_EMAIL` substitui o cabeçalho.
- Migrações aplicadas por um serviço `migrate` (one-shot) do qual `web` e `bot` dependem.
- Layout Jinja mobile-first com HTMX e CSS próprio enxuto.

### 5.2 Relatórios (`services/relatorios.py`)

- Consultas agregadas por mês de competência, considerando só lançamentos `ativo`: resumo (receitas, despesas, saldo), por categoria, por forma de pagamento, por pessoa, evolução dos últimos 12 meses.
- Telas: resumo do mês com navegação ‹ mês ›; detalhamentos; evolução com barras em CSS.

### 5.3 Edição

- Lista de lançamentos do mês com filtros; editar e desfazer a qualquer momento, sem prazo, com confirmação (recalcula competência ao mudar data ou forma). Desfazer usa o mesmo serviço do bot: compra parcelada sai inteira; adiantamento devolve as parcelas abatidas para `ativo`. Em lançamento parcelado, a edição é na compra e regenera as parcelas ainda não antecipadas.
- Detalhe da compra parcelada: parcelas, adiantamentos e economia.
- CRUD de categorias (renomear, criar, arquivar; não apaga categoria em uso).

### 5.4 Consulta pelo bot

- Intenção `consulta` ("quanto gastamos com mercado este mês?"): a IA devolve filtros estruturados (período, categoria, forma, pessoa, termo da descrição) e o serviço de relatórios responde. A IA nunca calcula valores.

**Testes**: agregações com dados controlados (integração), middleware de acesso (cabeçalho ausente, e-mail não autorizado, JWT inválido), rotas com `TestClient` e repositórios falsos, consulta pelo bot com dublê.

**Pronto quando** cada membro acessa pelo celular via Cloudflare Access e vê o mês com cartão contado no mês da fatura.

---

## Etapa 6 — Lista de compras

Modelo de lista permanente, no estilo de uma nota de lista: pendentes em cima, comprados embaixo, sem sessões e sem duplicar itens.

### 6.1 Domínio (`domain/lista.py`)

- `normalizar(nome)`: caixa, acentos e espaços (`"  Água "` → `"agua"`); chave única do catálogo.
- `adicionar(lista, nome)`: devolve a ação a executar — item já pendente → nada; item comprado → desmarcar (sobe); item no catálogo mas fora da lista → incluir; item inexistente → criar no catálogo e incluir.
- `sugerir(prefixo, lista, catalogo, limite)`: primeiro os comprados da lista, depois os do catálogo que não estão na lista; casamento pelo nome normalizado (prefixo e depois "contém"); itens já pendentes não aparecem.
- Marcar/desmarcar/remover como transições puras sobre o estado do `ItemLista`.
- Ordem: `ordenar_pendentes` por `posicao`; `ordenar_comprados` alfabético pelo nome normalizado; `reordenar(pendentes, nova_ordem)` valida que a nova ordem contém exatamente os pendentes atuais (itens adicionados ou marcados por outra pessoa no meio do arraste são mantidos: os que faltam vão para o fim, os que já não estão pendentes são ignorados). Item incluído ou desmarcado recebe a maior posição + 1.

### 6.2 Persistência

- `item` (com `nome_normalizado` único), `lista_compras` (nome único entre as não arquivadas), `item_lista` (único por lista + item), `compra_item` (histórico de marcações).
- Operações concorrentes resolvidas no banco: `INSERT … ON CONFLICT` para adicionar e atualização condicional para marcar, de modo que dois toques simultâneos no mesmo item não dupliquem nem se percam.

### 6.3 Tempo real

- Toda alteração numa lista (web ou bot) dispara `NOTIFY lista_<id>` no Postgres, na mesma transação.
- O `web` mantém uma conexão `LISTEN` e repassa os eventos por Server-Sent Events (`/listas/{id}/eventos`) aos navegadores abertos naquela lista; a página usa a extensão SSE do HTMX para trocar só o trecho alterado.
- Batimento a cada ~25 s para a conexão não cair no Cloudflare Tunnel; ao reconectar (celular saiu do segundo plano), a página recarrega a lista inteira para não perder eventos.
- Como o `bot` roda em outro container, o `NOTIFY` pelo banco é o que liga as duas pontas; não há estado em memória compartilhado.

### 6.4 Interfaces

- Web: tela inicial com as listas; criar, renomear e arquivar lista. Tela da lista para uso no mercado: pendentes em cima, comprados embaixo recolhidos com contador, toque marca/desmarca (registra `marcado_por`), arrastar pela alça para reordenar os pendentes (SortableJS servido como arquivo estático do app; ao soltar, envia a nova ordem, o servidor regrava as posições numa transação e notifica os outros aparelhos), campo de adicionar com sugestões enquanto digita (HTMX com `hx-trigger="keyup changed delay:200ms"`), remover item da lista.
- Bot: intenção `item_lista` ("adiciona leite e ovos na lista") usa o mesmo `adicionar` do domínio; vai para a lista citada no texto, senão para a única existente; com várias, o bot pergunta com botões; sem nenhuma, cria "Mercado". A resposta diz o que foi incluído e o que voltou para os pendentes.

**Testes**: normalização e casos de `adicionar` (pendente, comprado, catálogo, novo), ordem das sugestões, ordem alfabética dos comprados com acentos, reordenação com lista alterada durante o arraste, concorrência de marcação e adição simultânea (integração), emissão do `NOTIFY` e entrega por SSE (integração), rotas e handler do bot.

**Pronto quando** duas pessoas com a mesma lista aberta no celular veem as marcações uma da outra em poucos segundos, um item adicionado pelo bot aparece na página sem recarregar, e digitar "agua" sugere "Água" dos comprados e o faz voltar para os pendentes.

---

## Etapa 7 — Backup

- Serviço `backup`: imagem com `pg_dump` e `rclone`, agendada com `supercronic`. Dump diário compactado, enviado ao remote `crypt` do Google Drive; configuração do rclone só por variáveis de ambiente/arquivo montado fora do Git.
- Retenção: 7 diários e 4 semanais (o dump de domingo é copiado para `semanal/`); os mais antigos apagados.
- Falha → aviso no Telegram pelo Bot API usando o mesmo token (sem depender do serviço `bot` estar no ar).
- Lógica de retenção em Python puro e testada; script de execução fino.
- `docs/restauracao.md` com o passo a passo; teste de restauração real feito e registrado antes do uso de verdade.

**Testes**: seleção de arquivos a apagar pela retenção com datas injetadas; montagem dos comandos; aviso de falha com `Mensageiro` falso.

**Pronto quando** um dump do Drive foi restaurado num banco vazio e o app subiu com os dados.

---

## Etapa 8 — Deploy contínuo

- Runner self-hosted no servidor doméstico, usuário sem privilégios com acesso só à pasta do projeto e ao Docker (registrar na doc que o grupo `docker` equivale a root na máquina).
- `.github/workflows/deploy.yml`: só `on: push` na `main`, `runs-on: self-hosted`, `environment: production`, `concurrency` para não haver deploys simultâneos; nunca em `pull_request`. Passos: checkout, `docker compose up -d --build`, aguardar healthchecks, teste de fumaça na rota `/saude`.
- Configuração do repositório: aprovação obrigatória para workflows de forks; proteção da `main` exigindo o CI verde.
- `.env` e `seed.local.yaml` ficam só no servidor.

**Pronto quando** um merge na `main` atualiza o servidor sem intervenção e um PR de fork não executa nada no runner.

---

## Pendências para decidir

1. **Comprovante em PDF**: fora da fase 1, salvo pedido.
