"""Converte payloads Evolution no contrato textual confiavel do dominio."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


class EventoEvolutionInvalido(Exception):
    """Indica que uma mensagem textual nao possui campos obrigatorios validos."""


@dataclass(frozen=True, slots=True)
class EventoMensagemRecebida:
    """Representa somente os dados confiaveis usados pelo dominio."""

    identificador_externo: str
    numero_remetente: str
    nome_remetente: str
    texto: str
    enviado_pela_instancia: bool
    ocorrido_em: datetime


@dataclass(frozen=True, slots=True)
class EventoStatusEntrega:
    """Representa um recibo externo sem transportar conteudo da mensagem."""

    identificador_externo: str
    status: str
    ocorrido_em: datetime | None


def _dicionario(valor: Any) -> dict[str, Any]:
    """Retorna um dicionario ou uma estrutura vazia segura."""
    return valor if isinstance(valor, dict) else {}


def _texto_da_mensagem(mensagem: dict[str, Any]) -> str:
    """Extrai somente as duas variantes textuais aceitas no MVP."""
    conversa = mensagem.get("conversation")
    if isinstance(conversa, str):
        return conversa.strip()
    estendida = _dicionario(mensagem.get("extendedTextMessage")).get("text")
    return estendida.strip() if isinstance(estendida, str) else ""


def _instante(valor: Any) -> datetime:
    """Normaliza segundos ou milissegundos Unix para UTC."""
    try:
        timestamp = float(valor)
        if timestamp >= 1_000_000_000_000:
            timestamp /= 1000
        return datetime.fromtimestamp(timestamp, tz=UTC)
    except (OverflowError, TypeError, ValueError) as erro:
        raise EventoEvolutionInvalido("Timestamp da mensagem invalido.") from erro


def normalizar_evento(
    payload: dict[str, Any],
) -> EventoMensagemRecebida | None:
    """Normaliza texto conhecido e ignora eventos ou midias fora do MVP."""
    tipo_evento = payload.get("event")
    if (
        not isinstance(tipo_evento, str)
        or tipo_evento.lower().replace("_", ".") != "messages.upsert"
    ):
        return None
    dados = _dicionario(payload.get("data"))
    mensagem = _dicionario(dados.get("message"))
    texto = _texto_da_mensagem(mensagem)
    if not texto:
        return None
    chave = _dicionario(dados.get("key"))
    identificador = chave.get("id")
    jid = chave.get("remoteJid")
    if not isinstance(identificador, str) or not identificador.strip():
        raise EventoEvolutionInvalido("Identificador externo ausente.")
    if not isinstance(jid, str) or not jid.strip():
        raise EventoEvolutionInvalido("Remetente ausente.")
    identificador = identificador.strip()
    numero = jid.split("@", maxsplit=1)[0].split(":", maxsplit=1)[0].strip()
    nome = dados.get("pushName", "")
    nome = nome.strip() if isinstance(nome, str) else ""
    if (
        not numero
        or len(numero) > 30
        or len(nome) > 160
        or len(texto) > 4096
        or len(identificador) > 160
    ):
        raise EventoEvolutionInvalido("Mensagem textual excede o contrato permitido.")
    return EventoMensagemRecebida(
        identificador_externo=identificador,
        numero_remetente=numero,
        nome_remetente=nome,
        texto=texto,
        enviado_pela_instancia=chave.get("fromMe") is True,
        ocorrido_em=_instante(dados.get("messageTimestamp")),
    )


def normalizar_evento_entrega(
    payload: dict[str, Any],
) -> EventoStatusEntrega | None:
    """Normaliza somente atualizacoes conhecidas de envio, entrega ou falha."""
    tipo_evento = payload.get("event")
    if (
        not isinstance(tipo_evento, str)
        or tipo_evento.lower().replace("_", ".") != "messages.update"
    ):
        return None
    dados_brutos = payload.get("data")
    if isinstance(dados_brutos, list):
        dados = _dicionario(dados_brutos[0]) if dados_brutos else {}
    else:
        dados = _dicionario(dados_brutos)
    chave = _dicionario(dados.get("key"))
    identificador = chave.get("id")
    if not isinstance(identificador, str) or not identificador.strip():
        raise EventoEvolutionInvalido("Identificador do recibo ausente.")
    status_externo = dados.get("status")
    mapa_status = {
        "PENDING": "PENDENTE",
        "SERVER_ACK": "ENVIADA",
        "SENT": "ENVIADA",
        "DELIVERY_ACK": "ENTREGUE",
        "DELIVERED": "ENTREGUE",
        "READ": "ENTREGUE",
        "READ_ACK": "ENTREGUE",
        "ERROR": "FALHA",
        "FAILED": "FALHA",
    }
    status = mapa_status.get(str(status_externo).upper())
    if status is None:
        return None
    timestamp = dados.get("messageTimestamp") or dados.get("timestamp")
    ocorrido_em = _instante(timestamp) if timestamp is not None else None
    return EventoStatusEntrega(
        identificador_externo=identificador.strip(),
        status=status,
        ocorrido_em=ocorrido_em,
    )
