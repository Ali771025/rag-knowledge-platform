from __future__ import annotations

from uuid import UUID

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.core.security import get_password_hash


class UserService:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    def create_user(self, *, email: str, password: str, full_name: str | None = None) -> User:
        existing = self.user_repository.get_by_email(email)
        if existing is not None:
            raise ValueError("User with this email already exists")

        hashed_password = get_password_hash(password)
        return self.user_repository.create(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
        )

    def get_user(self, user_id: UUID) -> User | None:
        return self.user_repository.get_by_id(user_id)

    def update_user(
        self,
        user_id: UUID,
        *,
        email: str | None = None,
        password: str | None = None,
        full_name: str | None = None,
        is_active: bool | None = None,
    ) -> User | None:
        user = self.user_repository.get_by_id(user_id)
        if user is None:
            return None

        updates: dict[str, object] = {}
        if email is not None and email != user.email:
            conflict = self.user_repository.get_by_email(email)
            if conflict is not None and conflict.id != user.id:
                raise ValueError("User with this email already exists")
            updates["email"] = email

        if password is not None:
            updates["hashed_password"] = get_password_hash(password)

        if full_name is not None:
            updates["full_name"] = full_name

        if is_active is not None:
            updates["is_active"] = is_active

        if not updates:
            return user

        return self.user_repository.update(user, **updates)

    def delete_user(self, user_id: UUID) -> bool:
        user = self.user_repository.get_by_id(user_id)
        if user is None:
            return False

        self.user_repository.delete(user)
        return True
