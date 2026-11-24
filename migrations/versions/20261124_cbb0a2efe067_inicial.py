"""Tabelas iniciais: pessoas, categorias, formas de pagamento, lançamentos e comprovantes.

Revision ID: cbb0a2efe067
Revises:
Create Date: 2026-11-24 14:28:00.801118
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "cbb0a2efe067"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categoria",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=100), nullable=False),
        sa.Column(
            "tipo",
            sa.Enum(
                "despesa",
                "receita",
                name="tipo_lancamento",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("arquivada", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categoria")),
        sa.UniqueConstraint("nome", "tipo", name=op.f("uq_categoria_nome")),
    )
    op.create_table(
        "compra_parcelada",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("descricao", sa.String(length=200), nullable=False),
        sa.Column("valor_total", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("num_parcelas", sa.SmallInteger(), nullable=False),
        sa.Column("data_real", sa.Date(), nullable=False),
        sa.CheckConstraint(
            "num_parcelas >= 2", name=op.f("ck_compra_parcelada_ao_menos_duas_parcelas")
        ),
        sa.CheckConstraint(
            "valor_total > 0", name=op.f("ck_compra_parcelada_valor_total_positivo")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_compra_parcelada")),
    )
    op.create_table(
        "pessoa",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=100), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=True),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pessoa")),
        sa.UniqueConstraint("email", name=op.f("uq_pessoa_email")),
        sa.UniqueConstraint("nome", name=op.f("uq_pessoa_nome")),
        sa.UniqueConstraint("telegram_user_id", name=op.f("uq_pessoa_telegram_user_id")),
    )
    op.create_table(
        "forma_pagamento",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=100), nullable=False),
        sa.Column(
            "tipo",
            sa.Enum(
                "dinheiro",
                "pix",
                "debito",
                "vale_refeicao",
                "credito",
                name="tipo_forma",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("dono_id", sa.Integer(), nullable=True),
        sa.Column("dia_fechamento", sa.SmallInteger(), nullable=True),
        sa.Column(
            "fecha_ultimo_dia", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("dia_vencimento", sa.SmallInteger(), nullable=True),
        sa.CheckConstraint(
            "(tipo = 'credito') = ((dia_fechamento IS NOT NULL) <> fecha_ultimo_dia)",
            name=op.f("ck_forma_pagamento_fechamento_so_no_credito"),
        ),
        sa.CheckConstraint(
            "(tipo = 'credito') = (dia_vencimento IS NOT NULL)",
            name=op.f("ck_forma_pagamento_vencimento_so_no_credito"),
        ),
        sa.CheckConstraint(
            "NOT (dia_fechamento IS NOT NULL AND fecha_ultimo_dia)",
            name=op.f("ck_forma_pagamento_fechamento_exclusivo"),
        ),
        sa.CheckConstraint(
            "dia_fechamento BETWEEN 1 AND 31", name=op.f("ck_forma_pagamento_dia_fechamento_valido")
        ),
        sa.CheckConstraint(
            "dia_vencimento BETWEEN 1 AND 31", name=op.f("ck_forma_pagamento_dia_vencimento_valido")
        ),
        sa.ForeignKeyConstraint(
            ["dono_id"],
            ["pessoa.id"],
            name=op.f("fk_forma_pagamento_dono_id_pessoa"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_forma_pagamento")),
        sa.UniqueConstraint("nome", name=op.f("uq_forma_pagamento_nome")),
    )
    op.create_table(
        "forma_pagamento_usuario",
        sa.Column("forma_pagamento_id", sa.Integer(), nullable=False),
        sa.Column("pessoa_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["forma_pagamento_id"],
            ["forma_pagamento.id"],
            name=op.f("fk_forma_pagamento_usuario_forma_pagamento_id_forma_pagamento"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["pessoa_id"],
            ["pessoa.id"],
            name=op.f("fk_forma_pagamento_usuario_pessoa_id_pessoa"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "forma_pagamento_id", "pessoa_id", name=op.f("pk_forma_pagamento_usuario")
        ),
    )
    op.create_table(
        "lancamento",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "tipo",
            sa.Enum(
                "despesa",
                "receita",
                name="tipo_lancamento",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("valor", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("descricao", sa.String(length=200), nullable=False),
        sa.Column("data_real", sa.Date(), nullable=False),
        sa.Column("mes_competencia", sa.Date(), nullable=False),
        sa.Column(
            "registrado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "ativo",
                "antecipada",
                name="status_lancamento",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("pessoa_id", sa.Integer(), nullable=False),
        sa.Column("autor_id", sa.Integer(), nullable=False),
        sa.Column("categoria_id", sa.Integer(), nullable=False),
        sa.Column("forma_pagamento_id", sa.Integer(), nullable=True),
        sa.Column("compra_parcelada_id", sa.Integer(), nullable=True),
        sa.Column("numero_parcela", sa.SmallInteger(), nullable=True),
        sa.Column("eh_adiantamento", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.CheckConstraint(
            "(tipo = 'despesa') = (forma_pagamento_id IS NOT NULL)",
            name=op.f("ck_lancamento_forma_so_na_despesa"),
        ),
        sa.CheckConstraint(
            "status = 'ativo' OR numero_parcela IS NOT NULL",
            name=op.f("ck_lancamento_so_parcela_antecipada"),
        ),
        sa.CheckConstraint(
            "EXTRACT(DAY FROM mes_competencia) = 1", name=op.f("ck_lancamento_competencia_no_dia_1")
        ),
        sa.CheckConstraint(
            "NOT eh_adiantamento OR compra_parcelada_id IS NOT NULL",
            name=op.f("ck_lancamento_adiantamento_tem_compra"),
        ),
        sa.CheckConstraint(
            "numero_parcela >= 1", name=op.f("ck_lancamento_numero_parcela_positivo")
        ),
        sa.CheckConstraint(
            "numero_parcela IS NULL OR (compra_parcelada_id IS NOT NULL AND NOT eh_adiantamento)",
            name=op.f("ck_lancamento_parcela_tem_compra"),
        ),
        sa.CheckConstraint("valor > 0", name=op.f("ck_lancamento_valor_positivo")),
        sa.ForeignKeyConstraint(
            ["autor_id"],
            ["pessoa.id"],
            name=op.f("fk_lancamento_autor_id_pessoa"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["categoria_id"],
            ["categoria.id"],
            name=op.f("fk_lancamento_categoria_id_categoria"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["compra_parcelada_id"],
            ["compra_parcelada.id"],
            name=op.f("fk_lancamento_compra_parcelada_id_compra_parcelada"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["forma_pagamento_id"],
            ["forma_pagamento.id"],
            name=op.f("fk_lancamento_forma_pagamento_id_forma_pagamento"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["pessoa_id"],
            ["pessoa.id"],
            name=op.f("fk_lancamento_pessoa_id_pessoa"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lancamento")),
        sa.UniqueConstraint(
            "compra_parcelada_id", "numero_parcela", name=op.f("uq_lancamento_compra_parcelada_id")
        ),
    )
    op.create_index(
        "ix_lancamento_competencia_status",
        "lancamento",
        ["mes_competencia", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_lancamento_compra_parcelada_id"),
        "lancamento",
        ["compra_parcelada_id"],
        unique=False,
    )
    op.create_table(
        "comprovante",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lancamento_id", sa.Integer(), nullable=False),
        sa.Column("imagem", sa.LargeBinary(), nullable=False),
        sa.Column("mime", sa.String(length=50), nullable=False),
        sa.Column("tamanho", sa.Integer(), nullable=False),
        sa.Column(
            "criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.CheckConstraint(
            "tamanho BETWEEN 1 AND 1048576", name=op.f("ck_comprovante_tamanho_maximo")
        ),
        sa.ForeignKeyConstraint(
            ["lancamento_id"],
            ["lancamento.id"],
            name=op.f("fk_comprovante_lancamento_id_lancamento"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_comprovante")),
        sa.UniqueConstraint("lancamento_id", name=op.f("uq_comprovante_lancamento_id")),
    )
    op.create_index(op.f("ix_comprovante_criado_em"), "comprovante", ["criado_em"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_comprovante_criado_em"), table_name="comprovante")
    op.drop_table("comprovante")
    op.drop_index(op.f("ix_lancamento_compra_parcelada_id"), table_name="lancamento")
    op.drop_index("ix_lancamento_competencia_status", table_name="lancamento")
    op.drop_table("lancamento")
    op.drop_table("forma_pagamento_usuario")
    op.drop_table("forma_pagamento")
    op.drop_table("pessoa")
    op.drop_table("compra_parcelada")
    op.drop_table("categoria")
