"""Declara rotas das paginas de configuracao de IA."""

from django.urls import path

from apps.ia.views.paginas.configuracao_ia import pagina_configuracao_ia
from apps.ia.views.paginas.conhecimento import pagina_conhecimento
from apps.ia.views.paginas.perguntas_frequentes import pagina_perguntas_frequentes

app_name = "ia"
urlpatterns = [
    path("configuracao/", pagina_configuracao_ia, name="configuracao"),
    path("conhecimentos/", pagina_conhecimento, name="conhecimentos"),
    path(
        "perguntas-frequentes/",
        pagina_perguntas_frequentes,
        name="perguntas_frequentes",
    ),
]
