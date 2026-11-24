from pathlib import Path

import pytest
from pydantic import ValidationError

from financas.domain.tipos import TipoForma
from financas.services.seed import ler_seed

EXEMPLO = Path(__file__).parents[2] / "config" / "seed.example.yaml"

PESSOAS = """
pessoas:
  - nome: Ana
    email: Ana@Example.com
    telegram_user_id: 100000001
  - nome: Bruno
    email: null
"""


def test_le_o_seed_de_exemplo():
    dados = ler_seed(EXEMPLO.read_text(encoding="utf-8"))

    assert [pessoa.nome for pessoa in dados.pessoas] == ["Ana", "Bruno"]
    formas = {forma.nome: forma for forma in dados.formas_pagamento}
    assert formas["Dinheiro"].dono_nome is None
    assert formas["Crédito Ana"].fecha_ultimo_dia
    assert formas["Crédito Ana"].dia_fechamento is None
    assert formas["Crédito Ana"].usuarios == ("Ana", "Bruno")
    assert formas["Crédito Bruno"].dia_fechamento == 3
    assert formas["Crédito Bruno"].vencimento == 12
    assert formas["VR Ana"].tipo is TipoForma.VALE_REFEICAO


def test_normaliza_email_e_aceita_campos_opcionais():
    dados = ler_seed(PESSOAS)

    assert dados.pessoas[0].email == "ana@example.com"
    assert dados.pessoas[1].email is None
    assert dados.formas_pagamento == ()


@pytest.mark.parametrize(
    ("formas", "mensagem"),
    [
        ("  - {nome: Pix, tipo: pix, dono: Carla}", "pessoa desconhecida: Carla"),
        (
            "  - {nome: Cartão, tipo: credito, dono: Ana, usuarios: [Carla], "
            "fechamento: 3, vencimento: 10}",
            "pessoa desconhecida: Carla",
        ),
        ("  - {nome: Dinheiro, tipo: dinheiro, dono: Ana}", "não tem dono"),
        ("  - {nome: Pix, tipo: pix, dono: Ana, usuarios: [Bruno]}", "usuários adicionais"),
        ("  - {nome: Cartão, tipo: credito, dono: Ana, vencimento: 10}", "e não dos dois"),
        (
            "  - {nome: Cartão, tipo: credito, dono: Ana, fechamento: penultimo, vencimento: 10}",
            "fechamento",
        ),
        ("  - {nome: Cheque, tipo: cheque, dono: Ana}", "tipo"),
        (
            "  - {nome: Pix, tipo: pix, dono: Ana}\n  - {nome: Pix, tipo: pix, dono: Bruno}",
            "nome de forma de pagamento repetido: Pix",
        ),
        ("  - {nome: Pix, tipo: pix, dono: Ana, apelido: x}", "apelido"),
    ],
)
def test_recusa_formas_invalidas(formas, mensagem):
    with pytest.raises(ValidationError, match=mensagem):
        ler_seed(PESSOAS + "formas_pagamento:\n" + formas)


@pytest.mark.parametrize(
    ("texto", "mensagem"),
    [
        ("", "valid dictionary"),
        ("pessoas: []", "at least 1"),
        ("pessoas:\n  - nome: Ana\n  - nome: Ana", "nome de pessoa repetido: Ana"),
        (
            "pessoas:\n  - {nome: Ana, email: a@x.com}\n  - {nome: Bia, email: A@x.com}",
            "e-mail repetido: a@x.com",
        ),
        (
            "pessoas:\n  - {nome: Ana, telegram_user_id: 1}\n  - {nome: Bia, telegram_user_id: 1}",
            "telegram_user_id repetido: 1",
        ),
        ("pessoas:\n  - {nome: Ana, email: sem-arroba}", "e-mail inválido"),
    ],
)
def test_recusa_pessoas_invalidas(texto, mensagem):
    with pytest.raises(ValidationError, match=mensagem):
        ler_seed(texto)
