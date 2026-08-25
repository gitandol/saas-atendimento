"""Declara rotas das paginas de configuracao de IA."""

from django.urls import path

from apps.ia.views.paginas.configuracao_ia import pagina_configuracao_ia

app_name = "ia"
urlpatterns = [path("configuracao/", pagina_configuracao_ia, name="configuracao")]
