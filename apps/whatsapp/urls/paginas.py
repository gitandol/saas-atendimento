"""Declara a rota da pagina de conexao do WhatsApp."""

from django.urls import path

from apps.whatsapp.views.paginas.configuracao import pagina_configuracao_whatsapp

app_name = "whatsapp"
urlpatterns = [
    path("configuracao/", pagina_configuracao_whatsapp, name="configuracao"),
]
