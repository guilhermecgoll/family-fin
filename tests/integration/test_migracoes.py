from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect

import financas.adapters.db.modelos  # noqa: F401 - registra as tabelas no metadata
from financas.adapters.db.base import Base

TABELAS = {
    "pessoa",
    "categoria",
    "forma_pagamento",
    "forma_pagamento_usuario",
    "compra_parcelada",
    "lancamento",
    "comprovante",
}


def _tabelas(engine):
    return set(inspect(engine).get_table_names()) - {"alembic_version"}


def test_migracoes_criam_as_tabelas_dos_modelos(engine):
    assert _tabelas(engine) == TABELAS == set(Base.metadata.tables)


def test_migracoes_revertem_e_reaplicam(engine, alembic_config):
    command.downgrade(alembic_config, "base")
    assert _tabelas(engine) == set()

    command.upgrade(alembic_config, "head")
    assert _tabelas(engine) == TABELAS


def test_modelos_e_migracoes_estao_em_sincronia(engine):
    """Falha se um modelo mudou sem a migração correspondente."""
    with engine.connect() as conexao:
        diferencas = compare_metadata(MigrationContext.configure(conexao), Base.metadata)

    assert diferencas == []
