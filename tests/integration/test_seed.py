from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from financas import seed
from financas.adapters.db.modelos import CategoriaModelo, FormaPagamentoModelo, PessoaModelo
from financas.adapters.db.seed import ResumoSeed, aplicar_seed
from financas.services.seed import ler_seed

EXEMPLO = Path(__file__).parents[2] / "config" / "seed.example.yaml"


def _dados(texto=None):
    return ler_seed(texto or EXEMPLO.read_text(encoding="utf-8"))


def test_primeira_carga_cria_tudo(sessao):
    resumo = aplicar_seed(sessao, _dados())

    assert resumo == ResumoSeed(pessoas_criadas=2, formas_criadas=6, categorias_criadas=16)


def test_segunda_carga_nao_duplica(sessao):
    aplicar_seed(sessao, _dados())

    assert aplicar_seed(sessao, _dados()) == ResumoSeed()
    assert len(sessao.scalars(select(PessoaModelo)).all()) == 2
    assert len(sessao.scalars(select(FormaPagamentoModelo)).all()) == 6
    assert len(sessao.scalars(select(CategoriaModelo)).all()) == 16


def test_atualiza_pessoas_e_formas_existentes(sessao):
    aplicar_seed(sessao, _dados())
    alterado = (
        EXEMPLO.read_text(encoding="utf-8")
        .replace("ana@example.com", "ana.nova@example.com")
        .replace("usuarios: [Ana, Bruno]", "usuarios: [Ana]")
        .replace("fechamento: 3", "fechamento: 5")
    )

    resumo = aplicar_seed(sessao, _dados(alterado))

    assert resumo == ResumoSeed(pessoas_atualizadas=1, formas_atualizadas=2)
    cartao_ana = sessao.scalar(
        select(FormaPagamentoModelo).where(FormaPagamentoModelo.nome == "Crédito Ana")
    )
    assert [usuario.nome for usuario in cartao_ana.usuarios] == ["Ana"]


def test_nao_recria_categorias_editadas_pela_familia(sessao):
    aplicar_seed(sessao, _dados())
    pets = sessao.scalar(select(CategoriaModelo).where(CategoriaModelo.nome == "Pets"))
    pets.nome = "Animais"
    sessao.flush()

    assert aplicar_seed(sessao, _dados()).categorias_criadas == 0
    assert sessao.scalar(select(CategoriaModelo).where(CategoriaModelo.nome == "Pets")) is None


def test_comando_grava_no_banco(banco_limpo, postgres_url, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", postgres_url)

    assert seed.main([str(EXEMPLO)]) == 0

    assert "Pessoas: 2 criadas" in capsys.readouterr().out
    with Session(banco_limpo) as sessao:
        assert len(sessao.scalars(select(PessoaModelo)).all()) == 2
