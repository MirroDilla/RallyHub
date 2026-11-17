"""Registro rápido de estudiantes (/auth/register)."""
from sqlalchemy import select

from app.core.config import get_settings
from app.models import AuditLog, Student, User
from app.models.enums import Level, Role
from tests.integration.helpers import make_student

API = "/api/v1"
NEW = {"first_name": "Ana", "last_name": "Rojas", "email": "Ana.Rojas@T.example",
       "password": "Clave-Segura-2026"}


def test_register_creates_student_and_opens_session(db, make_client):
    c = make_client()
    r = c.post(f"{API}/auth/register", json=NEW)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user"]["role"] == "STUDENT"
    assert body["user"]["email"] == "ana.rojas@t.example"  # correo normalizado
    assert body["display_name"] == "Ana Rojas" and body["student_id"]
    assert "password" not in r.text.lower()
    set_cookie = " ".join(r.headers.get_list("set-cookie")).lower()
    assert "rh_session=" in set_cookie and "httponly" in set_cookie
    # La sesión queda abierta: /auth/me responde sin volver a iniciar sesión.
    assert c.get(f"{API}/auth/me").json()["user"]["email"] == "ana.rojas@t.example"
    student = db.scalar(select(Student).where(Student.id == body["student_id"]))
    assert student.level == Level.BEGINNER and student.is_active
    log = db.scalar(select(AuditLog).where(AuditLog.action == "REGISTER"))
    assert log is not None and log.entity_id == student.id


def test_registered_student_can_log_in_again(make_client):
    make_client().post(f"{API}/auth/register", json=NEW)
    r = make_client().post(f"{API}/auth/login",
                           json={"email": "ana.rojas@t.example", "password": NEW["password"]})
    assert r.status_code == 200


def test_register_duplicate_email_is_conflict(db, make_client):
    make_student(db, 1)
    r = make_client().post(f"{API}/auth/register", json={**NEW, "email": "student1@t.example"})
    assert r.status_code == 409


def test_register_rejects_weak_password(make_client):
    r = make_client().post(f"{API}/auth/register", json={**NEW, "password": "corta1"})
    assert r.status_code == 422
    assert r.json()["errors"][0]["field"] == "password"
    assert "corta1" not in r.text  # el 422 no devuelve la entrada


def test_register_cannot_choose_role(db, make_client):
    r = make_client().post(f"{API}/auth/register", json={**NEW, "role": "ADMIN"})
    assert r.status_code == 201
    user = db.scalar(select(User).where(User.email == "ana.rojas@t.example"))
    assert user.role == Role.STUDENT


def test_register_can_be_disabled(make_client):
    from app.main import app

    disabled = get_settings().model_copy(update={"self_registration": False})
    app.dependency_overrides[get_settings] = lambda: disabled
    try:
        r = make_client().post(f"{API}/auth/register", json=NEW)
    finally:
        app.dependency_overrides.pop(get_settings, None)
    assert r.status_code == 403


def test_register_is_rate_limited_per_connection(make_client):
    limit = get_settings().register_max_attempts
    c = make_client()
    for i in range(limit):
        r = c.post(f"{API}/auth/register", json={**NEW, "email": f"nuevo{i}@t.example"})
        assert r.status_code == 201, r.text
    r = c.post(f"{API}/auth/register", json={**NEW, "email": "uno.mas@t.example"})
    assert r.status_code == 429


def test_register_page_is_served(make_client):
    r = make_client().get("/registro")
    assert r.status_code == 200 and "Registro rápido" in r.text
