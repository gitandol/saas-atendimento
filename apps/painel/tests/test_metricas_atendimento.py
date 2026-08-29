"""Testes das metricas operacionais do dashboard."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta

import pytest
from django.core.cache import cache

from apps.atendimento.models import Conversa, Mensagem
from apps.atendimento.tests.factories import (
    ConversaFactory,
    EmpresaFactory,
    MensagemFactory,
)
from apps.ia.models import ConfiguracaoIA
from apps.painel.services.metricas_atendimento import (
    MetricasAtendimento,
    obter_metricas_do_dia,
)
from apps.whatsapp.integrations.protocolos import EstadoConexao
from apps.whatsapp.models import ConfiguracaoWhatsApp


@pytest.fixture(autouse=True)
def limpar_cache_metricas() -> None:
    """Evita que uma metrica armazenada interfira em outro cenario."""
    cache.clear()


@pytest.mark.django_db
def test_metricas_sem_dados_retorna_estado_operacional_util() -> None:
    """Falha se o dashboard vazio omitir zeros ou integrações inativas."""
    empresa = EmpresaFactory()

    metricas = obter_metricas_do_dia(
        empresa=empresa,
        agora=datetime(2026, 8, 29, 15, tzinfo=UTC),
    )

    assert metricas == MetricasAtendimento(
        conversas_abertas=0,
        conversas_ia=0,
        conversas_humano=0,
        mensagens_recebidas_hoje=0,
        mensagens_enviadas_hoje=0,
        mensagens_com_falha=0,
        estado_openai="INATIVA",
        estado_evolution="DESCONECTADO",
    )
    with pytest.raises(FrozenInstanceError):
        metricas.conversas_abertas = 1


@pytest.mark.django_db
def test_metricas_respeitam_fuso_direcao_estado_e_empresa() -> None:
    """Falha se limites do dia, estados ou tenant alterarem as contagens."""
    empresa = EmpresaFactory(fuso_horario="America/Sao_Paulo")
    aberta_ia = ConversaFactory(
        empresa=empresa,
        modo=Conversa.Modo.IA,
        contato__empresa=empresa,
    )
    ConversaFactory(
        empresa=empresa,
        modo=Conversa.Modo.HUMANO,
        contato__empresa=empresa,
    )
    ConversaFactory(
        empresa=empresa,
        estado=Conversa.Estado.FINALIZADA,
        contato__empresa=empresa,
    )
    agora = datetime(2026, 8, 29, 3, 30, tzinfo=UTC)
    dentro_do_dia = agora - timedelta(minutes=15)
    dia_anterior_local = agora - timedelta(hours=1)

    recebida = MensagemFactory(
        empresa=empresa,
        conversa=aberta_ia,
        direcao=Mensagem.Direcao.ENTRADA,
    )
    recebida_antiga = MensagemFactory(
        empresa=empresa,
        conversa=aberta_ia,
        direcao=Mensagem.Direcao.ENTRADA,
    )
    enviada = MensagemFactory(
        empresa=empresa,
        conversa=aberta_ia,
        direcao=Mensagem.Direcao.SAIDA,
        status=Mensagem.Status.ENTREGUE,
        enviado_em=dentro_do_dia,
    )
    falha_antiga = MensagemFactory(
        empresa=empresa,
        conversa=aberta_ia,
        direcao=Mensagem.Direcao.SAIDA,
        status=Mensagem.Status.FALHA,
    )
    Mensagem.objects.filter(pk=recebida.pk).update(criado_em=dentro_do_dia)
    Mensagem.objects.filter(pk=recebida_antiga.pk).update(criado_em=dia_anterior_local)
    Mensagem.objects.filter(pk=enviada.pk).update(criado_em=dentro_do_dia)
    Mensagem.objects.filter(pk=falha_antiga.pk).update(criado_em=dia_anterior_local)
    outra = ConversaFactory()
    MensagemFactory(
        empresa=outra.empresa,
        conversa=outra,
        status=Mensagem.Status.FALHA,
    )
    ConfiguracaoIA.objects.create(
        empresa=empresa,
        respostas_automaticas_ativas=True,
        chave_api_criptografada="segredo-cifrado",
    )
    ConfiguracaoWhatsApp.objects.create(
        empresa=empresa,
        url_base="https://evolution.example.com",
        nome_instancia="empresa",
        ativo=True,
        estado=EstadoConexao.CONECTADO.value,
    )

    metricas = obter_metricas_do_dia(empresa=empresa, agora=agora)

    assert metricas == MetricasAtendimento(
        conversas_abertas=2,
        conversas_ia=1,
        conversas_humano=1,
        mensagens_recebidas_hoje=1,
        mensagens_enviadas_hoje=1,
        mensagens_com_falha=1,
        estado_openai="ATIVA",
        estado_evolution="CONECTADO",
    )


@pytest.mark.django_db
def test_cache_nao_atravessa_meia_noite_local_da_empresa() -> None:
    """Falha se o retrato do dia anterior ocultar dados apos a virada local."""
    empresa = EmpresaFactory(fuso_horario="America/Sao_Paulo")
    antes_da_virada = datetime(2026, 8, 29, 2, 59, tzinfo=UTC)
    depois_da_virada = datetime(2026, 8, 29, 3, 1, tzinfo=UTC)

    anteriores = obter_metricas_do_dia(
        empresa=empresa,
        agora=antes_da_virada,
    )
    conversa = ConversaFactory(
        empresa=empresa,
        contato__empresa=empresa,
    )
    mensagem = MensagemFactory(
        empresa=empresa,
        conversa=conversa,
        direcao=Mensagem.Direcao.ENTRADA,
    )
    Mensagem.objects.filter(pk=mensagem.pk).update(criado_em=depois_da_virada)

    atuais = obter_metricas_do_dia(empresa=empresa, agora=depois_da_virada)

    assert anteriores.mensagens_recebidas_hoje == 0
    assert atuais.mensagens_recebidas_hoje == 1


@pytest.mark.django_db
def test_metricas_usam_quatro_queries_e_cache_por_empresa(
    django_assert_num_queries,
) -> None:
    """Falha se o dashboard repetir consultas ou misturar chaves de cache."""
    empresa = EmpresaFactory()
    outra_empresa = EmpresaFactory()
    agora = datetime(2026, 8, 29, 15, tzinfo=UTC)

    with django_assert_num_queries(4):
        primeiras = obter_metricas_do_dia(empresa=empresa, agora=agora)

    ConversaFactory(empresa=empresa, contato__empresa=empresa)
    with django_assert_num_queries(0):
        repetidas = obter_metricas_do_dia(empresa=empresa, agora=agora)

    with django_assert_num_queries(4):
        outra = obter_metricas_do_dia(empresa=outra_empresa, agora=agora)

    assert repetidas == primeiras
    assert outra.conversas_abertas == 0
