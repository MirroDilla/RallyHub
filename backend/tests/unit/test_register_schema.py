"""Validación del esquema de registro rápido (sin base de datos)."""
import pytest
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest

OK = {"first_name": " Ana ", "last_name": "Rojas", "email": " Ana@Club.Example ",
      "password": "Clave-Segura-2026"}


def test_valid_data_is_normalized():
    r = RegisterRequest(**OK)
    assert r.first_name == "Ana" and r.email == "ana@club.example"


@pytest.mark.parametrize("password", ["corta1", "soloLetrasLargas", "1234567890123"])
def test_password_rules(password):
    with pytest.raises(ValidationError):
        RegisterRequest(**{**OK, "password": password})


@pytest.mark.parametrize("field", ["first_name", "last_name"])
def test_blank_names_are_rejected(field):
    with pytest.raises(ValidationError):
        RegisterRequest(**{**OK, field: "   "})


def test_invalid_email_is_rejected():
    with pytest.raises(ValidationError):
        RegisterRequest(**{**OK, "email": "no-es-correo"})


def test_extra_fields_like_role_are_ignored():
    r = RegisterRequest(**{**OK, "role": "ADMIN"})
    assert not hasattr(r, "role")
