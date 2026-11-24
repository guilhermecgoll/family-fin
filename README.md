# family-fin

Finanças da família: lançamento de despesas e receitas por um bot do Telegram, fluxo de caixa por categoria e forma de pagamento, e lista de compras compartilhada numa página web para celular.

- Especificação: [`docs/spec.md`](docs/spec.md)
- Plano de implementação: [`docs/plan.md`](docs/plan.md)

## Desenvolvimento

Só é preciso Docker com Compose (ex.: no WSL). Python, uv e as ferramentas rodam no serviço `dev`.

```bash
scripts/criar-env.sh          # cria o .env com senha aleatória do banco (uma vez)
docker compose build dev      # imagem de desenvolvimento
docker compose up -d db       # banco da aplicação
docker compose run --rm --no-deps dev uv run alembic upgrade head

# dados da família: copie config/seed.example.yaml para config/seed.local.yaml e edite
docker compose run --rm --no-deps dev uv run python -m financas.seed config/seed.local.yaml
```

O seed pode ser rodado de novo depois de editar o arquivo: atualiza pessoas e formas de pagamento pelo nome e não duplica nada.

Testes e qualidade:

```bash
# todos, com cobertura (sobe o db-test, Postgres em memória, automaticamente)
docker compose run --rm dev uv run pytest --cov=financas --cov-fail-under=90

# só unitários
docker compose run --rm dev uv run pytest tests/unit

# lint e formatação
docker compose run --rm --no-deps dev sh -c "uv run ruff check . && uv run ruff format --check ."

# depois de mudar dependências no pyproject.toml
docker compose run --rm --no-deps dev uv lock
```

O serviço `dev` roda com o mesmo UID/GID do host (gravados no `.env` pelo script), para que os arquivos criados no projeto não mudem de dono. Para limpar os containers de desenvolvimento: `docker compose --profile dev down`.

## Dados pessoais

O repositório é público. Membros, IDs do Telegram, e-mails, formas de pagamento e datas do cartão ficam só no `.env` e em `config/seed.local.yaml`, ambos fora do Git. Os arquivos versionados (`.env.example`, `config/seed.example.yaml`) têm apenas dados fictícios.
