"""Orquestra respostas automaticas com elegibilidade e idempotencia."""

import logging
from uuid import UUID

from django.db import transaction

from apps.atendimento.models import Conversa, Mensagem
from apps.atendimento.services.mensagens import registrar_mensagem
from apps.empresas.models import Empresa
from apps.ia.integrations.protocolos import (
    CredencialIAInvalida,
    IAIndisponivel,
    LimiteIAExcedido,
)
from apps.ia.models import ConfiguracaoIA
from apps.ia.services.montar_prompt import montar_prompt
from apps.ia.services.obter_provider import obter_provider

logger = logging.getLogger(__name__)
LIMITE_RESPOSTA = 4096
EXCECOES_PROVIDER = (CredencialIAInvalida, IAIndisponivel, LimiteIAExcedido)


class RespostaAutomaticaNaoPermitida(Exception):
    """Indica que o estado atual nao autoriza uma resposta da IA."""


def _exigir_elegibilidade(
    *, conversa: Conversa, configuracao: ConfiguracaoIA | None
) -> ConfiguracaoIA:
    """Valida as condicoes que precisam permanecer verdadeiras ate a persistencia."""
    if conversa.modo != Conversa.Modo.IA:
        raise RespostaAutomaticaNaoPermitida("A conversa esta em modo humano.")
    if conversa.estado != Conversa.Estado.ABERTA:
        raise RespostaAutomaticaNaoPermitida("A conversa esta finalizada.")
    if (
        configuracao is None
        or not configuracao.respostas_automaticas_ativas
        or not configuracao.modelo.strip()
        or not configuracao.chave_api_criptografada
    ):
        raise RespostaAutomaticaNaoPermitida("A configuracao de IA esta inativa.")
    return configuracao


def _identificador_saida(mensagem_entrada_id: UUID) -> str:
    """Deriva a chave idempotente da resposta automatica."""
    return f"ia:{mensagem_entrada_id}"


def _identificador_falha(mensagem_entrada_id: UUID) -> str:
    """Deriva a chave idempotente do estado operacional de falha."""
    return f"ia-falha:{mensagem_entrada_id}"


def _carregar_para_geracao(
    *, conversa_id: UUID, mensagem_entrada_id: UUID
) -> tuple[Conversa, Mensagem, ConfiguracaoIA, Mensagem | None]:
    """Bloqueia o tenant e valida a entrada antes da chamada externa."""
    conversa_base = (
        Conversa.objects.select_related("empresa").filter(pk=conversa_id).first()
    )
    if conversa_base is None:
        raise RespostaAutomaticaNaoPermitida("A conversa nao existe.")
    with transaction.atomic():
        Empresa.objects.select_for_update().get(pk=conversa_base.empresa_id)
        conversa = (
            Conversa.objects.select_for_update()
            .select_related("empresa")
            .get(pk=conversa_id, empresa_id=conversa_base.empresa_id)
        )
        configuracao = _exigir_elegibilidade(
            conversa=conversa,
            configuracao=ConfiguracaoIA.objects.select_for_update()
            .filter(empresa_id=conversa.empresa_id)
            .first(),
        )
        entrada = (
            Mensagem.objects.select_for_update()
            .filter(
                pk=mensagem_entrada_id,
                conversa=conversa,
                empresa_id=conversa.empresa_id,
                direcao=Mensagem.Direcao.ENTRADA,
                autor=Mensagem.Autor.CLIENTE,
                status=Mensagem.Status.RECEBIDA,
            )
            .first()
        )
        if entrada is None:
            raise RespostaAutomaticaNaoPermitida("A mensagem de entrada e invalida.")
        existente = Mensagem.objects.filter(
            empresa_id=conversa.empresa_id,
            identificador_externo=_identificador_saida(entrada.id),
        ).first()
        return conversa, entrada, configuracao, existente


