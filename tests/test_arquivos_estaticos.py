"""Protege a entrega dos arquivos estaticos em producao."""

from pathlib import Path

from django.core.management import call_command
from django.test import Client


def test_css_do_admin_e_servido_com_debug_desabilitado(
    settings: object,
    tmp_path: Path,
) -> None:
    """Evita que o admin seja entregue sem estilos pelo servidor WSGI."""
    settings.DEBUG = False
    settings.STATIC_ROOT = tmp_path / "staticfiles"
    call_command("collectstatic", interactive=False, verbosity=0)

    resposta = Client().get("/static/admin/css/base.css")

    assert resposta.status_code == 200
    assert resposta.headers["Content-Type"].startswith("text/css")
