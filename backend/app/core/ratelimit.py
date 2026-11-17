"""Limitador sencillo de intentos de login fallidos (en memoria, por proceso).

Limitación documentada: con varios procesos/workers cada uno mantiene su propio
contador. La configuración estándar usa un único worker de Uvicorn.
"""
import threading
import time
from collections import deque
from collections.abc import Callable
from functools import lru_cache

from app.domain.errors import TooManyRequests


class LoginThrottle:
    def __init__(
        self,
        max_attempts: int = 5,
        window_seconds: int = 900,
        clock: Callable[[], float] = time.monotonic,
        max_keys: int = 10_000,
        message: str = "Demasiados intentos fallidos. Intenta de nuevo en unos minutos.",
    ):
        self.max_attempts = max_attempts
        self.window = window_seconds
        self._clock = clock
        self._max_keys = max_keys
        self._message = message
        self._failures: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        q = self._failures.setdefault(key, deque())
        while q and now - q[0] > self.window:
            q.popleft()
        if not q:
            self._failures.pop(key, None)
        return q

    def check(self, key: str) -> None:
        with self._lock:
            now = self._clock()
            q = self._prune(key, now)
            if len(q) >= self.max_attempts:
                raise TooManyRequests(self._message)

    def register_failure(self, key: str) -> None:
        with self._lock:
            now = self._clock()
            if len(self._failures) >= self._max_keys and key not in self._failures:
                self._failures.pop(next(iter(self._failures)))
            self._failures.setdefault(key, deque()).append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)


@lru_cache
def get_login_throttle() -> LoginThrottle:
    from app.core.config import get_settings

    cfg = get_settings()
    return LoginThrottle(cfg.login_max_attempts, cfg.login_window_seconds)


@lru_cache
def get_register_throttle() -> LoginThrottle:
    """Limita los registros rápidos por IP (cuenta cada intento, exitoso o no)."""
    from app.core.config import get_settings

    cfg = get_settings()
    return LoginThrottle(cfg.register_max_attempts, cfg.register_window_seconds,
                         message="Demasiados registros desde esta conexión. Intenta más tarde.")
