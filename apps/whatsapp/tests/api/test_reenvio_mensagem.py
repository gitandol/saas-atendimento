"""Testes do endpoint interno de reenvio de mensagem."""

import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.test import Client

from apps.atendimento.models import Mensagem
from apps.atendimento.tests.factories import MensagemFactory, UsuarioFactory
from apps.empresas.models import MembroEmpresa


@pytest.mark.django_db
def test_endpoint_autentica_converte_uuid_e_delega_ao_service() -> None:
    """Falha se a fronteira HTTP executar elegibilidade ou fila diretamente."""
    mensagem = MensagemFactory(
        direcao=Mensagem.Direcao.SAIDA,
        status=Mensagem.Status.FALHA,
    )
    usuario = UsuarioFactory()
    MembroEmpresa.objects.create(
        empresa=mensagem.empresa,
        usuario=usuario,
        papel=MembroEmpresa.Papel.ATENDENTE,
    )
    cliente = Client()
    cliente.force_login(usuario)

    with patch(
        "apps.whatsapp.api.endpoints.reenvio_mensagem.reenviar_mensagem",
        return_value=SimpleNamespace(
            id=mensagem.id,
            status=Mensagem.Status.PENDENTE,
        ),
    ) as reenviar:
        resposta = cliente.post(
            f"/api/v1/whatsapp/mensagens/{mensagem.id}/reenviar",
            HTTP_X_CORRELATION_ID="corr-http-reenvio",
        )

    assert resposta.status_code == 202
    assert resposta.json() == {
        "mensagem_id": str(mensagem.id),
        "status": "PENDENTE",
    }
    argumentos = reenviar.call_args.kwargs
    assert argumentos["mensagem_id"] == mensagem.id
    assert argumentos["empresa"] == mensagem.empresa
    assert argumentos["ator"] == usuario
    assert argumentos["correlacao"] == "corr-http-reenvio"


def test_endpoint_nao_importa_models_tasks_ou_provider() -> None:
    """Mantem regra, persistencia e integracao fora da camada HTTP."""
    arquivo = Path("apps/whatsapp/api/endpoints/reenvio_mensagem.py")
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
