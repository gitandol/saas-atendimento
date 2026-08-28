"""Testes HTTP da caixa de entrada de atendimentos."""

import ast
from pathlib import Path
from unittest.mock import patch

import pytest
from django.test import Client

from apps.atendimento.models import Conversa, Mensagem
from apps.atendimento.tests.factories import (
    ContatoFactory,
    ConversaFactory,
    EmpresaFactory,
    MensagemFactory,
    UsuarioFactory,
)
from apps.empresas.models import MembroEmpresa


def _cliente_membro(empresa):
    """Autentica um atendente ativo da empresa informada."""
    usuario = UsuarioFactory()
    MembroEmpresa.objects.create(
        empresa=empresa,
        usuario=usuario,
        papel=MembroEmpresa.Papel.ATENDENTE,
    )
    cliente = Client()
    cliente.force_login(usuario)
    return cliente


@pytest.mark.django_db
def test_api_caixa_exige_sessao() -> None:
    """Falha se qualquer leitura operacional aceitar cliente anonimo."""
    cliente = Client()
    conversa = ConversaFactory()

    assert cliente.get("/api/v1/atendimento/conversas").status_code == 401
    assert (
        cliente.get(
            f"/api/v1/atendimento/conversas/{conversa.id}/mensagens"
        ).status_code
        == 401
    )


