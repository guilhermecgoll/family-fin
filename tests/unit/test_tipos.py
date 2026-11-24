from decimal import Decimal

import pytest

from financas.domain.erros import ErroDeDominio
from financas.domain.tipos import FormaPagamento, TipoForma, validar_valor


class TestValidarValor:
    @pytest.mark.parametrize("valor", [Decimal("0.01"), Decimal("230.5"), Decimal("1000")])
    def test_aceita_valores_validos(self, valor):
        validar_valor(valor)

    @pytest.mark.parametrize(
        ("valor", "mensagem"),
        [
            (Decimal("0"), "positivo"),
            (Decimal("-1"), "positivo"),
            (Decimal("10.005"), "duas casas"),
            (10.5, "Decimal"),
        ],
    )
    def test_recusa_valores_invalidos(self, valor, mensagem):
        with pytest.raises(ErroDeDominio, match=mensagem):
            validar_valor(valor)


class TestFormaPagamento:
    def test_dinheiro_e_da_familia_e_qualquer_um_usa(self):
        dinheiro = FormaPagamento("Dinheiro", TipoForma.DINHEIRO)

        assert dinheiro.pode_usar(1)
        assert dinheiro.pode_usar(2)

    def test_pix_so_o_dono_usa(self):
        pix = FormaPagamento("Pix", TipoForma.PIX, dono_id=1)

        assert pix.pode_usar(1)
        assert not pix.pode_usar(2)

    def test_credito_titular_e_adicionais_usam(self):
        cartao = FormaPagamento(
            "Cartão",
            TipoForma.CREDITO,
            dono_id=1,
            usuarios_ids=frozenset({2}),
            fecha_ultimo_dia=True,
            dia_vencimento=7,
        )

        assert cartao.pode_usar(1)
        assert cartao.pode_usar(2)
        assert not cartao.pode_usar(3)

    @pytest.mark.parametrize(
        ("argumentos", "mensagem"),
        [
            ({"tipo": TipoForma.DINHEIRO, "dono_id": 1}, "não tem dono"),
            ({"tipo": TipoForma.PIX}, "precisa de um dono"),
            (
                {"tipo": TipoForma.DEBITO, "dono_id": 1, "usuarios_ids": frozenset({2})},
                "usuários adicionais",
            ),
            ({"tipo": TipoForma.PIX, "dono_id": 1, "dia_vencimento": 7}, "só existem no cartão"),
            ({"tipo": TipoForma.PIX, "dono_id": 1, "fecha_ultimo_dia": True}, "só existem"),
            ({"tipo": TipoForma.CREDITO, "dono_id": 1, "dia_fechamento": 3}, "vencimento"),
            ({"tipo": TipoForma.CREDITO, "dono_id": 1, "dia_vencimento": 7}, "e não dos dois"),
            (
                {
                    "tipo": TipoForma.CREDITO,
                    "dono_id": 1,
                    "dia_fechamento": 3,
                    "fecha_ultimo_dia": True,
                    "dia_vencimento": 7,
                },
                "e não dos dois",
            ),
            (
                {"tipo": TipoForma.CREDITO, "dono_id": 1, "dia_fechamento": 0, "dia_vencimento": 7},
                "dia de fechamento deve estar entre 1 e 31",
            ),
            (
                {
                    "tipo": TipoForma.CREDITO,
                    "dono_id": 1,
                    "fecha_ultimo_dia": True,
                    "dia_vencimento": 32,
                },
                "dia de vencimento deve estar entre 1 e 31",
            ),
        ],
    )
    def test_recusa_combinacoes_invalidas(self, argumentos, mensagem):
        with pytest.raises(ErroDeDominio, match=mensagem):
            FormaPagamento("Forma", **argumentos)
