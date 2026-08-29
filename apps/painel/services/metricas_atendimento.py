"""Calcula as metricas operacionais atuais de uma empresa."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.core.cache import cache
from django.db.models import Count, Q

from apps.atendimento.models import Conversa, Mensagem
from apps.empresas.models import Empresa
from apps.ia.models import ConfiguracaoIA
from apps.whatsapp.integrations.protocolos import EstadoConexao
from apps.whatsapp.models import ConfiguracaoWhatsApp

TEMPO_CACHE_METRICAS_SEGUNDOS = 30


@dataclass(frozen=True, slots=True)
class MetricasAtendimento:
    """Representa um retrato imutavel do atendimento da empresa."""

    conversas_abertas: int
    conversas_ia: int
    conversas_humano: int
    mensagens_recebidas_hoje: int
    mensagens_enviadas_hoje: int
    mensagens_com_falha: int
    estado_openai: str
    estado_evolution: str


def _limites_do_dia(
    empresa: Empresa,
    agora: datetime,
) -> tuple[date, datetime, datetime]:
    """Converte o dia civil da empresa em um intervalo temporal consciente."""
    fuso = ZoneInfo(empresa.fuso_horario)
    data_local = agora.astimezone(fuso).date()
    inicio = datetime.combine(data_local, time.min, tzinfo=fuso)
    fim = datetime.combine(data_local + timedelta(days=1), time.min, tzinfo=fuso)
    return data_local, inicio.astimezone(UTC), fim.astimezone(UTC)


def _chave_cache(empresa: Empresa, data_local: date) -> str:
    """Isola o retrato pelo tenant e impede cache entre dias civis."""
    return f"painel:metricas:{empresa.pk}:{data_local.isoformat()}"


def obter_metricas_do_dia(
    empresa: Empresa,
    agora: datetime,
) -> MetricasAtendimento:
    """Retorna metricas isoladas pelo tenant e pelo dia civil da empresa."""
    data_local, inicio, fim = _limites_do_dia(empresa, agora)
    chave = _chave_cache(empresa, data_local)
    armazenadas = cache.get(chave)
    if armazenadas is not None:
        return armazenadas

    conversas = Conversa.objects.filter(empresa=empresa).aggregate(
        abertas=Count("pk", filter=Q(estado=Conversa.Estado.ABERTA)),
        ia=Count(
            "pk",
            filter=Q(
                estado=Conversa.Estado.ABERTA,
                modo=Conversa.Modo.IA,
            ),
        ),
        humano=Count(
            "pk",
            filter=Q(
                estado=Conversa.Estado.ABERTA,
                modo=Conversa.Modo.HUMANO,
            ),
        ),
    )
    mensagens = Mensagem.objects.filter(empresa=empresa).aggregate(
        recebidas=Count(
            "pk",
            filter=Q(
                direcao=Mensagem.Direcao.ENTRADA,
                criado_em__gte=inicio,
                criado_em__lt=fim,
            ),
        ),
        enviadas=Count(
            "pk",
            filter=Q(
                direcao=Mensagem.Direcao.SAIDA,
                enviado_em__gte=inicio,
                enviado_em__lt=fim,
            ),
        ),
        falhas=Count("pk", filter=Q(status=Mensagem.Status.FALHA)),
    )
    configuracao_ia = (
        ConfiguracaoIA.objects.filter(empresa=empresa)
        .values("respostas_automaticas_ativas", "chave_api_criptografada")
        .first()
    )
    estado_evolution = (
        ConfiguracaoWhatsApp.objects.filter(empresa=empresa)
        .values_list("estado", flat=True)
        .first()
        or EstadoConexao.DESCONECTADO.value
    )
    estado_openai = (
        "ATIVA"
        if configuracao_ia
        and configuracao_ia["respostas_automaticas_ativas"]
        and configuracao_ia["chave_api_criptografada"]
        else "INATIVA"
    )
    metricas = MetricasAtendimento(
        conversas_abertas=conversas["abertas"],
        conversas_ia=conversas["ia"],
        conversas_humano=conversas["humano"],
        mensagens_recebidas_hoje=mensagens["recebidas"],
        mensagens_enviadas_hoje=mensagens["enviadas"],
        mensagens_com_falha=mensagens["falhas"],
        estado_openai=estado_openai,
        estado_evolution=estado_evolution,
    )
    cache.set(chave, metricas, TEMPO_CACHE_METRICAS_SEGUNDOS)
    return metricas
