"""Declara as rotas de paginas da configuracao empresarial."""

from django.urls import path

from apps.empresas.views.paginas.configuracao_empresa import (
    pagina_configuracao_empresa,
)

app_name = "empresas"
urlpatterns = [
    path("configuracao/", pagina_configuracao_empresa, name="configuracao"),
]
