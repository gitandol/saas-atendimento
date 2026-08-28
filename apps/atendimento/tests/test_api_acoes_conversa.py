"""Testes HTTP das acoes de transferencia de conversa."""

import pytest
from django.test import Client

from apps.atendimento.models import Conversa
from apps.atendimento.tests.factories import ConversaFactory, UsuarioFactory
from apps.empresas.models import MembroEmpresa


def _cliente(empresa):
    """Autentica um atendente da empresa ativa."""
    usuario = UsuarioFactory()
    MembroEmpresa.objects.create(
        empresa=empresa,
        usuario=usuario,
        papel=MembroEmpresa.Papel.ATENDENTE,
    )
    cliente = Client()
    cliente.force_login(usuario)
    return cliente, usuario


@pytest.mark.django_db
def test_acoes_exigem_sessao_e_post() -> None:
    """Falha se as mutacoes aceitarem anonimato ou GET."""
    conversa = ConversaFactory()
    rota = f"/api/v1/atendimento/conversas/{conversa.id}/assumir"
    assert (
        Client().post(rota, data={}, content_type="application/json").status_code == 401
    )
    cliente, _ = _cliente(conversa.empresa)
    assert cliente.get(rota).status_code == 405


@pytest.mark.django_db
def test_endpoint_assumir_publica_estado_e_conflito_de_versao() -> None:
    """Falha se a API nao expuser a transicao ou seu conflito otimista."""
    conversa = ConversaFactory()
    cliente, ator = _cliente(conversa.empresa)
    rota = f"/api/v1/atendimento/conversas/{conversa.id}/assumir"
    payload = {"versao": 1, "justificativa": "Atendimento solicitado"}
    resposta = cliente.post(rota, data=payload, content_type="application/json")
    conflito = cliente.post(rota, data=payload, content_type="application/json")
    assert resposta.status_code == 200
    assert resposta.json()["modo"] == Conversa.Modo.HUMANO
    assert resposta.json()["atendente_id"] == str(ator.id)
    assert resposta.json()["versao"] == 2
    assert conflito.status_code == 409
    assert conflito.json()["codigo"] == "conflito_versao"


@pytest.mark.django_db
def test_endpoints_devolver_finalizar_e_reabrir() -> None:
    """Falha se alguma transicao explicita nao estiver publicada pela API."""
    conversa = ConversaFactory()
    cliente, _ = _cliente(conversa.empresa)
    base = f"/api/v1/atendimento/conversas/{conversa.id}"
    assumida = cliente.post(
        f"{base}/assumir",
        data={"versao": 1},
        content_type="application/json",
    ).json()
    devolvida = cliente.post(
        f"{base}/devolver-para-ia",
        data={"versao": assumida["versao"]},
        content_type="application/json",
    )
    finalizada = cliente.post(
        f"{base}/finalizar",
        data={"versao": devolvida.json()["versao"]},
        content_type="application/json",
    )
    reaberta = cliente.post(
        f"{base}/reabrir",
        data={"versao": finalizada.json()["versao"], "modo": "IA"},
        content_type="application/json",
    )
    assert devolvida.status_code == 200
    assert devolvida.json()["modo"] == "IA"
    assert finalizada.status_code == 200
    assert finalizada.json()["estado"] == "FINALIZADA"
    assert reaberta.status_code == 200
    assert reaberta.json()["estado"] == "ABERTA"
    assert reaberta.json()["modo"] == "IA"


@pytest.mark.django_db
def test_acoes_http_distinguem_permissao_tenant_e_transicao() -> None:
    """Falha se 403, 404 e 409 perderem seus significados operacionais."""
    conversa = ConversaFactory()
    responsavel_cliente, _ = _cliente(conversa.empresa)
    assumida = responsavel_cliente.post(
        f"/api/v1/atendimento/conversas/{conversa.id}/assumir",
        data={"versao": 1},
        content_type="application/json",
    ).json()
    terceiro_cliente, _ = _cliente(conversa.empresa)
    devolucao = terceiro_cliente.post(
        f"/api/v1/atendimento/conversas/{conversa.id}/devolver-para-ia",
        data={"versao": assumida["versao"]},
        content_type="application/json",
    )
    outra = ConversaFactory()
    isolada = responsavel_cliente.post(
        f"/api/v1/atendimento/conversas/{outra.id}/assumir",
        data={"versao": 1},
        content_type="application/json",
    )
    conflito = responsavel_cliente.post(
        f"/api/v1/atendimento/conversas/{conversa.id}/reabrir",
        data={"versao": assumida["versao"], "modo": "IA"},
        content_type="application/json",
    )
    assert devolucao.status_code == 403
    assert isolada.status_code == 404
    assert conflito.status_code == 409
