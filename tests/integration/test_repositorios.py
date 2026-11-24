from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from financas.adapters.db.repositorios import RepositorioCadastrosSql, RepositorioLancamentosSql
from financas.adapters.db.seed import aplicar_seed
from financas.domain.erros import ErroDeDominio
from financas.domain.parcelamento import gerar_parcelas
from financas.domain.tipos import (
    CompraParcelada,
    Lancamento,
    StatusLancamento,
    TipoForma,
    TipoLancamento,
)
from financas.services.repositorios import RepositorioCadastros, RepositorioLancamentos
from financas.services.seed import ler_seed

EXEMPLO = Path(__file__).parents[2] / "config" / "seed.example.yaml"


@pytest.fixture
def cadastros(sessao):
    aplicar_seed(sessao, ler_seed(EXEMPLO.read_text(encoding="utf-8")))
    return RepositorioCadastrosSql(sessao)


@pytest.fixture
def lancamentos(sessao):
    return RepositorioLancamentosSql(sessao)


@pytest.fixture
def ana(cadastros):
    return cadastros.pessoa_por_email("ana@example.com")


@pytest.fixture
def bruno(cadastros):
    return cadastros.pessoa_por_email("bruno@example.com")


def _forma(cadastros, pessoa, nome):
    return next(forma for forma in cadastros.formas_da_pessoa(pessoa.id) if forma.nome == nome)


def _categoria(cadastros, tipo, nome):
    return next(categoria for categoria in cadastros.categorias(tipo) if categoria.nome == nome)


def test_implementacoes_seguem_as_interfaces(cadastros, lancamentos):
    assert isinstance(cadastros, RepositorioCadastros)
    assert isinstance(lancamentos, RepositorioLancamentos)


class TestCadastros:
    def test_busca_pessoas(self, cadastros, ana):
        assert [pessoa.nome for pessoa in cadastros.pessoas()] == ["Ana", "Bruno"]
        assert cadastros.pessoa_por_telegram(100000001) == ana
        assert cadastros.pessoa_por_email(" ANA@example.com ") == ana
        assert cadastros.pessoa_por_telegram(999) is None
        assert cadastros.pessoa_por_email("outra@example.com") is None

    def test_categorias_por_tipo(self, cadastros):
        receitas = [categoria.nome for categoria in cadastros.categorias(TipoLancamento.RECEITA)]

        assert receitas == ["Proventos", "Remuneração financeira", "Vale-refeição"]
        assert len(cadastros.categorias(TipoLancamento.DESPESA)) == 13

    def test_formas_que_cada_pessoa_pode_usar(self, cadastros, ana, bruno):
        assert [forma.nome for forma in cadastros.formas_da_pessoa(ana.id)] == [
            "Crédito Ana",
            "Dinheiro",
            "Pix Ana",
            "VR Ana",
        ]
        # Bruno é adicional no cartão da Ana.
        assert [forma.nome for forma in cadastros.formas_da_pessoa(bruno.id)] == [
            "Crédito Ana",
            "Crédito Bruno",
            "Débito Bruno",
            "Dinheiro",
        ]
        assert [c.nome for c in cadastros.categorias(TipoLancamento.DESPESA)][:3] == [
            "Alimentação",
            "Assinaturas",
            "Automóvel",
        ]

    def test_forma_por_id_com_dados_do_cartao(self, cadastros, ana, bruno):
        cartao = cadastros.forma(_forma(cadastros, ana, "Crédito Ana").id)

        assert cartao.tipo is TipoForma.CREDITO
        assert cartao.dono_id == ana.id
        assert cartao.usuarios_ids == {ana.id, bruno.id}
        assert cartao.fecha_ultimo_dia
        assert cartao.dia_vencimento == 7
        assert cadastros.forma(99999) is None


