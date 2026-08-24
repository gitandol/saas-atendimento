"""Modelo de usuario autenticado pelo endereco de e-mail."""

from uuid import uuid4

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UsuarioManager(BaseUserManager):
    """Cria usuarios cujo identificador de login e o e-mail."""

    use_in_migrations = True

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        """Cria um usuario normalizando seu e-mail."""
        if not email:
            raise ValueError("O e-mail e obrigatorio.")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        """Cria um superusuario autenticado pelo e-mail."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superusuario deve ter is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superusuario deve ter is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class Usuario(AbstractUser):
    """Usuario da plataforma identificado unicamente por e-mail."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    username = None
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UsuarioManager()
