from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import Role
from app.schemas.common import ORMModel, check_password


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _norm(cls, v: str) -> str:
        return v.strip().lower()


class RegisterRequest(BaseModel):
    """Registro rápido de un estudiante (solo los datos mínimos)."""

    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    password: str

    @field_validator("first_name", "last_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Campo obligatorio.")
        return v

    @field_validator("email")
    @classmethod
    def _norm(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def _pw(cls, v: str) -> str:
        return check_password(v)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _pw(cls, v: str) -> str:
        return check_password(v)


class ChangeEmailRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_email: EmailStr

    @field_validator("new_email")
    @classmethod
    def _norm(cls, v: str) -> str:
        return v.strip().lower()


class UserRead(ORMModel):
    id: int
    email: str
    role: Role
    is_active: bool


class MeRead(BaseModel):
    user: UserRead
    display_name: str
    student_id: int | None = None
    coach_id: int | None = None
