import pytest

from financas.domain.texto import chave_alfabetica


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Água", "agua"),
        ("  Pão   de Queijo ", "pao de queijo"),
        ("AÇÚCAR", "acucar"),
        ("Crédito Ana", "credito ana"),
    ],
)
def test_chave_alfabetica(texto, esperado):
    assert chave_alfabetica(texto) == esperado


def test_ordena_ignorando_acentos():
    nomes = ["Dinheiro", "Débito Bruno", "Crédito Ana", "água", "Alimentação"]

    assert sorted(nomes, key=chave_alfabetica) == [
        "água",
        "Alimentação",
        "Crédito Ana",
        "Débito Bruno",
        "Dinheiro",
    ]
