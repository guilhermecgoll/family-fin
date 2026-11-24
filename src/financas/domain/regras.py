"""Validações de um lançamento antes de gravar."""

from decimal import Decimal

from financas.domain.erros import ErroDeDominio
from financas.domain.tipos import Categoria, FormaPagamento, TipoLancamento, validar_valor


def validar_lancamento(
    tipo: TipoLancamento,
    valor: Decimal,
    categoria: Categoria,
    forma: FormaPagamento | None,
    pessoa_id: int,
) -> None:
    validar_valor(valor)
    if categoria.tipo is not tipo:
        raise ErroDeDominio(f"a categoria {categoria.nome} não é de {tipo}")
    if categoria.arquivada:
        raise ErroDeDominio(f"a categoria {categoria.nome} está arquivada")

    if tipo is TipoLancamento.RECEITA:
        if forma is not None:
            raise ErroDeDominio("receita não tem forma de pagamento")
        return

    if forma is None:
        raise ErroDeDominio("despesa precisa de forma de pagamento")
    if not forma.pode_usar(pessoa_id):
        raise ErroDeDominio(f"a forma de pagamento {forma.nome} não pode ser usada por essa pessoa")
