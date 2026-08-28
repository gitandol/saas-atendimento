"""Testes dos services mutaveis usados pela caixa de entrada."""

from unittest.mock import patch

import pytest
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError

from apps.atendimento.models import Conversa, Mensagem
from apps.atendimento.tests.factories import (
    ConversaFactory,
    EmpresaFactory,
    UsuarioFactory,
)
from apps.empresas.models import MembroEmpresa


def _membro(conversa: Conversa):
    """Cria um atendente ativo da empresa da conversa."""
    usuario = UsuarioFactory()
    MembroEmpresa.objects.create(
        empresa=conversa.empresa,
        usuario=usuario,
        papel=MembroEmpresa.Papel.ATENDENTE,
    )
    return usuario


@pytest.mark.django_db
def test_marcar_como_lida_zera_contador_e_audita() -> None:
    """Falha se abrir uma conversa autorizada nao persistir a leitura."""
    from apps.atendimento.services.conversas import marcar_como_lida
    from apps.auditoria.models import EventoAuditoria

    conversa = ConversaFactory(contagem_nao_lida=4)
    usuario = _membro(conversa)

    resultado = marcar_como_lida(
        empresa=conversa.empresa,
        conversa_id=conversa.id,
        ator=usuario,
        correlacao="leitura-1",
    )

    conversa.refresh_from_db()
    assert resultado.contagem_nao_lida == 0
    assert conversa.contagem_nao_lida == 0
    assert EventoAuditoria.objects.filter(correlacao="leitura-1").exists()


@pytest.mark.django_db
def test_marcar_como_lida_recusa_outra_empresa_e_nao_altera_contador() -> None:
    """Falha se o ID permitir leitura cruzada entre empresas."""
    from apps.atendimento.services.conversas import marcar_como_lida

    conversa = ConversaFactory(contagem_nao_lida=2)
    usuario = UsuarioFactory()
    outra_empresa = EmpresaFactory()
    MembroEmpresa.objects.create(
        empresa=outra_empresa,
        usuario=usuario,
        papel=MembroEmpresa.Papel.ATENDENTE,
    )

    with pytest.raises(ObjectDoesNotExist):
        marcar_como_lida(
            empresa=outra_empresa,
            conversa_id=conversa.id,
            ator=usuario,
            correlacao="leitura-cruzada",
        )

    conversa.refresh_from_db()
    assert conversa.contagem_nao_lida == 2


@pytest.mark.django_db
def test_enviar_resposta_manual_cria_pendente_e_solicita_pipeline() -> None:
    """Falha se o envio manual contornar a mensagem pendente ou a fila existente."""
    from apps.atendimento.services.respostas_manuais import enviar_resposta_manual

    conversa = ConversaFactory()
    usuario = _membro(conversa)
    conversa.modo = Conversa.Modo.HUMANO
    conversa.atendente = usuario
    conversa.save(update_fields=("modo", "atendente"))

    with patch("apps.whatsapp.services.enviar_mensagem.solicitar_envio") as solicitar:
        resultado = enviar_resposta_manual(
            empresa=conversa.empresa,
            conversa_id=conversa.id,
            texto="  Resposta do atendente  ",
            ator=usuario,
            correlacao="manual-1",
        )

    mensagem = Mensagem.objects.get(pk=resultado.id)
    assert mensagem.texto == "Resposta do atendente"
    assert mensagem.direcao == Mensagem.Direcao.SAIDA
    assert mensagem.autor == Mensagem.Autor.ATENDENTE
    assert mensagem.status == Mensagem.Status.PENDENTE
    solicitar.assert_called_once_with(mensagem.id, "manual-1")


@pytest.mark.django_db
@pytest.mark.parametrize("texto", ["", "   ", "x" * 4097])
def test_enviar_resposta_manual_recusa_texto_invalido(texto: str) -> None:
    """Falha se texto vazio ou acima do limite chegar a persistencia."""
    from apps.atendimento.services.respostas_manuais import enviar_resposta_manual

    conversa = ConversaFactory()
    usuario = _membro(conversa)
    conversa.modo = Conversa.Modo.HUMANO
    conversa.atendente = usuario
    conversa.save(update_fields=("modo", "atendente"))

    with pytest.raises(ValidationError):
        enviar_resposta_manual(
            empresa=conversa.empresa,
            conversa_id=conversa.id,
            texto=texto,
            ator=usuario,
            correlacao="manual-invalida",
        )

    assert not Mensagem.objects.filter(conversa=conversa).exists()


@pytest.mark.django_db
def test_enviar_resposta_manual_recusa_finalizada_e_nao_membro() -> None:
    """Falha se conversa finalizada ou ator externo puder enviar."""
    from apps.atendimento.services.respostas_manuais import enviar_resposta_manual

    finalizada = ConversaFactory(estado=Conversa.Estado.FINALIZADA)
    membro = _membro(finalizada)
    with pytest.raises(ValidationError):
        enviar_resposta_manual(
            empresa=finalizada.empresa,
            conversa_id=finalizada.id,
            texto="Nao enviar",
            ator=membro,
            correlacao="manual-finalizada",
        )

    aberta = ConversaFactory()
    with pytest.raises(PermissionDenied):
        enviar_resposta_manual(
            empresa=aberta.empresa,
            conversa_id=aberta.id,
            texto="Nao autorizado",
            ator=UsuarioFactory(),
            correlacao="manual-sem-membro",
        )


@pytest.mark.django_db
def test_enviar_resposta_manual_exige_modo_humano_e_responsavel_atual() -> None:
    """Falha se IA ou outro atendente puder publicar uma resposta manual."""
    from apps.atendimento.services.respostas_manuais import enviar_resposta_manual

    conversa = ConversaFactory()
    responsavel = _membro(conversa)
    outro = _membro(conversa)
    with pytest.raises(PermissionDenied):
        enviar_resposta_manual(
            empresa=conversa.empresa,
            conversa_id=conversa.id,
            texto="Nao enviar em modo IA",
            ator=responsavel,
            correlacao="manual-ia",
        )
    conversa.modo = Conversa.Modo.HUMANO
    conversa.atendente = responsavel
    conversa.save(update_fields=("modo", "atendente"))
    with pytest.raises(PermissionDenied):
        enviar_resposta_manual(
            empresa=conversa.empresa,
            conversa_id=conversa.id,
            texto="Nao sou responsavel",
            ator=outro,
            correlacao="manual-outro",
        )
