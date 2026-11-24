"""Interfaces de persistência usadas pelos serviços; implementações em `adapters/db`."""

from collections.abc import Iterable, Sequence
from typing import Protocol, runtime_checkable

from financas.domain.tipos import (
    Categoria,
    CompraParcelada,
    FormaPagamento,
    Lancamento,
    Pessoa,
    TipoLancamento,
)


@runtime_checkable
class RepositorioCadastros(Protocol):
    def pessoas(self) -> list[Pessoa]: ...

    def pessoa_por_telegram(self, telegram_user_id: int) -> Pessoa | None: ...

    def pessoa_por_email(self, email: str) -> Pessoa | None: ...

    def categorias(self, tipo: TipoLancamento) -> list[Categoria]: ...

    def forma(self, forma_id: int) -> FormaPagamento | None: ...

    def formas_da_pessoa(self, pessoa_id: int) -> list[FormaPagamento]: ...


@runtime_checkable
class RepositorioLancamentos(Protocol):
    def adicionar(
        self, lancamentos: Sequence[Lancamento], compra: CompraParcelada | None = None
    ) -> list[Lancamento]:
        """Grava os lançamentos; com `compra`, grava a compra e liga os lançamentos a ela."""
        ...

    def da_compra(self, compra_id: int) -> list[Lancamento]: ...

    def marcar_antecipadas(self, compra_id: int, numeros: Iterable[int]) -> None: ...
