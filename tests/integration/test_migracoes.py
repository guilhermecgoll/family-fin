from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

RAIZ = Path(__file__).parents[2]


def test_migracoes_aplicam_e_revertem(postgres_url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    config = Config(RAIZ / "alembic.ini")

    command.upgrade(config, "head")
    engine = create_engine(postgres_url)
    try:
        assert "alembic_version" in inspect(engine).get_table_names()
        command.downgrade(config, "base")
    finally:
        engine.dispose()
