"""Compras parceladas no cartão de crédito e adiantamento de parcelas."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_DOWN, Decimal

from financas.domain.competencia import mes_competencia, somar_meses
from financas.domain.erros import ErroDeDominio
from financas.domain.tipos import (
    CENTAVO,
    FormaPagamento,
    Lancamento,
    StatusLancamento,
    TipoForma,
    validar_valor,
)


@dataclass(frozen=True)
class Parcela:
    numero: int
    valor: Decimal
    mes_competencia: date


@dataclass(frozen=True)
class Antecipacao:
    """Resultado de um adiantamento: parcelas abatidas e o lançamento do valor pago."""

    numeros_antecipados: tuple[int, ...]
    valor_abatido: Decimal
    valor_pago: Decimal
    mes_competencia: date

    @property
    def economia(self) -> Decimal:
        return self.valor_abatido - self.valor_pago


def dividir_valor(total: Decimal, num_parcelas: int) -> list[Decimal]:
    """Divide em parcelas iguais; os centavos que sobram ficam na primeira."""
    base = (total / num_parcelas).quantize(CENTAVO, rounding=ROUND_DOWN)
    if base <= 0:
        raise ErroDeDominio("o valor é pequeno demais para tantas parcelas")
    resto = total - base * num_parcelas
    return [base + resto] + [base] * (num_parcelas - 1)


def gerar_parcelas(
    data_real: date,
    forma: FormaPagamento,
    num_parcelas: int,
    *,
    valor_total: Decimal | None = None,
    valor_parcela: Decimal | None = None,
) -> list[Parcela]:
    """Parcelas de uma compra no crédito, informada pelo total ou pelo valor da parcela.

    A parcela 1 segue a regra da fatura pela data real; cada seguinte cai um mês depois.
    """
    if forma.tipo is not TipoForma.CREDITO:
        raise ErroDeDominio("só compras no cartão de crédito podem ser parceladas")
    if num_parcelas < 2:
        raise ErroDeDominio("uma compra parcelada tem pelo menos 2 parcelas")

    if valor_total is not None and valor_parcela is None:
        validar_valor(valor_total)
        valores = dividir_valor(valor_total, num_parcelas)
    elif valor_parcela is not None and valor_total is None:
        validar_valor(valor_parcela)
        valores = [valor_parcela] * num_parcelas
    else:
        raise ErroDeDominio("informe o valor total ou o valor da parcela, e não os dois")

    primeira = mes_competencia(data_real, forma)
    return [
        Parcela(numero=numero, valor=valor, mes_competencia=somar_meses(primeira, numero - 1))
        for numero, valor in enumerate(valores, start=1)
    ]


def antecipar(
    lancamentos_da_compra: Sequence[Lancamento],
    quantidade: int,
    valor_pago: Decimal,
    data_solicitacao: date,
    forma: FormaPagamento,
) -> Antecipacao:
    """Abate as últimas parcelas ainda não cobradas e calcula o lançamento do valor pago.

    São elegíveis as parcelas ativas que caem depois da fatura em que o adiantamento
    entra (a da data da solicitação); a parcela dessa fatura já foi cobrada.
    """
    if quantidade < 1:
        raise ErroDeDominio("adiante pelo menos 1 parcela")
    validar_valor(valor_pago)

    competencia_pagamento = mes_competencia(data_solicitacao, forma)
    elegiveis = sorted(
        (
            lancamento
            for lancamento in lancamentos_da_compra
            if lancamento.numero_parcela is not None
            and lancamento.status is StatusLancamento.ATIVO
            and lancamento.mes_competencia > competencia_pagamento
        ),
        key=lambda lancamento: lancamento.numero_parcela or 0,
    )
    if quantidade > len(elegiveis):
        raise ErroDeDominio(f"só há {len(elegiveis)} parcela(s) a vencer que podem ser adiantadas")

    abatidas = elegiveis[-quantidade:]
    valor_abatido = sum((parcela.valor for parcela in abatidas), Decimal(0))
    if valor_pago > valor_abatido:
        raise ErroDeDominio("o valor pago não pode ser maior que o das parcelas adiantadas")

    return Antecipacao(
        numeros_antecipados=tuple(parcela.numero_parcela or 0 for parcela in abatidas),
        valor_abatido=valor_abatido,
        valor_pago=valor_pago,
        mes_competencia=competencia_pagamento,
    )


def economia(lancamentos_da_compra: Sequence[Lancamento]) -> Decimal:
    """Desconto obtido nos adiantamentos: parcelas antecipadas menos o que foi pago."""
    antecipadas = sum(
        (
            lancamento.valor
            for lancamento in lancamentos_da_compra
            if lancamento.status is StatusLancamento.ANTECIPADA
        ),
        Decimal(0),
    )
    pagos = sum(
        (lancamento.valor for lancamento in lancamentos_da_compra if lancamento.eh_adiantamento),
        Decimal(0),
    )
    return antecipadas - pagos
