"""Mês de competência: em que mês um lançamento pesa no fluxo de caixa.

Fora do cartão de crédito, é o mês da data real. No crédito, é o mês de vencimento da
fatura em que a compra entra:

- compra até o dia de fechamento (inclusive) entra na fatura que fecha naquele mês;
  depois dele, na do mês seguinte;
- a fatura vence no mesmo mês do fechamento se o dia de vencimento for maior que o de
  fechamento; senão, no mês seguinte. Com fechamento no último dia, sempre no seguinte;
- dia de fechamento que não existe no mês (31 em abril) vira o último dia do mês.
"""

import calendar
from datetime import date

from financas.domain.tipos import FormaPagamento, TipoForma


def primeiro_dia(data: date) -> date:
    return data.replace(day=1)


def somar_meses(mes: date, quantidade: int) -> date:
    """Dia 1 do mês `quantidade` meses depois (ou antes, se negativo) do mês de `mes`."""
    indice = mes.year * 12 + (mes.month - 1) + quantidade
    return date(indice // 12, indice % 12 + 1, 1)


def ultimo_dia_do_mes(ano: int, mes: int) -> int:
    return calendar.monthrange(ano, mes)[1]


def data_fechamento(ano: int, mes: int, forma: FormaPagamento) -> date:
    # Na forma de crédito validada, sem dia fixo significa "fecha no último dia".
    ultimo = ultimo_dia_do_mes(ano, mes)
    dia = forma.dia_fechamento
    return date(ano, mes, ultimo if dia is None else min(dia, ultimo))


def _vence_no_mes_seguinte_ao_fechamento(forma: FormaPagamento) -> bool:
    if forma.dia_fechamento is None or forma.dia_vencimento is None:
        return True  # fecha no último dia: o vencimento é sempre no mês seguinte
    return forma.dia_vencimento <= forma.dia_fechamento


def mes_competencia(data_real: date, forma: FormaPagamento | None) -> date:
    """Dia 1 do mês em que um lançamento com essa data e forma pesa no fluxo de caixa.

    `forma` é `None` nas receitas.
    """
    mes = primeiro_dia(data_real)
    if forma is None or forma.tipo is not TipoForma.CREDITO:
        return mes

    if data_real > data_fechamento(mes.year, mes.month, forma):
        mes = somar_meses(mes, 1)
    if _vence_no_mes_seguinte_ao_fechamento(forma):
        mes = somar_meses(mes, 1)
    return mes
