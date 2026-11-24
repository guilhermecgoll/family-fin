"""Leitura e validação do arquivo de seed (pessoas e formas de pagamento da família)."""

from collections import Counter
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from financas.domain.tipos import TipoForma, validar_forma

FAMILIA = "familia"


class _Modelo(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PessoaSeed(_Modelo):
    nome: str = Field(min_length=1, max_length=100)
    email: str | None = None
    telegram_user_id: int | None = None

    @field_validator("email")
    @classmethod
    def _normalizar_email(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        valor = valor.strip().lower()
        if "@" not in valor:
            raise ValueError(f"e-mail inválido: {valor}")
        return valor


class FormaSeed(_Modelo):
    nome: str = Field(min_length=1, max_length=100)
    tipo: TipoForma
    dono: str = Field(description='"familia" ou o nome de uma pessoa')
    usuarios: tuple[str, ...] = ()
    fechamento: Literal["ultimo_dia"] | int | None = None
    vencimento: int | None = None

    @property
    def dono_nome(self) -> str | None:
        return None if self.dono == FAMILIA else self.dono

    @property
    def dia_fechamento(self) -> int | None:
        return self.fechamento if isinstance(self.fechamento, int) else None

    @property
    def fecha_ultimo_dia(self) -> bool:
        return self.fechamento == "ultimo_dia"

    @model_validator(mode="after")
    def _validar_regras(self) -> Self:
        validar_forma(
            self.tipo,
            tem_dono=self.dono_nome is not None,
            tem_usuarios=bool(self.usuarios),
            dia_fechamento=self.dia_fechamento,
            fecha_ultimo_dia=self.fecha_ultimo_dia,
            dia_vencimento=self.vencimento,
        )
        return self


def _repetidos(valores: list[object]) -> list[str]:
    contagem = Counter(valor for valor in valores if valor is not None)
    return sorted(str(valor) for valor, vezes in contagem.items() if vezes > 1)


class DadosSeed(_Modelo):
    pessoas: tuple[PessoaSeed, ...] = Field(min_length=1)
    formas_pagamento: tuple[FormaSeed, ...] = ()

    @model_validator(mode="after")
    def _validar_referencias(self) -> Self:
        for campo, valores in (
            ("nome de pessoa", [pessoa.nome for pessoa in self.pessoas]),
            ("e-mail", [pessoa.email for pessoa in self.pessoas]),
            ("telegram_user_id", [pessoa.telegram_user_id for pessoa in self.pessoas]),
            ("nome de forma de pagamento", [forma.nome for forma in self.formas_pagamento]),
        ):
            if repetidos := _repetidos(valores):
                raise ValueError(f"{campo} repetido: {', '.join(repetidos)}")

        nomes = {pessoa.nome for pessoa in self.pessoas}
        for forma in self.formas_pagamento:
            citados = [forma.dono_nome, *forma.usuarios]
            desconhecidos = [nome for nome in citados if nome is not None and nome not in nomes]
            if desconhecidos:
                raise ValueError(
                    f"forma {forma.nome} cita pessoa desconhecida: {', '.join(desconhecidos)}"
                )
        return self


def ler_seed(texto: str) -> DadosSeed:
    return DadosSeed.model_validate(yaml.safe_load(texto))
