"""Expoe a aplicacao por meio da interface ASGI."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.producao")

application = get_asgi_application()
