"""Declara as rotas de pagina da ajuda."""

from django.urls import path

from apps.ajuda.views.paginas.topico import pagina_topico

app_name = "ajuda"
urlpatterns = [path("<slug:slug>/", pagina_topico, name="topico")]