class TestLancamentos:
    def test_grava_despesa_simples(self, cadastros, lancamentos, ana):
        vr = _forma(cadastros, ana, "VR Ana")
        alimentacao = _categoria(cadastros, TipoLancamento.DESPESA, "Alimentação")

        [gravado] = lancamentos.adicionar(
            [
                Lancamento(
                    tipo=TipoLancamento.DESPESA,
                    valor=Decimal("230.50"),
                    descricao="Mercado",
                    data_real=date(2026, 11, 20),
                    mes_competencia=date(2026, 11, 1),
                    pessoa_id=ana.id,
                    autor_id=ana.id,
                    categoria_id=alimentacao.id,
                    forma_pagamento_id=vr.id,
                )
            ]
        )

        assert gravado.id is not None
        assert gravado.valor == Decimal("230.50")
        assert gravado.registrado_em is not None
        assert gravado.status is StatusLancamento.ATIVO

    def test_compra_parcelada_e_antecipacao(self, cadastros, lancamentos, ana):
        cartao = _forma(cadastros, ana, "Crédito Ana")
        categoria = _categoria(cadastros, TipoLancamento.DESPESA, "Residência")
        parcelas = gerar_parcelas(date(2026, 9, 15), cartao, 3, valor_total=Decimal("100"))
        compra = CompraParcelada("Geladeira", Decimal("100"), 3, date(2026, 9, 15))

        gravados = lancamentos.adicionar(
            [
                Lancamento(
                    tipo=TipoLancamento.DESPESA,
                    valor=parcela.valor,
                    descricao="Geladeira",
                    data_real=date(2026, 9, 15),
                    mes_competencia=parcela.mes_competencia,
                    pessoa_id=ana.id,
                    autor_id=ana.id,
                    categoria_id=categoria.id,
                    forma_pagamento_id=cartao.id,
                    numero_parcela=parcela.numero,
                )
                for parcela in parcelas
            ],
            compra=compra,
        )
        compra_id = gravados[0].compra_parcelada_id

        lancamentos.marcar_antecipadas(compra_id, [3])
        da_compra = lancamentos.da_compra(compra_id)

        assert [(item.numero_parcela, item.status) for item in da_compra] == [
            (1, StatusLancamento.ATIVO),
            (2, StatusLancamento.ATIVO),
            (3, StatusLancamento.ANTECIPADA),
        ]
        assert [item.mes_competencia for item in da_compra] == [
            date(2026, 10, 1),
            date(2026, 11, 1),
            date(2026, 12, 1),
        ]
        with pytest.raises(ErroDeDominio, match="já foi antecipada"):
            lancamentos.marcar_antecipadas(compra_id, [2, 3])


class TestRestricoesDoBanco:
    def test_recusa_receita_com_forma_de_pagamento(self, cadastros, lancamentos, ana):
        pix = _forma(cadastros, ana, "Pix Ana")
        proventos = _categoria(cadastros, TipoLancamento.RECEITA, "Proventos")

        with pytest.raises(IntegrityError, match="forma_so_na_despesa"):
            lancamentos.adicionar(
                [
                    Lancamento(
                        tipo=TipoLancamento.RECEITA,
                        valor=Decimal("5000"),
                        descricao="Salário",
                        data_real=date(2026, 11, 5),
                        mes_competencia=date(2026, 11, 1),
                        pessoa_id=ana.id,
                        autor_id=ana.id,
                        categoria_id=proventos.id,
                        forma_pagamento_id=pix.id,
                    )
                ]
            )

    def test_recusa_competencia_fora_do_dia_1(self, cadastros, lancamentos, ana):
        proventos = _categoria(cadastros, TipoLancamento.RECEITA, "Proventos")

        with pytest.raises(IntegrityError, match="competencia_no_dia_1"):
            lancamentos.adicionar(
                [
                    Lancamento(
                        tipo=TipoLancamento.RECEITA,
                        valor=Decimal("5000"),
                        descricao="Salário",
                        data_real=date(2026, 11, 5),
                        mes_competencia=date(2026, 11, 5),
                        pessoa_id=ana.id,
                        autor_id=ana.id,
                        categoria_id=proventos.id,
                    )
                ]
            )
