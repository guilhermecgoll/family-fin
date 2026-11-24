from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from financas.domain.erros import ErroDeDominio
from financas.domain.parcelamento import (
    antecipar,
    dividir_valor,
    economia,
    gerar_parcelas,
)
from financas.domain.tipos import (
    FormaPagamento,
    Lancamento,
    StatusLancamento,
    TipoForma,
    TipoLancamento,
)

CARTAO = FormaPagamento(
    "Cartão", TipoForma.CREDITO, dono_id=1, fecha_ultimo_dia=True, dia_vencimento=7
)
PIX = FormaPagamento("Pix", TipoForma.PIX, dono_id=1)


def _lancamentos(parcelas):
    return [
        Lancamento(
            tipo=TipoLancamento.DESPESA,
            valor=parcela.valor,
            descricao="Geladeira",
            data_real=date(2026, 9, 15),
            mes_competencia=parcela.mes_competencia,
            pessoa_id=1,
            autor_id=1,
            categoria_id=1,
            forma_pagamento_id=1,
            compra_parcelada_id=1,
            numero_parcela=parcela.numero,
        )
        for parcela in parcelas
    ]


@pytest.fixture
def compra_em_10x():
    """10 x R$ 30 com a parcela 1 em out/2026; a parcela 3 cai em dez/2026."""
    return _lancamentos(
        gerar_parcelas(date(2026, 9, 15), CARTAO, 10, valor_total=Decimal("300.00"))
    )


class TestDividirValor:
    @pytest.mark.parametrize(
        ("total", "parcelas", "esperado"),
        [
            (Decimal("3000"), 10, [Decimal("300.00")] * 10),
            (Decimal("100"), 3, [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")]),
            (Decimal("0.05"), 2, [Decimal("0.03"), Decimal("0.02")]),
        ],
    )
    def test_divide_com_resto_na_primeira(self, total, parcelas, esperado):
        valores = dividir_valor(total, parcelas)

        assert valores == esperado
        assert sum(valores) == total

    def test_recusa_parcela_zerada(self):
        with pytest.raises(ErroDeDominio, match="pequeno demais"):
            dividir_valor(Decimal("0.01"), 2)


class TestGerarParcelas:
    def test_parcelas_em_meses_seguidos_atravessando_o_ano(self):
        parcelas = gerar_parcelas(date(2026, 11, 20), CARTAO, 3, valor_total=Decimal("100"))

        assert [(p.numero, p.valor, p.mes_competencia) for p in parcelas] == [
            (1, Decimal("33.34"), date(2026, 12, 1)),
            (2, Decimal("33.33"), date(2027, 1, 1)),
            (3, Decimal("33.33"), date(2027, 2, 1)),
        ]

    def test_pelo_valor_da_parcela(self):
        parcelas = gerar_parcelas(date(2026, 11, 20), CARTAO, 10, valor_parcela=Decimal("299.90"))

        assert {p.valor for p in parcelas} == {Decimal("299.90")}
        assert sum(p.valor for p in parcelas) == Decimal("2999.00")

    @pytest.mark.parametrize(
        ("forma", "num_parcelas", "valores", "mensagem"),
        [
            (PIX, 3, {"valor_total": Decimal("100")}, "cartão de crédito"),
            (CARTAO, 1, {"valor_total": Decimal("100")}, "pelo menos 2"),
            (CARTAO, 3, {}, "valor total ou o valor da parcela"),
            (
                CARTAO,
                3,
                {"valor_total": Decimal("100"), "valor_parcela": Decimal("10")},
                "valor total ou o valor da parcela",
            ),
            (CARTAO, 3, {"valor_total": Decimal("-100")}, "positivo"),
            (CARTAO, 3, {"valor_parcela": Decimal("10.001")}, "duas casas"),
        ],
    )
    def test_recusa_entradas_invalidas(self, forma, num_parcelas, valores, mensagem):
        with pytest.raises(ErroDeDominio, match=mensagem):
            gerar_parcelas(date(2026, 11, 20), forma, num_parcelas, **valores)


class TestAntecipar:
    def test_exemplo_da_spec_abate_as_ultimas(self, compra_em_10x):
        # Na parcela 3 (fatura de dez/2026), adianta 5 parcelas de R$ 30 pagando R$ 147.
        antecipacao = antecipar(compra_em_10x, 5, Decimal("147.00"), date(2026, 11, 20), CARTAO)

        assert antecipacao.numeros_antecipados == (6, 7, 8, 9, 10)
        assert antecipacao.valor_abatido == Decimal("150.00")
        assert antecipacao.valor_pago == Decimal("147.00")
        assert antecipacao.economia == Decimal("3.00")
        assert antecipacao.mes_competencia == date(2026, 12, 1)

    def test_parcela_da_fatura_atual_nao_e_elegivel(self, compra_em_10x):
        # Fatura de dez/2026: parcelas 4 a 10 ainda estão por vir.
        with pytest.raises(ErroDeDominio, match="só há 7 parcela"):
            antecipar(compra_em_10x, 8, Decimal("200"), date(2026, 11, 20), CARTAO)

    def test_solicitacao_depois_do_fechamento_cai_na_fatura_seguinte(self, compra_em_10x):
        # Solicitado em 1º/12: entra na fatura de jan/2027 e a parcela 4 já não é elegível.
        antecipacao = antecipar(compra_em_10x, 6, Decimal("170"), date(2026, 12, 1), CARTAO)

        assert antecipacao.mes_competencia == date(2027, 1, 1)
        assert antecipacao.numeros_antecipados == (5, 6, 7, 8, 9, 10)

    def test_ignora_parcelas_ja_antecipadas_e_adiantamentos(self, compra_em_10x):
        lancamentos = [
            replace(lancamento, status=StatusLancamento.ANTECIPADA)
            if lancamento.numero_parcela in (9, 10)
            else lancamento
            for lancamento in compra_em_10x
        ]
        adiantamento = replace(
            compra_em_10x[0], valor=Decimal("59"), numero_parcela=None, eh_adiantamento=True
        )

        antecipacao = antecipar(
            [*lancamentos, adiantamento], 2, Decimal("59"), date(2026, 11, 20), CARTAO
        )

        assert antecipacao.numeros_antecipados == (7, 8)

    @pytest.mark.parametrize(
        ("quantidade", "valor_pago", "mensagem"),
        [
            (0, Decimal("10"), "pelo menos 1"),
            (2, Decimal("0"), "positivo"),
            (2, Decimal("60.01"), "não pode ser maior"),
        ],
    )
    def test_recusa_entradas_invalidas(self, compra_em_10x, quantidade, valor_pago, mensagem):
        with pytest.raises(ErroDeDominio, match=mensagem):
            antecipar(compra_em_10x, quantidade, valor_pago, date(2026, 11, 20), CARTAO)


def test_economia_soma_antecipadas_menos_pagamentos(compra_em_10x):
    lancamentos = [
        replace(lancamento, status=StatusLancamento.ANTECIPADA)
        if lancamento.numero_parcela >= 6
        else lancamento
        for lancamento in compra_em_10x
    ]
    adiantamento = replace(
        compra_em_10x[0], valor=Decimal("147"), numero_parcela=None, eh_adiantamento=True
    )

    assert economia([*lancamentos, adiantamento]) == Decimal("3.00")
    assert economia(compra_em_10x) == Decimal("0")
