"""Define configuracoes compartilhadas por todos os ambientes."""

import os
from pathlib import Path

from config.logging import CONFIGURACAO_LOGGING

BASE_DIR = Path(__file__).resolve().parents[2]

SECRET_KEY = os.getenv("SECRET_KEY", "")
DEBUG = False
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,web").split(",")
    if host.strip()
]
CSRF_TRUSTED_ORIGINS = [
    origem.strip()
    for origem in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origem.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.contas",
    "apps.empresas",
    "apps.auditoria",
    "apps.ajuda",
    "apps.ia",
    "apps.whatsapp",
    "apps.atendimento",
    "apps.painel",
]

AUTH_USER_MODEL = "contas.Usuario"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.nucleo.middleware.correlacao.CorrelacaoMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.empresas.middleware.empresa_ativa.EmpresaAtivaMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
DATA_UPLOAD_MAX_MEMORY_SIZE = 262_144

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "atendimento"),
        "USER": os.getenv("POSTGRES_USER", "atendimento"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "HOST": os.getenv("POSTGRES_HOST", "postgres"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        )
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Rio_Branco"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}
CELERY_BROKER_URL = REDIS_URL

LOGGING = CONFIGURACAO_LOGGING
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300

DOCS_AUTENTICADA = True
LOGIN_URL = "/admin/login/"
IA_CHAVE_CRIPTOGRAFIA = os.getenv("IA_CHAVE_CRIPTOGRAFIA", "")
EVOLUTION_INTERNAL_URL = os.getenv(
    "EVOLUTION_INTERNAL_URL", "http://evolution:8080"
).rstrip("/")
EVOLUTION_WEBHOOK_BASE_URL = os.getenv(
    "EVOLUTION_WEBHOOK_BASE_URL", "http://web:8000"
).rstrip("/")
WHATSAPP_HOSTS_INTERNOS_PERMITIDOS = frozenset(
    host.strip().rstrip(".").lower()
    for host in os.getenv("WHATSAPP_HOSTS_INTERNOS_PERMITIDOS", "evolution").split(",")
    if host.strip()
)
