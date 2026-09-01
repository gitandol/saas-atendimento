"""Testes da normalizacao segura de eventos Evolution."""

from datetime import UTC, datetime


def test_normaliza_mensagem_de_texto_sem_confiar_em_empresa_do_payload() -> None:
    """Extrai apenas o contrato textual confiavel do evento recebido."""
    from apps.whatsapp.services.normalizar_evento import normalizar_evento

    evento = normalizar_evento(
        {
            "event": "messages.upsert",
            "empresa": "empresa-forjada",
            "data": {
                "key": {
                    "id": "evolution-msg-1",
                    "remoteJid": "5568999990000@s.whatsapp.net",
                    "fromMe": False,
                },
                "pushName": "  Ana  ",
                "message": {"conversation": "Preciso de ajuda"},
                "messageTimestamp": 1_725_192_000,
            },
        }
    )

    assert evento is not None
    assert evento.identificador_externo == "evolution-msg-1"
    assert evento.numero_remetente == "5568999990000"
    assert evento.nome_remetente == "Ana"
    assert evento.texto == "Preciso de ajuda"
    assert evento.enviado_pela_instancia is False
    assert evento.ocorrido_em == datetime(2024, 9, 1, 12, tzinfo=UTC)
    assert not hasattr(evento, "empresa")


def test_normaliza_texto_estendido_e_timestamp_em_milissegundos() -> None:
    """Aceita a variante textual documentada sem perder o instante real."""
    from apps.whatsapp.services.normalizar_evento import normalizar_evento

    evento = normalizar_evento(
        {
            "event": "MESSAGES_UPSERT",
            "data": {
                "key": {
                    "id": "evolution-msg-2",
                    "remoteJid": "5568999990001@s.whatsapp.net",
                    "fromMe": True,
                },
                "message": {"extendedTextMessage": {"text": "Resposta humana"}},
                "messageTimestamp": 1_725_192_000_000,
            },
        }
    )

    assert evento is not None
    assert evento.texto == "Resposta humana"
    assert evento.enviado_pela_instancia is True
    assert evento.ocorrido_em == datetime(2024, 9, 1, 12, tzinfo=UTC)


def test_ignora_evento_desconhecido_e_mensagem_sem_texto() -> None:
    """Mantem eventos fora do MVP longe do dominio textual."""
    from apps.whatsapp.services.normalizar_evento import normalizar_evento

    desconhecido = normalizar_evento({"event": "connection.update", "data": {}})
    midia = normalizar_evento(
        {
            "event": "messages.upsert",
            "data": {
                "key": {
                    "id": "midia-1",
                    "remoteJid": "5568999990002@s.whatsapp.net",
                    "fromMe": False,
                },
                "message": {"imageMessage": {"caption": "Foto"}},
                "messageTimestamp": 1_725_192_000,
            },
        }
    )

    assert desconhecido is None
    assert midia is None


def test_ignora_mensagem_textual_de_grupo() -> None:
    """Impede que um JID de grupo seja tratado como contato direto."""
    from apps.whatsapp.services.normalizar_evento import normalizar_evento

    evento = normalizar_evento(
        {
            "event": "messages.upsert",
            "data": {
                "key": {
                    "id": "grupo-1",
                    "remoteJid": "120363123456789012@g.us",
                    "fromMe": False,
                },
                "pushName": "Participante",
                "message": {"conversation": "Mensagem enviada no grupo"},
                "messageTimestamp": 1_725_192_000,
            },
        }
    )

    assert evento is None


def test_recusa_mensagem_textual_sem_identificador_ou_remetente() -> None:
    """Nao permite que dados incompletos alcancem a persistencia idempotente."""
    import pytest

    from apps.whatsapp.services.normalizar_evento import (
        EventoEvolutionInvalido,
        normalizar_evento,
    )

    with pytest.raises(EventoEvolutionInvalido):
        normalizar_evento(
            {
                "event": "messages.upsert",
                "data": {
                    "key": {"id": "", "remoteJid": "", "fromMe": False},
                    "message": {"conversation": "Oi"},
                    "messageTimestamp": 1_725_192_000,
                },
            }
        )
