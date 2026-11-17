from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from app.core.passwords import hash_password, verify_password
from app.core.tokens import create_session_token, new_csrf_token
from app.domain.errors import (
    AuthenticationError,
    DuplicateError,
    InvalidCurrentPassword,
    NotFoundError,
)
from app.models import Student, User
from app.models.enums import Level, Role
from app.repositories.people import UserRepository
from app.schemas.auth import MeRead, RegisterRequest, UserRead
from app.services.base import Service, require_roles


class AuthService(Service):
    def login(self, email: str, password: str) -> tuple[User, str, str]:
        """Valida credenciales. Mensaje único para usuario inexistente/clave errónea/inactivo."""
        user = UserRepository(self.db).by_email(email)
        ok = verify_password(password, user.password_hash if user else None)
        if user is None or not ok or not user.is_active:
            raise AuthenticationError("Credenciales inválidas.")
        csrf = new_csrf_token()
        token = create_session_token(
            self.settings.secret_key.get_secret_value(), user.id, user.token_version, csrf,
            self.settings.access_token_minutes, now=self.now(),
        )
        return user, token, csrf

    def register(self, data: RegisterRequest) -> tuple[User, str, str]:
        """Registro rápido: crea un estudiante (nunca otro rol) y abre su sesión."""
        if UserRepository(self.db).by_email(data.email):
            raise DuplicateError("Ya existe un usuario con ese correo.")
        user = User(email=data.email, password_hash=hash_password(data.password),
                    role=Role.STUDENT, is_active=True, token_version=0)
        student = Student(user=user, first_name=data.first_name, last_name=data.last_name,
                          level=Level.BEGINNER, is_active=True)
        try:
            self.db.add_all([user, student])
            self.db.flush()
            self.audit(user, "REGISTER", "student", student.id, "registro rápido")
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateError("Ya existe un usuario con ese correo.") from exc
        csrf = new_csrf_token()
        token = create_session_token(
            self.settings.secret_key.get_secret_value(), user.id, user.token_version, csrf,
            self.settings.access_token_minutes, now=self.now(),
        )
        return user, token, csrf

    def logout(self, user: User) -> None:
        """Invalida todas las sesiones del usuario incrementando su versión de token."""
        user.token_version += 1
        self.db.commit()

    def change_password(self, user: User, current: str, new: str) -> None:
        if not verify_password(current, user.password_hash):
            raise InvalidCurrentPassword("La contraseña actual no es correcta.")
        user.password_hash = hash_password(new)
        user.token_version += 1  # cierra las demás sesiones
        self.db.commit()

    def change_email(self, user: User, current: str, new_email: str) -> None:
        """Cambia el correo de acceso; exige la contraseña actual. La sesión sigue vigente."""
        if not verify_password(current, user.password_hash):
            raise InvalidCurrentPassword("La contraseña actual no es correcta.")
        new_email = new_email.strip().lower()
        if new_email == user.email:
            return
        if UserRepository(self.db).by_email(new_email):
            raise DuplicateError("Ya existe un usuario con ese correo.")
        old = user.email
        user.email = new_email
        self.audit(user, "CHANGE_EMAIL", "user", user.id, f"{old} -> {new_email}")
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateError("Ya existe un usuario con ese correo.") from exc

    def list_users(self, actor: User, limit: int, offset: int):
        require_roles(actor, Role.ADMIN)
        from sqlalchemy import func, select

        total = self.db.scalar(select(func.count()).select_from(User)) or 0
        items = list(self.db.scalars(select(User).order_by(User.id).limit(limit).offset(offset)))
        return items, int(total)

    def admin_reset_password(self, actor: User, user_id: int, new_password: str) -> None:
        require_roles(actor, Role.ADMIN)
        target = self.db.get(User, user_id)
        if target is None:
            raise NotFoundError("Usuario no encontrado.")
        target.password_hash = hash_password(new_password)
        target.token_version += 1
        self.audit(actor, "RESET_PASSWORD", "user", target.id)
        self.db.commit()

    @staticmethod
    def me(user: User) -> MeRead:
        name = user.email
        if user.student:
            name = user.student.full_name
        elif user.coach:
            name = user.coach.full_name
        elif user.role.value == "ADMIN":
            name = "Administración"
        return MeRead(
            user=UserRead.model_validate(user), display_name=name,
            student_id=user.student.id if user.student else None,
            coach_id=user.coach.id if user.coach else None,
        )
