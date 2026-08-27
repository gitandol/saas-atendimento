"""Testes das consultas imutaveis e isoladas do atendimento."""

from dataclasses import FrozenInstanceError
from uuid import UUID

import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from apps.atendimento.models import Contato, Conversa, Mensagem
from apps.atendimento.tests.factories import (
    ContatoFactory,
    ConversaFactory,
    EmpresaFactory,
    MensagemFactory,
)


@pytest.mark.django_db
def test_listar_conversas_isola_exclui_contato_removido_e_retorna_dto() -> None:
    """Publica apenas conversas visiveis do tenant em DTOs congelados."""
    from apps.atendimento.dto import ConversaDTO
    from apps.atendimento.services.consultas.listar_conversas import (
        listar_conversas,
    )

    empresa = EmpresaFactory()
    visivel = ConversaFactory(empresa=empresa, contato=ContatoFactory(empresa=empresa))
    excluido = ConversaFactory(empresa=empresa, contato=ContatoFactory(empresa=empresa))
    Contato.objects.filter(pk=excluido.contato_id).update(excluido_em=timezone.now())
    ConversaFactory()

    resultado = listar_conversas(empresa=empresa)

    assert isinstance(resultado, list)
    assert [item.id for item in resultado] == [visivel.id]
    assert isinstance(resultado[0], ConversaDTO)
    with pytest.raises(FrozenInstanceError):
        resultado[0].estado = Conversa.Estado.FINALIZADA


@pytest.mark.django_db
def test_listar_conversas_ordena_estavelmente_por_data_e_uuid() -> None:
    """Desempata conversas com a mesma data pelo UUID em ordem decrescente."""
    from apps.atendimento.services.consultas.listar_conversas import (
        listar_conversas,
    )

    empresa = EmpresaFactory()
    menor = ConversaFactory(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        empresa=empresa,
        contato=ContatoFactory(empresa=empresa),
    )
    maior = ConversaFactory(
        id=UUID("00000000-0000-0000-0000-000000000002"),
        empresa=empresa,
        contato=ContatoFactory(empresa=empresa),
    )
    instante = timezone.now()
    Conversa.objects.filter(pk__in=(menor.id, maior.id)).update(atualizado_em=instante)

    assert [item.id for item in listar_conversas(empresa=empresa)] == [
        maior.id,
        menor.id,
    ]


@pytest.mark.django_db
def test_obter_historico_preserva_mensagens_e_ordena_por_data_e_uuid() -> None:
    """Retorna historico finalizado em ordem cronologica deterministica."""
    from apps.atendimento.dto import MensagemDTO
    from apps.atendimento.services.consultas.obter_historico import obter_historico

    conversa = ConversaFactory(estado=Conversa.Estado.FINALIZADA)
    maior = MensagemFactory(
        id=UUID("00000000-0000-0000-0000-000000000002"),
        conversa=conversa,
        empresa=conversa.empresa,
    )
    menor = MensagemFactory(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        conversa=conversa,
        empresa=conversa.empresa,
    )
    instante = timezone.now()
    Mensagem.objects.filter(pk__in=(menor.id, maior.id)).update(criado_em=instante)

    resultado = obter_historico(empresa=conversa.empresa, conversa_id=conversa.id)

    assert isinstance(resultado, list)
    assert [item.id for item in resultado] == [menor.id, maior.id]
    assert all(isinstance(item, MensagemDTO) for item in resultado)


@pytest.mark.django_db
def test_obter_historico_recusa_conversa_de_outra_empresa() -> None:
    """Nao diferencia ausencia de tentativa de acesso entre tenants."""
    from apps.atendimento.services.consultas.obter_historico import obter_historico

    conversa = ConversaFactory()
    with pytest.raises(ObjectDoesNotExist):
        obter_historico(empresa=EmpresaFactory(), conversa_id=conversa.id)
