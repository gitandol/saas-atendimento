"""Testes do envio seguro e do reenvio manual de mensagens."""

from unittest.mock import patch

import pytest

from apps.atendimento.models import Mensagem
from apps.atendimento.tests.factories import MensagemFactory, UsuarioFactory
from apps.auditoria.models import EventoAuditoria
from apps.empresas.models import MembroEmpresa


class ProviderFalso:
    """Registra o contrato de envio exercido pelo service real."""

    def __init__(self, identificador: str = "wamid-saida-1") -> None:
        """Configura o identificador externo devolvido pelo fornecedor."""
        self.identificador = identificador
        self.chamadas: list[tuple[str, str, str]] = []

    def enviar_texto(self, numero: str, texto: str, chave: str) -> str:
        """Simula somente a fronteira externa e preserva os argumentos."""
        self.chamadas.append((numero, texto, chave))
        return self.identificador


@pytest.mark.django_db
def test_envia_pendente_com_numero_texto_e_uuid_sem_repetir() -> None:
    """Falha se uma task repetida reenviar ou perder o contrato externo."""
    from apps.whatsapp.services.enviar_mensagem import executar_envio

    mensagem = MensagemFactory(
        direcao=Mensagem.Direcao.SAIDA,
        autor=Mensagem.Autor.IA,
        status=Mensagem.Status.PENDENTE,
        texto="Resposta segura",
    )
    provider = ProviderFalso()
    with patch(
        "apps.whatsapp.services.enviar_mensagem.obter_provider",
        return_value=provider,
    ):
        assert executar_envio(mensagem_id=mensagem.id, correlacao="corr-envio") is True
        assert (
            executar_envio(mensagem_id=mensagem.id, correlacao="corr-repetida") is False
        )

    mensagem.refresh_from_db()
    assert provider.chamadas == [
        (
            mensagem.conversa.contato.numero_normalizado,
            "Resposta segura",
            str(mensagem.id),
        )
    ]
    assert mensagem.status == Mensagem.Status.ENVIADA
    assert mensagem.identificador_externo == "wamid-saida-1"
    assert mensagem.enviado_em is not None


@pytest.mark.django_db
def test_reenvio_manual_reabre_falha_audita_e_enfileira_mesma_mensagem() -> None:
    """Falha se o reenvio criar entidade nova ou omitir o historico auditavel."""
    from apps.whatsapp.services.enviar_mensagem import reenviar_mensagem

    mensagem = MensagemFactory(
        direcao=Mensagem.Direcao.SAIDA,
        autor=Mensagem.Autor.ATENDENTE,
        status=Mensagem.Status.FALHA,
        erro_sanitizado="whatsapp_indisponivel",
    )
    ator = UsuarioFactory()
    MembroEmpresa.objects.create(
        empresa=mensagem.empresa,
        usuario=ator,
        papel=MembroEmpresa.Papel.ATENDENTE,
    )
    quantidade = Mensagem.objects.count()

    with patch("apps.whatsapp.services.enviar_mensagem.solicitar_envio") as solicitar:
        resultado = reenviar_mensagem(
            empresa=mensagem.empresa,
            ator=ator,
            mensagem_id=mensagem.id,
            correlacao="corr-manual",
        )

    mensagem.refresh_from_db()
    assert resultado.id == mensagem.id
    assert Mensagem.objects.count() == quantidade
    assert mensagem.status == Mensagem.Status.PENDENTE
    assert mensagem.erro_sanitizado == ""
    solicitar.assert_called_once_with(mensagem.id, "corr-manual")
    evento = EventoAuditoria.objects.filter(objeto_id=str(mensagem.id)).first()
    assert evento is not None
    assert evento.ator == ator
    assert evento.origem == "api_reenvio_whatsapp"
    assert mensagem.texto not in str(evento.depois)
    assert evento.depois["texto_tamanho"] == len(mensagem.texto)
