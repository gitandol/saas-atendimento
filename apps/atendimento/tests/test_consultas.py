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
    UsuarioFactory,
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
def test_listar_conversas_busca_filtra_e_publica_resumo_operacional() -> None:
    """Falha se a caixa ignorar busca, filtro ou dados visiveis da conversa."""
    from apps.atendimento.services.consultas.listar_conversas import listar_conversas

    empresa = EmpresaFactory()
    atendente = UsuarioFactory(first_name="Bia", last_name="Lima")
    conversa = ConversaFactory(
        empresa=empresa,
        contato=ContatoFactory(
            empresa=empresa,
            nome="Ana Souza",
            numero_normalizado="5568999990000",
        ),
        modo=Conversa.Modo.HUMANO,
        atendente=atendente,
        contagem_nao_lida=3,
    )
    ultima = MensagemFactory(
        empresa=empresa,
        conversa=conversa,
        texto="Preciso de ajuda com meu pedido",
    )
    Conversa.objects.filter(pk=conversa.id).update(ultima_mensagem=ultima)
    ConversaFactory(
        empresa=empresa,
        contato=ContatoFactory(empresa=empresa, nome="Outro contato"),
        modo=Conversa.Modo.IA,
    )

    resultado = listar_conversas(
        empresa=empresa,
        busca="(68) 99999-0000",
        filtro="HUMANO",
    )

    assert [item.id for item in resultado] == [conversa.id]
    assert resultado[0].ultima_mensagem_texto == "Preciso de ajuda com meu pedido"
    assert resultado[0].atendente_nome == "Bia Lima"
    assert resultado[0].contagem_nao_lida == 3


@pytest.mark.django_db
def test_listar_conversas_aplica_filtros_operacionais() -> None:
    """Falha se um filtro misturar abertas, modos ou finalizadas."""
    from apps.atendimento.services.consultas.listar_conversas import listar_conversas

    empresa = EmpresaFactory()
    aberta_ia = ConversaFactory(
        empresa=empresa,
        contato=ContatoFactory(empresa=empresa),
        modo=Conversa.Modo.IA,
    )
    aberta_humana = ConversaFactory(
        empresa=empresa,
        contato=ContatoFactory(empresa=empresa),
        modo=Conversa.Modo.HUMANO,
    )
    finalizada = ConversaFactory(
        empresa=empresa,
        contato=ContatoFactory(empresa=empresa),
        estado=Conversa.Estado.FINALIZADA,
    )

    assert {item.id for item in listar_conversas(empresa=empresa)} == {
        aberta_ia.id,
        aberta_humana.id,
    }
    assert [item.id for item in listar_conversas(empresa=empresa, filtro="IA")] == [
        aberta_ia.id
    ]
    assert [item.id for item in listar_conversas(empresa=empresa, filtro="HUMANO")] == [
        aberta_humana.id
    ]
    assert [
        item.id for item in listar_conversas(empresa=empresa, filtro="FINALIZADAS")
    ] == [finalizada.id]


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


@pytest.mark.django_db
def test_obter_historico_pagina_por_cursor_sem_duplicar_mensagens() -> None:
    """Falha se paginas adjacentes repetirem ou pularem mensagens."""
    from apps.atendimento.services.consultas.obter_historico import obter_historico

    conversa = ConversaFactory()
    mensagens = [
        MensagemFactory(conversa=conversa, empresa=conversa.empresa) for _ in range(4)
    ]
    instante = timezone.now()
    for indice, mensagem in enumerate(mensagens):
        Mensagem.objects.filter(pk=mensagem.id).update(
            criado_em=instante + timezone.timedelta(seconds=indice)
        )

    recentes = obter_historico(
        empresa=conversa.empresa,
        conversa_id=conversa.id,
        limite=2,
    )
    antigas = obter_historico(
        empresa=conversa.empresa,
        conversa_id=conversa.id,
        cursor=recentes[0].id,
        limite=2,
    )
    novas = obter_historico(
        empresa=conversa.empresa,
        conversa_id=conversa.id,
        depois_de=recentes[-1].id,
        limite=2,
    )

    assert [item.id for item in recentes] == [mensagens[2].id, mensagens[3].id]
    assert [item.id for item in antigas] == [mensagens[0].id, mensagens[1].id]
    assert novas == []
    assert not ({item.id for item in recentes} & {item.id for item in antigas})
