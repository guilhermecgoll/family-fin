"""Grava o seed no banco sem duplicar: pessoas e formas por nome; categorias só no banco vazio.

Nada é apagado: pessoas e formas que saíram do arquivo continuam no banco, e as
categorias editadas pela família não são recriadas.
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from financas.adapters.db.modelos import CategoriaModelo, FormaPagamentoModelo, PessoaModelo
from financas.domain.categorias import CATEGORIAS_INICIAIS
from financas.services.seed import DadosSeed


@dataclass
class ResumoSeed:
    pessoas_criadas: int = 0
    pessoas_atualizadas: int = 0
    formas_criadas: int = 0
    formas_atualizadas: int = 0
    categorias_criadas: int = 0


def _atualizar(modelo: object, valores: dict[str, object]) -> bool:
    mudou = any(getattr(modelo, campo) != valor for campo, valor in valores.items())
    for campo, valor in valores.items():
        setattr(modelo, campo, valor)
    return mudou


def aplicar_seed(sessao: Session, dados: DadosSeed) -> ResumoSeed:
    resumo = ResumoSeed()

    pessoas = {modelo.nome: modelo for modelo in sessao.scalars(select(PessoaModelo))}
    for pessoa in dados.pessoas:
        valores = {"email": pessoa.email, "telegram_user_id": pessoa.telegram_user_id}
        modelo = pessoas.get(pessoa.nome)
        if modelo is None:
            pessoas[pessoa.nome] = PessoaModelo(nome=pessoa.nome, **valores)
            sessao.add(pessoas[pessoa.nome])
            resumo.pessoas_criadas += 1
        elif _atualizar(modelo, valores):
            resumo.pessoas_atualizadas += 1
    sessao.flush()

    formas = {modelo.nome: modelo for modelo in sessao.scalars(select(FormaPagamentoModelo))}
    for forma in dados.formas_pagamento:
        valores = {
            "tipo": forma.tipo,
            "dono_id": pessoas[forma.dono_nome].id if forma.dono_nome else None,
            "dia_fechamento": forma.dia_fechamento,
            "fecha_ultimo_dia": forma.fecha_ultimo_dia,
            "dia_vencimento": forma.vencimento,
        }
        usuarios = [pessoas[nome] for nome in forma.usuarios]
        modelo = formas.get(forma.nome)
        if modelo is None:
            sessao.add(FormaPagamentoModelo(nome=forma.nome, usuarios=usuarios, **valores))
            resumo.formas_criadas += 1
            continue
        mudou = _atualizar(modelo, valores)
        if {usuario.id for usuario in modelo.usuarios} != {usuario.id for usuario in usuarios}:
            modelo.usuarios = usuarios
            mudou = True
        if mudou:
            resumo.formas_atualizadas += 1

    if not sessao.scalar(select(func.count()).select_from(CategoriaModelo)):
        sessao.add_all(CategoriaModelo(nome=nome, tipo=tipo) for nome, tipo in CATEGORIAS_INICIAIS)
        resumo.categorias_criadas = len(CATEGORIAS_INICIAIS)

    sessao.flush()
    return resumo
