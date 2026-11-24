from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from financas.config import ConfiguracaoBase, ConfiguracaoBot, ConfiguracaoWeb

URL = "postgresql+psycopg://u:p@localhost:5432/financas"

VARIAVEIS = [
    "APP_ENV",
    "DATABASE_URL",
    "TIMEZONE",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_ALLOWED_IDS",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "ACCESS_ALLOWED_EMAILS",
    "ACCESS_TEAM_DOMAIN",
    "ACCESS_AUD",
    "DEV_USER_EMAIL",
]


@pytest.fixture(autouse=True)
def ambiente_limpo(monkeypatch):
    for nome in VARIAVEIS:
        monkeypatch.delenv(nome, raising=False)
    monkeypatch.setenv("DATABASE_URL", URL)


@pytest.fixture
def ambiente_bot(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token-falso")
    monkeypatch.setenv("TELEGRAM_ALLOWED_IDS", "100000001, 100000002")
    monkeypatch.setenv("GEMINI_API_KEY", "chave-falsa")
    monkeypatch.setenv("GEMINI_MODEL", "modelo-falso")


@pytest.fixture
def ambiente_web(monkeypatch):
    monkeypatch.setenv("ACCESS_ALLOWED_EMAILS", " Ana@Example.com ,bruno@example.com,")
    monkeypatch.setenv("ACCESS_TEAM_DOMAIN", "familia.cloudflareaccess.com")
    monkeypatch.setenv("ACCESS_AUD", "aud-falso")


class TestConfiguracaoBase:
    def test_le_variaveis_com_padroes(self):
        config = ConfiguracaoBase(_env_file=None)

        assert config.database_url.get_secret_value() == URL
        assert config.app_env == "prod"
        assert config.fuso == ZoneInfo("America/Sao_Paulo")

    def test_url_do_banco_nao_aparece_na_representacao(self):
        assert "u:p" not in repr(ConfiguracaoBase(_env_file=None))

    def test_falha_sem_url_do_banco(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL")

        with pytest.raises(ValidationError, match="database_url"):
            ConfiguracaoBase(_env_file=None)

    def test_aceita_outro_fuso(self, monkeypatch):
        monkeypatch.setenv("TIMEZONE", "America/Manaus")

        assert ConfiguracaoBase(_env_file=None).fuso == ZoneInfo("America/Manaus")

    @pytest.mark.parametrize("fuso", ["America/Atlantida", "../etc", ""])
    def test_recusa_fuso_desconhecido(self, monkeypatch, fuso):
        monkeypatch.setenv("TIMEZONE", fuso)

        with pytest.raises(ValidationError, match="fuso horário desconhecido"):
            ConfiguracaoBase(_env_file=None)

    def test_recusa_ambiente_desconhecido(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "teste")

        with pytest.raises(ValidationError, match="app_env"):
            ConfiguracaoBase(_env_file=None)


class TestConfiguracaoBot:
    def test_separa_ids_permitidos(self, ambiente_bot):
        config = ConfiguracaoBot(_env_file=None)

        assert config.telegram_allowed_ids == [100000001, 100000002]
        assert config.telegram_bot_token.get_secret_value() == "token-falso"
        assert config.gemini_model == "modelo-falso"

    def test_aceita_ids_ja_em_lista(self, ambiente_bot):
        config = ConfiguracaoBot(_env_file=None, telegram_allowed_ids=[100000003])

        assert config.telegram_allowed_ids == [100000003]

    def test_recusa_lista_de_ids_vazia(self, ambiente_bot, monkeypatch):
        monkeypatch.setenv("TELEGRAM_ALLOWED_IDS", " , ")

        with pytest.raises(ValidationError, match="não pode ser vazia"):
            ConfiguracaoBot(_env_file=None)

    def test_recusa_id_nao_numerico(self, ambiente_bot, monkeypatch):
        monkeypatch.setenv("TELEGRAM_ALLOWED_IDS", "100000001,abc")

        with pytest.raises(ValidationError):
            ConfiguracaoBot(_env_file=None)

    @pytest.mark.parametrize("ausente", ["TELEGRAM_BOT_TOKEN", "GEMINI_API_KEY"])
    def test_falha_sem_segredo(self, ambiente_bot, monkeypatch, ausente):
        monkeypatch.delenv(ausente)

        with pytest.raises(ValidationError, match=ausente.lower()):
            ConfiguracaoBot(_env_file=None)


class TestConfiguracaoWeb:
    def test_normaliza_emails_permitidos(self, ambiente_web):
        config = ConfiguracaoWeb(_env_file=None)

        assert config.access_allowed_emails == ["ana@example.com", "bruno@example.com"]
        assert config.dev_user_email is None

    def test_recusa_lista_de_emails_vazia(self, ambiente_web, monkeypatch):
        monkeypatch.setenv("ACCESS_ALLOWED_EMAILS", "")

        with pytest.raises(ValidationError, match="não pode ser vazia"):
            ConfiguracaoWeb(_env_file=None)

    def test_producao_exige_dados_do_access(self, ambiente_web, monkeypatch):
        monkeypatch.delenv("ACCESS_AUD")

        with pytest.raises(ValidationError, match="obrigatórios em produção"):
            ConfiguracaoWeb(_env_file=None)

    def test_producao_recusa_usuario_de_desenvolvimento(self, ambiente_web, monkeypatch):
        monkeypatch.setenv("DEV_USER_EMAIL", "ana@example.com")

        with pytest.raises(ValidationError, match="só é permitido com APP_ENV=dev"):
            ConfiguracaoWeb(_env_file=None)

    def test_desenvolvimento_dispensa_access_e_aceita_usuario_simulado(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "dev")
        monkeypatch.setenv("ACCESS_ALLOWED_EMAILS", "ana@example.com")
        monkeypatch.setenv("DEV_USER_EMAIL", " Ana@Example.com ")

        config = ConfiguracaoWeb(_env_file=None)

        assert config.dev_user_email == "ana@example.com"
        assert config.access_aud is None