def _persistir_mensagem(
    *,
    conversa_id: UUID,
    mensagem_entrada_id: UUID,
    texto: str,
    autor: str,
    status: str,
    erro_sanitizado: str,
    correlacao: str,
) -> Mensagem:
    """Revalida o modo sob lock e registra uma saida auditavel uma unica vez."""
    conversa_base = Conversa.objects.only("empresa_id").get(pk=conversa_id)
    with transaction.atomic():
        empresa = Empresa.objects.select_for_update().get(pk=conversa_base.empresa_id)
        conversa = Conversa.objects.select_for_update().get(
            pk=conversa_id, empresa=empresa
        )
        configuracao = (
            ConfiguracaoIA.objects.select_for_update().filter(empresa=empresa).first()
        )
        _exigir_elegibilidade(conversa=conversa, configuracao=configuracao)
        entrada = (
            Mensagem.objects.select_for_update()
            .filter(
                pk=mensagem_entrada_id,
                conversa=conversa,
                empresa=empresa,
                direcao=Mensagem.Direcao.ENTRADA,
                autor=Mensagem.Autor.CLIENTE,
            )
            .first()
        )
        if entrada is None:
            raise RespostaAutomaticaNaoPermitida("A mensagem de entrada e invalida.")
        identificador = (
            _identificador_saida(entrada.id)
            if autor == Mensagem.Autor.IA
            else _identificador_falha(entrada.id)
        )
        existente = Mensagem.objects.filter(
            empresa=empresa,
            identificador_externo=identificador,
        ).first()
        if existente is not None:
            return existente
        registrada = registrar_mensagem(
            empresa=empresa,
            conversa_id=conversa.id,
            direcao=Mensagem.Direcao.SAIDA,
            autor=autor,
            texto=texto,
            identificador_externo=identificador,
            status=status,
            erro_sanitizado=erro_sanitizado,
            ator=None,
            origem="task_ia",
            correlacao=correlacao,
        )
        return Mensagem.objects.get(pk=registrada.id)


def _solicitar_envio(mensagem_id: str, correlacao: str) -> None:
    """Aciona a interface de envio sem antecipar a implementacao da tarefa 012."""
    try:
        from apps.whatsapp.services.enviar_mensagem import solicitar_envio
    except ModuleNotFoundError:
        logger.warning(
            "envio_whatsapp_ainda_indisponivel",
            extra={"mensagem_id": mensagem_id, "correlacao": correlacao},
        )
        return
    solicitar_envio(mensagem_id=mensagem_id, correlacao=correlacao)


def _registrar_falha(
    *,
    conversa_id: UUID,
    mensagem_entrada_id: UUID,
    configuracao: ConfiguracaoIA,
    erro: Exception,
    correlacao: str,
) -> Mensagem:
    """Converte uma falha externa em estado interno recuperavel e sanitizado."""
    codigos = {
        CredencialIAInvalida: "credencial_ia_invalida",
        LimiteIAExcedido: "limite_ia_excedido",
        IAIndisponivel: "ia_indisponivel",
    }
    codigo = codigos.get(type(erro), "resposta_ia_invalida")
    mensagem = (
        configuracao.mensagem_falha.strip()
        or "Nao foi possivel gerar a resposta automatica."
    )
    logger.warning(
        "resposta_ia_falhou",
        extra={
            "conversa_id": str(conversa_id),
            "mensagem_entrada_id": str(mensagem_entrada_id),
            "correlacao": correlacao,
            "erro": codigo,
        },
    )
    return _persistir_mensagem(
        conversa_id=conversa_id,
        mensagem_entrada_id=mensagem_entrada_id,
        texto=mensagem,
        autor=Mensagem.Autor.SISTEMA,
        status=Mensagem.Status.FALHA,
        erro_sanitizado=codigo,
        correlacao=correlacao,
    )


def gerar_resposta_atendimento(
    *, conversa_id: UUID, mensagem_entrada_id: UUID, correlacao: str
) -> Mensagem:
    """Gera e persiste uma resposta contextual somente quando a IA pode atuar."""
    conversa, entrada, configuracao, existente = _carregar_para_geracao(
        conversa_id=conversa_id,
        mensagem_entrada_id=mensagem_entrada_id,
    )
    if existente is not None:
        return existente
    prompt = montar_prompt(
        conversa=conversa,
        configuracao=configuracao,
        mensagem_atual=entrada,
    )
    try:
        provider = obter_provider(conversa.empresa)
        resposta = provider.gerar_resposta(prompt, configuracao.modelo)
        texto = resposta.texto.strip()
        if not texto or len(texto) > LIMITE_RESPOSTA:
            raise IAIndisponivel("O provider retornou conteudo fora do limite.")
    except EXCECOES_PROVIDER as erro:
        return _registrar_falha(
            conversa_id=conversa.id,
            mensagem_entrada_id=entrada.id,
            configuracao=configuracao,
            erro=erro,
            correlacao=correlacao,
        )
    mensagem = _persistir_mensagem(
        conversa_id=conversa.id,
        mensagem_entrada_id=entrada.id,
        texto=texto,
        autor=Mensagem.Autor.IA,
        status=Mensagem.Status.PENDENTE,
        erro_sanitizado="",
        correlacao=correlacao,
    )
    logger.info(
        "resposta_ia_gerada",
        extra={
            "empresa_id": str(conversa.empresa_id),
            "conversa_id": str(conversa.id),
            "mensagem_id": str(mensagem.id),
            "correlacao": correlacao,
            "modelo": resposta.modelo,
            "tokens_entrada": resposta.tokens_entrada,
            "tokens_saida": resposta.tokens_saida,
        },
    )
    transaction.on_commit(lambda: _solicitar_envio(str(mensagem.id), correlacao))
    return mensagem
