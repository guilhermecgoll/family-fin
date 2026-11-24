# Finanças da Família

App de finanças pessoais de uma família: lançamento de despesas e receitas por um bot do Telegram (texto livre ou foto do comprovante), fluxo de caixa por categoria e forma de pagamento, e lista de compras compartilhada numa página web para celular.

A especificação completa está em `docs/spec.md`. Leia antes de implementar qualquer funcionalidade e mantenha-a atualizada quando uma decisão mudar.

@docs/spec.md

## Stack

- Python 3.12+
- FastAPI (web/API) + templates Jinja + HTMX (página para celular, sem frontend separado)
- python-telegram-bot (bot)
- PostgreSQL + SQLAlchemy 2.x + Alembic (migrações)
- Gemini Flash via API paga (extração de lançamentos de texto e imagem)
- Docker Compose com os serviços `web`, `bot`, `db`, `cloudflared` e `backup`
- Exposição via Cloudflare Tunnel com Cloudflare Access; o usuário logado vem do cabeçalho `Cf-Access-Authenticated-User-Email`

## Estrutura do projeto

```
src/financas/
  domain/        # regras de negócio puras (sem I/O): competência da fatura, lançamentos, lista de compras
  services/      # casos de uso que orquestram domínio + repositórios + integrações
  adapters/
    db/          # modelos SQLAlchemy e repositórios
    llm/         # cliente Gemini atrás da interface de extração
    telegram/    # handlers do bot
  web/           # rotas FastAPI e templates
  config.py      # configuração via variáveis de ambiente
migrations/      # Alembic
tests/
  unit/          # sem banco, sem rede
  integration/   # Postgres real em container
docs/specs/spec.md
docker-compose.yml
```

## Regras de código

- Regras de negócio ficam em `domain/` como funções ou classes puras, sem acesso a banco, rede ou relógio do sistema (receber a data como parâmetro).
- Gemini e Telegram ficam atrás de interfaces (`Protocol`) para serem substituídos por dublês nos testes.
- Valores monetários em `Decimal` (nunca `float`); no banco, `NUMERIC(12, 2)`.
- Datas sem fuso para data real e mês de competência; timestamps em UTC.
- O mês de competência é calculado no domínio e gravado no lançamento. No cartão de crédito, o custo cai no mês de vencimento da fatura; o fechamento aceita dia fixo ou "último dia do mês".
- Só os IDs do Telegram e os e-mails do Cloudflare Access configurados têm acesso; qualquer outro é ignorado.
- Segredos (token do bot, chave do Gemini, credenciais do banco e do rclone) só por variáveis de ambiente; nunca no repositório.
- O repositório é público: nenhum dado pessoal no código, nos testes, nas migrações ou na documentação. Membros, IDs do Telegram, e-mails, formas de pagamento e datas do cartão vêm do `.env` e de `config/seed.local.yaml`, ambos no `.gitignore`. Versionar só `.env.example` e `config/seed.example.yaml` com dados fictícios.
- Workflows de CI nunca rodam no runner self-hosted a partir de pull requests; o deploy roda só em push na branch principal.

## Testes e qualidade

- Toda funcionalidade nova vem com testes unitários. Cobertura mínima de 90%; o CI falha abaixo disso.
- `pytest tests/unit` precisa rodar sem Docker nem rede.
- Testes de integração em `tests/integration`, contra Postgres em container.
- `ruff check` e `ruff format` sem erros antes de qualquer commit.

## Comandos

```bash
uv sync                                  # instalar dependências
uv run pytest tests/unit                 # testes unitários
uv run pytest --cov=financas --cov-fail-under=90
uv run ruff check . && uv run ruff format --check .
uv run alembic upgrade head              # aplicar migrações
docker compose up -d --build             # subir tudo
```

## Ordem de implementação sugerida

1. Esqueleto do projeto, Compose com `db`, Alembic, pytest, ruff e CI no GitHub Actions.
2. Domínio: categorias, formas de pagamento, lançamentos e cálculo do mês de competência.
3. Bot: lançamento por texto com confirmação estruturada antes de gravar.
4. Lançamento por foto do comprovante.
5. Página web: fluxo de caixa do mês.
6. Lista de compras.
7. Backup diário para o Google Drive via rclone criptografado.
8. Deploy contínuo por runner self-hosted no notebook de casa.
