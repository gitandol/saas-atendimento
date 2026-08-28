"""Declara a rota da caixa de entrada."""

from django.urls import path

from apps.atendimento.views.paginas.caixa_entrada import pagina_caixa_entrada

app_name = "atendimento"
urlpatterns = [
    path("caixa-de-entrada/", pagina_caixa_entrada, name="caixa_entrada"),
]
