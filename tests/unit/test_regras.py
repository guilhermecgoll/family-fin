from decimal import Decimal

import pytest

from financas.domain.erros import ErroDeDominio
from financas.domain.regras import validar_lancamento
from financas.domain.tipos import Categoria, FormaPagamento, TipoForma, TipoLancamento

ALIMENTACAO = Categoria("Alimentação", TipoLancamento.DESPESA, id=1)
PROVENTOS = Categoria("Proventos", TipoLancamento.RECEITA, id=2)
ANTIGA = Categoria("Antiga", TipoLancamento.DESPESA, arquivada=True, id=3)
VR_DA_PESSOA_1 = FormaPagamento("VR", TipoForma.VALE_REFEICAO, dono_id=1, id=1)

DESPESA = TipoLancamento.DESPESA
RECEITA = TipoLancamento.RECEITA


def test_aceita_despesa_valida():
    validar_lancamento(DESPESA, Decimal("230.50"), ALIMENTACAO, VR_DA_PESSOA_1, pessoa_id=1)


def test_aceita_receita_valida():
    validar_lancamento(RECEITA, Decimal("5000"), PROVENTOS, None, pessoa_id=2)


@pytest.mark.parametrize(
    ("tipo", "valor", "categoria", "forma", "pessoa_id", "mensagem"),
    [
        (DESPESA, Decimal("0"), ALIMENTACAO, VR_DA_PESSOA_1, 1, "positivo"),
        (DESPESA, Decimal("10"), PROVENTOS, VR_DA_PESSOA_1, 1, "não é de despesa"),
        (RECEITA, Decimal("10"), ALIMENTACAO, None, 1, "não é de receita"),
        (DESPESA, Decimal("10"), ANTIGA, VR_DA_PESSOA_1, 1, "arquivada"),
        (RECEITA, Decimal("10"), PROVENTOS, VR_DA_PESSOA_1, 1, "receita não tem forma"),
        (DESPESA, Decimal("10"), ALIMENTACAO, None, 1, "precisa de forma"),
        (DESPESA, Decimal("10"), ALIMENTACAO, VR_DA_PESSOA_1, 2, "não pode ser usada"),
    ],
)
def test_recusa_lancamento_invalido(tipo, valor, categoria, forma, pessoa_id, mensagem):
    with pytest.raises(ErroDeDominio, match=mensagem):
        validar_lancamento(tipo, valor, categoria, forma, pessoa_id)
