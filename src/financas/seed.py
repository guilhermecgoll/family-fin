"""Carrega pessoas, formas de pagamento e categorias iniciais no banco.

Uso: python -m financas.seed [config/seed.local.yaml]
"""

import argparse
from pathlib import Path

from sqlalchemy.orm import Session

from financas.adapters.db.seed import ResumoSeed, aplicar_seed
from financas.adapters.db.sessao import criar_engine
from financas.config import ConfiguracaoBase
from financas.services.seed import ler_seed

CAMINHO_PADRAO = Path("config/seed.local.yaml")


def executar(caminho: Path, url_banco: str) -> ResumoSeed:
    dados = ler_seed(caminho.read_text(encoding="utf-8"))
    engine = criar_engine(url_banco)
    try:
        with Session(engine) as sessao, sessao.begin():
            return aplicar_seed(sessao, dados)
    finally:
        engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("caminho", nargs="?", type=Path, default=CAMINHO_PADRAO)
    args = parser.parse_args(argv)

    resumo = executar(args.caminho, ConfiguracaoBase().database_url.get_secret_value())
    print(
        f"Pessoas: {resumo.pessoas_criadas} criadas, {resumo.pessoas_atualizadas} atualizadas. "
        f"Formas de pagamento: {resumo.formas_criadas} criadas, "
        f"{resumo.formas_atualizadas} atualizadas. "
        f"Categorias: {resumo.categorias_criadas} criadas."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
