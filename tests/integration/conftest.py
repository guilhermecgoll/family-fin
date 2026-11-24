import os
from pathlib import Path

import pytest

PASTA = Path(__file__).parent


def pytest_collection_modifyitems(items):
    for item in items:
        if PASTA in item.path.parents:
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session")
def postgres_url():
    """URL do Postgres descartável dos testes (serviço `db-test` do compose).

    Sem TEST_DATABASE_URL, os testes são pulados, exceto com EXIGIR_BANCO_TESTE=1 (CI).
    """
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        if os.environ.get("EXIGIR_BANCO_TESTE") == "1":
            pytest.fail("TEST_DATABASE_URL não definida")
        pytest.skip("TEST_DATABASE_URL não definida; rode via docker compose run --rm dev")
    return url
