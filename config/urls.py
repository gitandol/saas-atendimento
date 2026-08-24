"""Declara as rotas HTTP publicas do projeto."""

from django.contrib import admin
from django.urls import path

from apps.contas.views.paginas.autenticacao import pagina_login
from apps.contas.views.paginas.perfil import pagina_perfil
from config.api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", api.urls),
    path("entrar/", pagina_login, name="entrar"),
    path("perfil/", pagina_perfil, name="perfil"),
]