@pytest.mark.django_db
def test_lista_conversas_publica_contrato_ordenado_e_filtrado() -> None:
    """Falha se a API omitir dados operacionais ou ignorar busca e filtro."""
    empresa = EmpresaFactory()
    conversa = ConversaFactory(
        empresa=empresa,
        contato=ContatoFactory(
            empresa=empresa,
            nome="Ana Cliente",
            numero_normalizado="556899998888",
        ),
        modo=Conversa.Modo.HUMANO,
        contagem_nao_lida=2,
    )
    ultima = MensagemFactory(
        empresa=empresa,
        conversa=conversa,
        texto="Mensagem mais recente",
    )
    Conversa.objects.filter(pk=conversa.id).update(ultima_mensagem=ultima)
    ConversaFactory(
        empresa=empresa,
        contato=ContatoFactory(empresa=empresa, nome="Outro"),
        modo=Conversa.Modo.IA,
    )
    cliente = _cliente_membro(empresa)

    resposta = cliente.get(
        "/api/v1/atendimento/conversas",
        {"busca": "Ana", "filtro": "HUMANO"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["conversas"] == [
        {
            "id": str(conversa.id),
            "nome": "Ana Cliente",
            "numero": "556899998888",
            "previa": "Mensagem mais recente",
            "nao_lidas": 2,
            "modo": "HUMANO",
            "estado": "ABERTA",
            "atendente": "",
            "atualizado_em": resposta.json()["conversas"][0]["atualizado_em"],
        }
    ]


@pytest.mark.django_db
def test_historico_pagina_por_cursor_e_isola_empresa() -> None:
    """Falha se o cursor duplicar itens ou expuser conversa de outro tenant."""
    conversa = ConversaFactory()
    mensagens = [
        MensagemFactory(conversa=conversa, empresa=conversa.empresa) for _ in range(3)
    ]
    cliente = _cliente_membro(conversa.empresa)

    resposta = cliente.get(
        f"/api/v1/atendimento/conversas/{conversa.id}/mensagens",
        {"limite": 2},
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert [item["id"] for item in corpo["mensagens"]] == [
        str(mensagens[1].id),
        str(mensagens[2].id),
    ]
    assert corpo["proximo_cursor"] == str(mensagens[1].id)

    outra = ConversaFactory()
    assert (
        cliente.get(f"/api/v1/atendimento/conversas/{outra.id}/mensagens").status_code
        == 404
    )


@pytest.mark.django_db
def test_polling_limitado_nao_pula_a_primeira_mensagem_nova() -> None:
    """Falha se o excesso do polling descartar a mensagem mais antiga ainda nova."""
    conversa = ConversaFactory()
    anterior = MensagemFactory(conversa=conversa, empresa=conversa.empresa)
    novas = [
        MensagemFactory(conversa=conversa, empresa=conversa.empresa) for _ in range(3)
    ]
    cliente = _cliente_membro(conversa.empresa)

    resposta = cliente.get(
        f"/api/v1/atendimento/conversas/{conversa.id}/mensagens",
        {"depois_de": str(anterior.id), "limite": 2},
    )

    assert resposta.status_code == 200
    assert [item["id"] for item in resposta.json()["mensagens"]] == [
        str(novas[0].id),
        str(novas[1].id),
    ]


@pytest.mark.django_db
def test_marcar_lida_exige_post_e_zera_apenas_conversa_do_tenant() -> None:
    """Falha se leitura mutar por GET ou atravessar a empresa ativa."""
    conversa = ConversaFactory(contagem_nao_lida=5)
    cliente = _cliente_membro(conversa.empresa)

    assert (
        cliente.get(
            f"/api/v1/atendimento/conversas/{conversa.id}/marcar-lida"
        ).status_code
        == 405
    )
    resposta = cliente.post(f"/api/v1/atendimento/conversas/{conversa.id}/marcar-lida")

    assert resposta.status_code == 200
    assert resposta.json() == {
        "conversa_id": str(conversa.id),
        "nao_lidas": 0,
    }
    conversa.refresh_from_db()
    assert conversa.contagem_nao_lida == 0

    outra = ConversaFactory(contagem_nao_lida=4)
    assert (
        cliente.post(
            f"/api/v1/atendimento/conversas/{outra.id}/marcar-lida"
        ).status_code
        == 404
    )
    outra.refresh_from_db()
    assert outra.contagem_nao_lida == 4


@pytest.mark.django_db
def test_envio_manual_valida_schema_estado_e_tenant() -> None:
    """Falha se texto invalido, finalizada ou outro tenant puder enviar."""
    conversa = ConversaFactory()
    cliente = _cliente_membro(conversa.empresa)
    rota = f"/api/v1/atendimento/conversas/{conversa.id}/mensagens"

    assert (
        cliente.post(
            rota,
            data={"texto": ""},
            content_type="application/json",
        ).status_code
        == 422
    )
    assert (
        cliente.post(
            rota,
            data={"texto": "x" * 4097},
            content_type="application/json",
        ).status_code
        == 422
    )
    assert (
        cliente.post(
            rota,
            data={"texto": "   "},
            content_type="application/json",
        ).status_code
        == 422
    )

    finalizada = ConversaFactory(
        empresa=conversa.empresa,
        contato=ContatoFactory(empresa=conversa.empresa),
        estado=Conversa.Estado.FINALIZADA,
    )
    assert (
        cliente.post(
            f"/api/v1/atendimento/conversas/{finalizada.id}/mensagens",
            data={"texto": "Nao enviar"},
            content_type="application/json",
        ).status_code
        == 409
    )
    outra = ConversaFactory()
    assert (
        cliente.post(
            f"/api/v1/atendimento/conversas/{outra.id}/mensagens",
            data={"texto": "Nao enviar"},
            content_type="application/json",
        ).status_code
        == 404
    )


@pytest.mark.django_db
def test_envio_manual_cria_mensagem_pendente_e_retorna_202() -> None:
    """Falha se a API nao persistir e encaminhar a resposta pelo pipeline."""
    conversa = ConversaFactory()
    cliente = _cliente_membro(conversa.empresa)

    with patch("apps.whatsapp.services.enviar_mensagem.solicitar_envio") as solicitar:
        resposta = cliente.post(
            f"/api/v1/atendimento/conversas/{conversa.id}/mensagens",
            data={"texto": "Resposta pela API"},
            content_type="application/json",
            HTTP_X_CORRELATION_ID="manual-http-1",
        )

    assert resposta.status_code == 202
    mensagem = Mensagem.objects.get(pk=resposta.json()["id"])
    assert mensagem.texto == "Resposta pela API"
    assert mensagem.status == Mensagem.Status.PENDENTE
    solicitar.assert_called_once_with(mensagem.id, "manual-http-1")


@pytest.mark.django_db
def test_historico_valida_limite_do_cursor() -> None:
    """Falha se limite invalido chegar ao service ou provocar erro interno."""
    conversa = ConversaFactory()
    cliente = _cliente_membro(conversa.empresa)
    rota = f"/api/v1/atendimento/conversas/{conversa.id}/mensagens"

    assert cliente.get(rota, {"limite": 0}).status_code == 422
    assert cliente.get(rota, {"limite": 101}).status_code == 422


def test_endpoints_da_caixa_nao_importam_models_tasks_ou_integracoes() -> None:
    """Falha se a fronteira HTTP ultrapassar services e schemas."""
    for nome in ("conversas.py", "mensagens.py"):
        arquivo = Path("apps/atendimento/api/endpoints") / nome
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        importacoes = {
            no.module
            for no in ast.walk(arvore)
            if isinstance(no, ast.ImportFrom) and no.module
        }
        assert not {
            modulo
            for modulo in importacoes
            if ".models" in modulo or ".tasks" in modulo or ".integrations" in modulo
        }
