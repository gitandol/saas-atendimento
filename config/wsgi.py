"""Expoe a aplicacao por meio da interface WSGI."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.producao")

application = get_wsgi_application()
