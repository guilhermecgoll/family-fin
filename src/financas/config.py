"""Configuração lida de variáveis de ambiente (e do `.env` em desenvolvimento).

Cada processo carrega só o que usa: `ConfiguracaoBase` para migrações e seed,
`ConfiguracaoBot` para o bot e `ConfiguracaoWeb` para a página web.
"""

from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _separar_por_virgula(valor: object) -> object:
    if isinstance(valor, str):
        return [parte.strip() for parte in valor.split(",") if parte.strip()]
    return valor


def _exigir_nao_vazia[T](valores: list[T]) -> list[T]:
    if not valores:
        raise ValueError("a lista não pode ser vazia")
    return valores


class ConfiguracaoBase(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["dev", "prod"] = "prod"
    database_url: SecretStr
    timezone: str = "America/Sao_Paulo"

    @field_validator("timezone")
    @classmethod
    def _validar_fuso(cls, valor: str) -> str:
        try:
            ZoneInfo(valor)
        except (ZoneInfoNotFoundError, ValueError) as erro:
            raise ValueError(f"fuso horário desconhecido: {valor}") from erro
        return valor

    @property
    def fuso(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


class ConfiguracaoBot(ConfiguracaoBase):
    telegram_bot_token: SecretStr
    telegram_allowed_ids: Annotated[list[int], NoDecode]
    gemini_api_key: SecretStr
    gemini_model: str

    @field_validator("telegram_allowed_ids", mode="before")
    @classmethod
    def _separar_ids(cls, valor: object) -> object:
        return _separar_por_virgula(valor)

    @field_validator("telegram_allowed_ids")
    @classmethod
    def _validar_ids(cls, valores: list[int]) -> list[int]:
        return _exigir_nao_vazia(valores)


class ConfiguracaoWeb(ConfiguracaoBase):
    access_allowed_emails: Annotated[list[str], NoDecode]
    access_team_domain: str | None = None
    access_aud: str | None = None
    dev_user_email: str | None = None

    @field_validator("access_allowed_emails", mode="before")
    @classmethod
    def _separar_emails(cls, valor: object) -> object:
        return _separar_por_virgula(valor)

    @field_validator("access_allowed_emails")
    @classmethod
    def _normalizar_emails(cls, valores: list[str]) -> list[str]:
        return _exigir_nao_vazia([email.lower() for email in valores])

    @field_validator("dev_user_email")
    @classmethod
    def _normalizar_email_dev(cls, valor: str | None) -> str | None:
        return valor.strip().lower() if valor else None

    @model_validator(mode="after")
    def _validar_ambiente(self) -> "ConfiguracaoWeb":
        if self.app_env == "prod":
            if self.dev_user_email:
                raise ValueError("DEV_USER_EMAIL só é permitido com APP_ENV=dev")
            if not (self.access_team_domain and self.access_aud):
                raise ValueError("ACCESS_TEAM_DOMAIN e ACCESS_AUD são obrigatórios em produção")
        return self
