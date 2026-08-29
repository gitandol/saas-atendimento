"""Declara a rota da pagina do dashboard operacional."""

from django.urls import path

from apps.painel.views.paginas.dashboard import pagina_dashboard

app_name = "painel"
urlpatterns = [
    path("", pagina_dashboard, name="dashboard"),
]
