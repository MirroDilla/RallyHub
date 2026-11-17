"""Fixtures de integración. SEGURIDAD: se niegan a correr contra una base que no termine en `_test`."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND.parent))  # para importar `scripts.seed`

from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_engine, get_sessionmaker  # noqa: E402
from tests.integration import helpers  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _database():
    url = get_settings().sqlalchemy_url
    if not (url.database or "").endswith("_test"):
        pytest.exit(f"Rechazado: la base '{url.database}' no termina en _test.", returncode=2)
    from alembic.config import Config

    from alembic import command

    engine = get_engine()
    with engine.begin() as conn:  # partir de una base vacía
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for name in inspect(conn).get_table_names():
            conn.execute(text(f"DROP TABLE IF EXISTS `{name}`"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    command.upgrade(cfg, "head")
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    with get_engine().begin() as conn:
        conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for table in Base.metadata.sorted_tables:
            conn.execute(text(f"TRUNCATE TABLE `{table.name}`"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))


@pytest.fixture(autouse=True)
def _reset_login_throttle():
    from app.core.ratelimit import get_login_throttle, get_register_throttle

    get_login_throttle.cache_clear()  # el limitador es global al proceso: aislar cada prueba
    get_register_throttle.cache_clear()
    yield


@pytest.fixture
def db():
    with get_sessionmaker()() as session:
        yield session


@pytest.fixture
def make_client():
    """Fábrica de clientes autenticados (cada uno con su propio cookie jar y cabecera CSRF)."""
    from app.main import app

    created: list[TestClient] = []

    def factory(email: str | None = None, password: str = helpers.PASSWORD) -> TestClient:
        client = TestClient(app)
        created.append(client)
        if email:
            r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
            assert r.status_code == 200, r.text
            client.headers["X-CSRF-Token"] = client.cookies.get("rh_csrf")
        return client

    yield factory
    for c in created:
        c.close()
