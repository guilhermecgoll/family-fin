from collections.abc import Iterable, Sequence
from dataclasses import replace

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from financas.adapters.db.modelos import (
    CategoriaModelo,
    CompraParceladaModelo,
    FormaPagamentoModelo,
    LancamentoModelo,
    PessoaModelo,
)
from financas.domain.erros import ErroDeDominio
from financas.domain.texto import chave_alfabetica
from financas.domain.tipos import (
    Categoria,
    CompraParcelada,
    FormaPagamento,
    Lancamento,
    Pessoa,
    StatusLancamento,
    TipoLancamento,
)


def para_pessoa(modelo: PessoaModelo) -> Pessoa:
    return Pessoa(
        id=modelo.id,
        nome=modelo.nome,
        telegram_user_id=modelo.telegram_user_id,
        email=modelo.email,
    )


def para_categoria(modelo: CategoriaModelo) -> Categoria:
    return Categoria(id=modelo.id, nome=modelo.nome, tipo=modelo.tipo, arquivada=modelo.arquivada)


def para_forma(modelo: FormaPagamentoModelo) -> FormaPagamento:
    return FormaPagamento(
        id=modelo.id,
        nome=modelo.nome,
        tipo=modelo.tipo,
        dono_id=modelo.dono_id,
        usuarios_ids=frozenset(usuario.id for usuario in modelo.usuarios),
        dia_fechamento=modelo.dia_fechamento,
        fecha_ultimo_dia=modelo.fecha_ultimo_dia,
        dia_vencimento=modelo.dia_vencimento,
    )


def para_lancamento(modelo: LancamentoModelo) -> Lancamento:
    return Lancamento(
        id=modelo.id,
        tipo=modelo.tipo,
        valor=modelo.valor,
        descricao=modelo.descricao,
        data_real=modelo.data_real,
        mes_competencia=modelo.mes_competencia,
        registrado_em=modelo.registrado_em,
        status=modelo.status,
        pessoa_id=modelo.pessoa_id,
        autor_id=modelo.autor_id,
        categoria_id=modelo.categoria_id,
        forma_pagamento_id=modelo.forma_pagamento_id,
        compra_parcelada_id=modelo.compra_parcelada_id,
        numero_parcela=modelo.numero_parcela,
        eh_adiantamento=modelo.eh_adiantamento,
    )


def _para_modelo(lancamento: Lancamento) -> LancamentoModelo:
    return LancamentoModelo(
        tipo=lancamento.tipo,
        valor=lancamento.valor,
        descricao=lancamento.descricao,
        data_real=lancamento.data_real,
        mes_competencia=lancamento.mes_competencia,
        status=lancamento.status,
        pessoa_id=lancamento.pessoa_id,
        autor_id=lancamento.autor_id,
        categoria_id=lancamento.categoria_id,
        forma_pagamento_id=lancamento.forma_pagamento_id,
        compra_parcelada_id=lancamento.compra_parcelada_id,
        numero_parcela=lancamento.numero_parcela,
        eh_adiantamento=lancamento.eh_adiantamento,
    )


class RepositorioCadastrosSql:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def pessoas(self) -> list[Pessoa]:
        pessoas = [para_pessoa(modelo) for modelo in self._sessao.scalars(select(PessoaModelo))]
        return sorted(pessoas, key=lambda pessoa: chave_alfabetica(pessoa.nome))

    def pessoa_por_telegram(self, telegram_user_id: int) -> Pessoa | None:
        modelo = self._sessao.scalar(
            select(PessoaModelo).where(PessoaModelo.telegram_user_id == telegram_user_id)
        )
        return para_pessoa(modelo) if modelo else None

    def pessoa_por_email(self, email: str) -> Pessoa | None:
        modelo = self._sessao.scalar(
            select(PessoaModelo).where(PessoaModelo.email == email.strip().lower())
        )
        return para_pessoa(modelo) if modelo else None

    def categorias(self, tipo: TipoLancamento) -> list[Categoria]:
        modelos = self._sessao.scalars(
            select(CategoriaModelo).where(
                CategoriaModelo.tipo == tipo, CategoriaModelo.arquivada.is_(False)
            )
        )
        categorias = [para_categoria(modelo) for modelo in modelos]
        return sorted(categorias, key=lambda categoria: chave_alfabetica(categoria.nome))

    def forma(self, forma_id: int) -> FormaPagamento | None:
        modelo = self._sessao.get(FormaPagamentoModelo, forma_id)
        return para_forma(modelo) if modelo else None

    def formas_da_pessoa(self, pessoa_id: int) -> list[FormaPagamento]:
        formas = (
            para_forma(modelo) for modelo in self._sessao.scalars(select(FormaPagamentoModelo))
        )
        return sorted(
            (forma for forma in formas if forma.pode_usar(pessoa_id)),
            key=lambda forma: chave_alfabetica(forma.nome),
        )


class RepositorioLancamentosSql:
    def __init__(self, sessao: Session) -> None:
        self._sessao = sessao

    def adicionar(
        self, lancamentos: Sequence[Lancamento], compra: CompraParcelada | None = None
    ) -> list[Lancamento]:
        if compra is not None:
            compra_modelo = CompraParceladaModelo(
                descricao=compra.descricao,
                valor_total=compra.valor_total,
                num_parcelas=compra.num_parcelas,
                data_real=compra.data_real,
            )
            self._sessao.add(compra_modelo)
            self._sessao.flush()
            lancamentos = [
                replace(lancamento, compra_parcelada_id=compra_modelo.id)
                for lancamento in lancamentos
            ]

        modelos = [_para_modelo(lancamento) for lancamento in lancamentos]
        self._sessao.add_all(modelos)
        self._sessao.flush()
        return [para_lancamento(modelo) for modelo in modelos]

    def da_compra(self, compra_id: int) -> list[Lancamento]:
        modelos = self._sessao.scalars(
            select(LancamentoModelo)
            .where(LancamentoModelo.compra_parcelada_id == compra_id)
            .order_by(LancamentoModelo.numero_parcela.nulls_last(), LancamentoModelo.id)
        )
        return [para_lancamento(modelo) for modelo in modelos]

    def marcar_antecipadas(self, compra_id: int, numeros: Iterable[int]) -> None:
        numeros = set(numeros)
        resultado = self._sessao.execute(
            update(LancamentoModelo)
            .where(
                LancamentoModelo.compra_parcelada_id == compra_id,
                LancamentoModelo.numero_parcela.in_(numeros),
                LancamentoModelo.status == StatusLancamento.ATIVO,
            )
            .values(status=StatusLancamento.ANTECIPADA)
            .execution_options(synchronize_session="fetch")
        )
        if resultado.rowcount != len(numeros):
            raise ErroDeDominio("alguma das parcelas não existe ou já foi antecipada")
