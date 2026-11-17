"""Configuración centralizada (variables de entorno). Ningún secreto vive en el código."""

from __future__ import annotations

from datetime import time
from functools import lru_cache
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url

from app.domain.booking_rules import BookingPolicy

PLACEHOLDER_PREFIX = "change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    docs_enabled: bool = True

    secret_key: SecretStr = Field(min_length=32)
    access_token_minutes: int = Field(60, ge=5, le=1440)
    cookie_secure: bool = False
    allowed_origins: str = ""  # lista separada por comas; vacío = solo mismo origen
    max_body_bytes: int = 1_048_576

    database_url: str | None = None
    db_host: str = "db"
    db_port: int = 3306
    db_name: str = "rallyhub"
    db_user: str = "rallyhub"
    db_password: SecretStr = SecretStr("")
    db_pool_size: int = 10

    timezone: str = "America/Bogota"
    opening_time: time = time(8, 0)
    closing_time: time = time(21, 0)
    reservation_min_minutes: int = 30
    reservation_max_minutes: int = 120
    reservation_max_advance_days: int = 30
    cancel_min_hours_before: int = 2

    login_max_attempts: int = 5
    login_window_seconds: int = 900

    # Registro rápido: un estudiante crea su propia cuenta desde /registro
    self_registration: bool = True
    register_max_attempts: int = 5  # registros por conexión (IP) dentro de la ventana
    register_window_seconds: int = 3600

    @model_validator(mode="after")
    def _check(self) -> Settings:
        if self.opening_time >= self.closing_time:
            raise ValueError("OPENING_TIME debe ser anterior a CLOSING_TIME")
        if self.reservation_min_minutes > self.reservation_max_minutes:
            raise ValueError("RESERVATION_MIN_MINUTES no puede superar RESERVATION_MAX_MINUTES")
        if self.environment == "production":
            if self.secret_key.get_secret_value().startswith(PLACEHOLDER_PREFIX):
                raise ValueError("SECRET_KEY de ejemplo no permitida en producción")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE debe ser true en producción (HTTPS)")
        return self

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def sqlalchemy_url(self) -> URL:
        if self.database_url:
            return make_url(self.database_url)
        return URL.create(
            "mysql+pymysql",
            username=self.db_user,
            password=self.db_password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query={"charset": "utf8mb4"},
        )

    @property
    def origins(self) -> set[str]:
        return {o.strip().rstrip("/") for o in self.allowed_origins.split(",") if o.strip()}

    @property
    def open_minutes_per_day(self) -> int:
        o, c = self.opening_time, self.closing_time
        return (c.hour * 60 + c.minute) - (o.hour * 60 + o.minute)

    @property
    def booking_policy(self) -> BookingPolicy:
        return BookingPolicy(
            tz=self.tz,
            open_time=self.opening_time,
            close_time=self.closing_time,
            min_minutes=self.reservation_min_minutes,
            max_minutes=self.reservation_max_minutes,
            max_advance_days=self.reservation_max_advance_days,
            cancel_min_hours=self.cancel_min_hours_before,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # los valores vienen del entorno
