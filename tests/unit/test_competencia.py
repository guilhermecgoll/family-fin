from datetime import date

import pytest

from financas.domain.competencia import data_fechamento, mes_competencia, somar_meses
from financas.domain.tipos import FormaPagamento, TipoForma

PIX = FormaPagamento("Pix", TipoForma.PIX, dono_id=1)
# Exemplos da spec.
FECHA_ULTIMO_VENCE_7 = FormaPagamento(
    "Cartão A", TipoForma.CREDITO, dono_id=1, fecha_ultimo_dia=True, dia_vencimento=7
)
FECHA_3_VENCE_12 = FormaPagamento(
    "Cartão B", TipoForma.CREDITO, dono_id=1, dia_fechamento=3, dia_vencimento=12
)
# Dia fixo que não existe em todos os meses.
FECHA_31_VENCE_10 = FormaPagamento(
    "Cartão C", TipoForma.CREDITO, dono_id=1, dia_fechamento=31, dia_vencimento=10
)
FECHA_30_VENCE_10 = FormaPagamento(
    "Cartão D", TipoForma.CREDITO, dono_id=1, dia_fechamento=30, dia_vencimento=10
)
# Vencimento antes e no mesmo dia do fechamento.
FECHA_25_VENCE_5 = FormaPagamento(
    "Cartão E", TipoForma.CREDITO, dono_id=1, dia_fechamento=25, dia_vencimento=5
)
FECHA_10_VENCE_10 = FormaPagamento(
    "Cartão F", TipoForma.CREDITO, dono_id=1, dia_fechamento=10, dia_vencimento=10
)


@pytest.mark.parametrize(
    ("data_real", "forma", "esperado"),
    [
        # Fora do crédito e receitas: mês da data real.
        (date(2026, 11, 20), PIX, date(2026, 11, 1)),
        (date(2026, 11, 30), None, date(2026, 11, 1)),
        # Spec: fechamento no último dia, vencimento no dia 7.
        (date(2026, 11, 1), FECHA_ULTIMO_VENCE_7, date(2026, 12, 1)),
        (date(2026, 11, 30), FECHA_ULTIMO_VENCE_7, date(2026, 12, 1)),
        (date(2026, 12, 1), FECHA_ULTIMO_VENCE_7, date(2027, 1, 1)),
        (date(2026, 12, 31), FECHA_ULTIMO_VENCE_7, date(2027, 1, 1)),
        (date(2028, 2, 29), FECHA_ULTIMO_VENCE_7, date(2028, 3, 1)),
        # Spec: fechamento no dia 3, vencimento no dia 12.
        (date(2026, 11, 2), FECHA_3_VENCE_12, date(2026, 11, 1)),
        (date(2026, 11, 3), FECHA_3_VENCE_12, date(2026, 11, 1)),
        (date(2026, 11, 4), FECHA_3_VENCE_12, date(2026, 12, 1)),
        (date(2026, 11, 20), FECHA_3_VENCE_12, date(2026, 12, 1)),
        (date(2026, 12, 20), FECHA_3_VENCE_12, date(2027, 1, 1)),
        # Fechamento no dia 31 vira o último dia em meses curtos.
        (date(2027, 1, 31), FECHA_31_VENCE_10, date(2027, 2, 1)),
        (date(2027, 2, 28), FECHA_31_VENCE_10, date(2027, 3, 1)),
        (date(2027, 3, 1), FECHA_31_VENCE_10, date(2027, 4, 1)),
        (date(2027, 4, 30), FECHA_31_VENCE_10, date(2027, 5, 1)),
        (date(2027, 2, 28), FECHA_30_VENCE_10, date(2027, 3, 1)),
        (date(2028, 2, 29), FECHA_30_VENCE_10, date(2028, 3, 1)),
        # Vencimento antes do fechamento: mês seguinte ao fechamento.
        (date(2026, 11, 25), FECHA_25_VENCE_5, date(2026, 12, 1)),
        (date(2026, 11, 26), FECHA_25_VENCE_5, date(2027, 1, 1)),
        # Vencimento no mesmo dia do fechamento: também mês seguinte.
        (date(2026, 11, 10), FECHA_10_VENCE_10, date(2026, 12, 1)),
    ],
)
def test_mes_competencia(data_real, forma, esperado):
    assert mes_competencia(data_real, forma) == esperado


@pytest.mark.parametrize(
    ("ano", "mes", "forma", "esperado"),
    [
        (2027, 4, FECHA_31_VENCE_10, date(2027, 4, 30)),
        (2027, 5, FECHA_31_VENCE_10, date(2027, 5, 31)),
        (2027, 2, FECHA_30_VENCE_10, date(2027, 2, 28)),
        (2028, 2, FECHA_ULTIMO_VENCE_7, date(2028, 2, 29)),
        (2026, 11, FECHA_3_VENCE_12, date(2026, 11, 3)),
    ],
)
def test_data_fechamento(ano, mes, forma, esperado):
    assert data_fechamento(ano, mes, forma) == esperado


@pytest.mark.parametrize(
    ("mes", "quantidade", "esperado"),
    [
        (date(2026, 11, 15), 0, date(2026, 11, 1)),
        (date(2026, 11, 1), 1, date(2026, 12, 1)),
        (date(2026, 12, 1), 1, date(2027, 1, 1)),
        (date(2026, 11, 1), 14, date(2028, 1, 1)),
        (date(2026, 1, 1), -1, date(2025, 12, 1)),
    ],
)
def test_somar_meses(mes, quantidade, esperado):
    assert somar_meses(mes, quantidade) == esperado
