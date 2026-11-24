"""Tabelas do banco. As regras ficam no domínio; aqui, só as restrições que o banco garante."""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    SmallInteger,
    String,
    Table,
    UniqueConstraint,
    false,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from financas.adapters.db.base import Base
from financas.domain.tipos import StatusLancamento, TipoForma, TipoLancamento

TAMANHO_MAXIMO_COMPROVANTE = 1024 * 1024


def _enum(tipo: type[StrEnum], nome: str) -> Enum:
    """Enum guardado como texto com CHECK, para evitar tipos nativos difíceis de migrar."""
    return Enum(
        tipo,
        name=nome,
        native_enum=False,
        create_constraint=True,
        length=20,
        values_callable=lambda membros: [membro.value for membro in membros],
    )


def _dinheiro() -> Numeric[Decimal]:
    return Numeric(12, 2)


forma_pagamento_usuario = Table(
    "forma_pagamento_usuario",
    Base.metadata,
    Column(
        "forma_pagamento_id",
        ForeignKey("forma_pagamento.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("pessoa_id", ForeignKey("pessoa.id", ondelete="CASCADE"), primary_key=True),
)


class PessoaModelo(Base):
    __tablename__ = "pessoa"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True)
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    email: Mapped[str | None] = mapped_column(String(254), unique=True)


class CategoriaModelo(Base):
    __tablename__ = "categoria"
    __table_args__ = (UniqueConstraint("nome", "tipo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    tipo: Mapped[TipoLancamento] = mapped_column(_enum(TipoLancamento, "tipo_lancamento"))
    arquivada: Mapped[bool] = mapped_column(default=False, server_default=false())


class FormaPagamentoModelo(Base):
    __tablename__ = "forma_pagamento"
    __table_args__ = (
        CheckConstraint("dia_fechamento BETWEEN 1 AND 31", name="dia_fechamento_valido"),
        CheckConstraint("dia_vencimento BETWEEN 1 AND 31", name="dia_vencimento_valido"),
        CheckConstraint(
            "(tipo = 'credito') = (dia_vencimento IS NOT NULL)", name="vencimento_so_no_credito"
        ),
        CheckConstraint(
            "(tipo = 'credito') = ((dia_fechamento IS NOT NULL) <> fecha_ultimo_dia)",
            name="fechamento_so_no_credito",
        ),
        CheckConstraint(
            "NOT (dia_fechamento IS NOT NULL AND fecha_ultimo_dia)", name="fechamento_exclusivo"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True)
    tipo: Mapped[TipoForma] = mapped_column(_enum(TipoForma, "tipo_forma"))
    dono_id: Mapped[int | None] = mapped_column(ForeignKey("pessoa.id", ondelete="RESTRICT"))
    dia_fechamento: Mapped[int | None] = mapped_column(SmallInteger)
    fecha_ultimo_dia: Mapped[bool] = mapped_column(default=False, server_default=false())
    dia_vencimento: Mapped[int | None] = mapped_column(SmallInteger)

    usuarios: Mapped[list[PessoaModelo]] = relationship(
        secondary=forma_pagamento_usuario, lazy="selectin"
    )


class CompraParceladaModelo(Base):
    __tablename__ = "compra_parcelada"
    __table_args__ = (
        CheckConstraint("valor_total > 0", name="valor_total_positivo"),
        CheckConstraint("num_parcelas >= 2", name="ao_menos_duas_parcelas"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    descricao: Mapped[str] = mapped_column(String(200))
    valor_total: Mapped[Decimal] = mapped_column(_dinheiro())
    num_parcelas: Mapped[int] = mapped_column(SmallInteger)
    data_real: Mapped[date] = mapped_column(Date)


class LancamentoModelo(Base):
    __tablename__ = "lancamento"
    __table_args__ = (
        CheckConstraint("valor > 0", name="valor_positivo"),
        CheckConstraint(
            "(tipo = 'despesa') = (forma_pagamento_id IS NOT NULL)", name="forma_so_na_despesa"
        ),
        CheckConstraint("EXTRACT(DAY FROM mes_competencia) = 1", name="competencia_no_dia_1"),
        CheckConstraint("numero_parcela >= 1", name="numero_parcela_positivo"),
        CheckConstraint(
            "numero_parcela IS NULL OR (compra_parcelada_id IS NOT NULL AND NOT eh_adiantamento)",
            name="parcela_tem_compra",
        ),
        CheckConstraint(
            "NOT eh_adiantamento OR compra_parcelada_id IS NOT NULL",
            name="adiantamento_tem_compra",
        ),
        CheckConstraint(
            "status = 'ativo' OR numero_parcela IS NOT NULL", name="so_parcela_antecipada"
        ),
        UniqueConstraint("compra_parcelada_id", "numero_parcela"),
        Index("ix_lancamento_competencia_status", "mes_competencia", "status"),
    )
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[TipoLancamento] = mapped_column(_enum(TipoLancamento, "tipo_lancamento"))
    valor: Mapped[Decimal] = mapped_column(_dinheiro())
    descricao: Mapped[str] = mapped_column(String(200))
    data_real: Mapped[date] = mapped_column(Date)
    mes_competencia: Mapped[date] = mapped_column(Date)
    registrado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    status: Mapped[StatusLancamento] = mapped_column(
        _enum(StatusLancamento, "status_lancamento"), default=StatusLancamento.ATIVO
    )
    pessoa_id: Mapped[int] = mapped_column(ForeignKey("pessoa.id", ondelete="RESTRICT"))
    autor_id: Mapped[int] = mapped_column(ForeignKey("pessoa.id", ondelete="RESTRICT"))
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categoria.id", ondelete="RESTRICT"))
    forma_pagamento_id: Mapped[int | None] = mapped_column(
        ForeignKey("forma_pagamento.id", ondelete="RESTRICT")
    )
    compra_parcelada_id: Mapped[int | None] = mapped_column(
        ForeignKey("compra_parcelada.id", ondelete="CASCADE"), index=True
    )
    numero_parcela: Mapped[int | None] = mapped_column(SmallInteger)
    eh_adiantamento: Mapped[bool] = mapped_column(default=False, server_default=false())


class ComprovanteModelo(Base):
    __tablename__ = "comprovante"
    __table_args__ = (
        CheckConstraint(
            f"tamanho BETWEEN 1 AND {TAMANHO_MAXIMO_COMPROVANTE}", name="tamanho_maximo"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    lancamento_id: Mapped[int] = mapped_column(
        ForeignKey("lancamento.id", ondelete="CASCADE"), unique=True
    )
    imagem: Mapped[bytes] = mapped_column(LargeBinary)
    mime: Mapped[str] = mapped_column(String(50))
    tamanho: Mapped[int] = mapped_column(Integer)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
