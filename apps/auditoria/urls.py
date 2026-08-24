"""Declara as rotas de pagina da auditoria."""

from django.urls import path

from apps.auditoria.views.paginas.historico import pagina_historico

app_name = "auditoria"
urlpatterns = [path("historico/", pagina_historico, name="historico")]
