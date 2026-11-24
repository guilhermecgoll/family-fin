"""Entidades e enums do domínio, sem dependência de banco."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from financas.domain.erros import ErroDeDominio

CENTAVO = Decimal("0.01")


class TipoLancamento(StrEnum):
    DESPESA = "despesa"
    RECEITA = "receita"


class TipoForma(StrEnum):
    DINHEIRO = "dinheiro"
    PIX = "pix"
    DEBITO = "debito"
    VALE_REFEICAO = "vale_refeicao"
    CREDITO = "credito"


class StatusLancamento(StrEnum):
    ATIVO = "ativo"
    ANTECIPADA = "antecipada"


def validar_valor(valor: Decimal) -> None:
    """Valor monetário: `Decimal` positivo com no máximo duas casas."""
    if not isinstance(valor, Decimal):
        raise ErroDeDominio("valores monetários devem ser Decimal")
    if valor <= 0:
        raise ErroDeDominio("o valor deve ser positivo")
    if valor != valor.quantize(CENTAVO):
        raise ErroDeDominio("o valor deve ter no máximo duas casas decimais")


def _validar_dia(dia: int, campo: str) -> None:
    if not 1 <= dia <= 31:
        raise ErroDeDominio(f"{campo} deve estar entre 1 e 31")


def validar_forma(
    tipo: TipoForma,
    *,
    tem_dono: bool,
    tem_usuarios: bool,
    dia_fechamento: int | None,
    fecha_ultimo_dia: bool,
    dia_vencimento: int | None,
) -> None:
    """Regras de uma forma de pagamento, usadas pela entidade e pelo seed."""
    if tipo is TipoForma.DINHEIRO and tem_dono:
        raise ErroDeDominio("dinheiro é da família e não tem dono")
    if tipo is not TipoForma.DINHEIRO and not tem_dono:
        raise ErroDeDominio(f"{tipo} precisa de um dono")

    if tipo is not TipoForma.CREDITO:
        if tem_usuarios:
            raise ErroDeDominio("só o cartão de crédito tem usuários adicionais")
        if dia_fechamento is not None or fecha_ultimo_dia or dia_vencimento is not None:
            raise ErroDeDominio("fechamento e vencimento só existem no cartão de crédito")
        return

    if dia_vencimento is None:
        raise ErroDeDominio("o cartão de crédito precisa do dia de vencimento")
    _validar_dia(dia_vencimento, "o dia de vencimento")
    if (dia_fechamento is None) == (not fecha_ultimo_dia):
        raise ErroDeDominio(
            "o cartão de crédito precisa de um dia de fechamento ou de fechar no último dia, "
            "e não dos dois"
        )
    if dia_fechamento is not None:
        _validar_dia(dia_fechamento, "o dia de fechamento")


@dataclass(frozen=True)
class Pessoa:
    nome: str
    telegram_user_id: int | None = None
    email: str | None = None
    id: int | None = None


@dataclass(frozen=True)
class Categoria:
    nome: str
    tipo: TipoLancamento
    arquivada: bool = False
    id: int | None = None


@dataclass(frozen=True)
class FormaPagamento:
    nome: str
    tipo: TipoForma
    dono_id: int | None = None
    usuarios_ids: frozenset[int] = frozenset()
    dia_fechamento: int | None = None
    fecha_ultimo_dia: bool = False
    dia_vencimento: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        validar_forma(
            self.tipo,
            tem_dono=self.dono_id is not None,
            tem_usuarios=bool(self.usuarios_ids),
            dia_fechamento=self.dia_fechamento,
            fecha_ultimo_dia=self.fecha_ultimo_dia,
            dia_vencimento=self.dia_vencimento,
        )

    def pode_usar(self, pessoa_id: int) -> bool:
        if self.tipo is TipoForma.DINHEIRO:
            return True
        return pessoa_id == self.dono_id or pessoa_id in self.usuarios_ids


@dataclass(frozen=True)
class CompraParcelada:
    descricao: str
    valor_total: Decimal
    num_parcelas: int
    data_real: date
    id: int | None = None


@dataclass(frozen=True)
class Lancamento:
    """Unidade do fluxo de caixa: uma despesa, uma receita, uma parcela ou um adiantamento.

    `pessoa_id` é a quem o lançamento pertence; `autor_id`, quem o registrou.
    `mes_competencia` é sempre o dia 1 do mês em que o valor pesa no fluxo de caixa.
    """

    tipo: TipoLancamento
    valor: Decimal
    descricao: str
    data_real: date
    mes_competencia: date
    pessoa_id: int
    autor_id: int
    categoria_id: int
    forma_pagamento_id: int | None = None
    status: StatusLancamento = StatusLancamento.ATIVO
    compra_parcelada_id: int | None = None
    numero_parcela: int | None = None
    eh_adiantamento: bool = False
    registrado_em: datetime | None = None
    id: int | None = None
