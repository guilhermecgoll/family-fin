import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

PASTA = Path(__file__).parent
RAIZ = PASTA.parents[1]


def pytest_collection_modifyitems(items):
    for item in items:
        if PASTA in item.path.parents:
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session")
def postgres_url():
    """URL do Postgres descartável dos testes (serviço `db-test` do compose).

    Sem TEST_DATABASE_URL, os testes são pulados, exceto com EXIGIR_BANCO_TESTE=1 (CI).
    """
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        if os.environ.get("EXIGIR_BANCO_TESTE") == "1":
            pytest.fail("TEST_DATABASE_URL não definida")
        pytest.skip("TEST_DATABASE_URL não definida; rode via docker compose run --rm dev")
    return url


@pytest.fixture(scope="session")
def alembic_config(postgres_url):
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("DATABASE_URL", postgres_url)  # lida pelo migrations/env.py
        yield Config(RAIZ / "alembic.ini")


@pytest.fixture(scope="session")
def engine(postgres_url, alembic_config):
    """Banco no esquema da última migração, recriado do zero a cada execução."""
    engine = create_engine(postgres_url)
    with engine.begin() as conexao:
        conexao.execute(text("DROP SCHEMA public CASCADE"))
        conexao.execute(text("CREATE SCHEMA public"))
    command.upgrade(alembic_config, "head")
    yield engine
    engine.dispose()


@pytest.fixture
def sessao(engine):
    """Sessão cujas alterações são desfeitas ao fim do teste, mesmo com commit."""
    with engine.connect() as conexao:
        transacao = conexao.begin()
        with Session(bind=conexao, join_transaction_mode="create_savepoint") as sessao:
            yield sessao
        transacao.rollback()


@pytest.fixture
def banco_limpo(engine):
    """Para testes que gravam por conta própria: apaga todos os dados ao final."""
    yield engine
    with engine.begin() as conexao:
        tabelas = conexao.scalars(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
            )
        ).all()
        conexao.execute(text(f"TRUNCATE {', '.join(tabelas)} RESTART IDENTITY CASCADE"))
