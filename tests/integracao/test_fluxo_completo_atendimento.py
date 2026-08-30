"""Exercita o aceite completo pelas paginas, API, services e tasks reais."""

import json
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.test import Client

from apps.atendimento.models import Conversa, Mensagem
from apps.auditoria.models import EventoAuditoria, RevisaoObjeto
from apps.contas.models import Usuario
from apps.empresas.models import Empresa, MembroEmpresa
from apps.ia.integrations.protocolos import RespostaIA
from apps.ia.tasks.responder_conversa import responder_conversa
from apps.whatsapp.services.enviar_mensagem import executar_envio
from apps.whatsapp.services.validar_webhook import gerar_token_webhook


class ProviderIAFalso:
    """Substitui somente a fronteira externa OpenAI."""

    def gerar_resposta(self, mensagens, modelo) -> RespostaIA:
        """Retorna uma resposta sintetica sem rede."""
        assert mensagens
        return RespostaIA(
            texto="resposta-automatica",
            modelo=modelo,
            tokens_entrada=7,
            tokens_saida=2,
        )


class ProviderWhatsAppFalso:
    """Substitui somente a fronteira externa Evolution."""

    def conectar(self) -> None:
        """Simula a inicializacao remota da instancia."""

    def enviar_texto(self, numero: str, texto: str, chave_idempotencia: str) -> str:
        """Simula entrega externa e devolve identificador opaco."""
        assert numero
        assert texto
        assert chave_idempotencia
        return f"evolution-{chave_idempotencia}"


def _payload_empresa(versao: str, telefone: str) -> dict[str, str]:
    """Monta a configuracao integral esperada pela API."""
    return {
        "nome": "Empresa Aceite",
        "segmento": "Servicos",
        "descricao": "Atendimento automatizado",
        "horario_atendimento": "08:00-18:00",
        "endereco": "Endereco sintetico",
        "telefone": telefone,
        "site": "https://example.com",
        "instrucoes_atendimento": "instrucao-privada",
        "atualizado_em": versao,
    }


def _payload_ia() -> dict[str, object]:
    """Monta configuracao de IA com credencial sintetica."""
    return {
        "modelo": "gpt-test",
        "nome_assistente": "Lia",
        "personalidade": "Objetiva",
        "mensagem_saudacao": "saudacao-sintetica",
        "mensagem_falha": "falha-sintetica",
        "respostas_automaticas_ativas": True,
        "chave_api": "sk-aceite-nao-registrar",
        "atualizado_em": None,
    }


def _payload_webhook(identificador: str, texto: str) -> dict[str, object]:
    """Monta uma mensagem textual sintetica da Evolution."""
    return {
        "event": "messages.upsert",
        "data": {
            "key": {
                "id": identificador,
                "remoteJid": f"55{'0' * 11}@s.whatsapp.net",
                "fromMe": False,
            },
            "pushName": "Cliente sintetico",
            "message": {"conversation": texto},
            "messageTimestamp": 1_725_192_000,
        },
    }


@pytest.mark.django_db
def test_fluxo_completo_de_atendimento(
    settings,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Completa configuracao, IA, envio, intervencao humana e finalizacao."""
    cache.clear()
    settings.IA_CHAVE_CRIPTOGRAFIA = "mestre-aceite-sintetica"
    empresa = Empresa.objects.create(nome="Empresa inicial")
    usuario = Usuario.objects.create_user(
        email="administrador-aceite@example.com",
        password="senha-aceite-segura",
    )
    MembroEmpresa.objects.create(
        empresa=empresa,
        usuario=usuario,
        papel=MembroEmpresa.Papel.ADMINISTRADOR,
    )
    cliente = Client(enforce_csrf_checks=True)

    csrf = cliente.get("/api/v1/autenticacao/csrf")
    token_csrf = csrf.json()["csrf_token"]
    cabecalho_csrf = {"HTTP_X_CSRFTOKEN": token_csrf}
    login = cliente.post(
        "/api/v1/autenticacao/login",
        data={"email": usuario.email, "senha": "senha-aceite-segura"},
        content_type="application/json",
        **cabecalho_csrf,
    )
    assert login.status_code == 200
    token_csrf = cliente.get("/api/v1/autenticacao/csrf").json()["csrf_token"]
    cabecalho_csrf = {"HTTP_X_CSRFTOKEN": token_csrf}

    paginas = (
        "/empresa/configuracao/",
        "/ia/configuracao/",
        "/whatsapp/configuracao/",
        "/atendimento/caixa-de-entrada/",
        "/painel/",
    )
    for pagina in paginas:
        resposta_pagina = cliente.get(pagina)
        assert resposta_pagina.status_code == 200
        assert "Ajuda" in resposta_pagina.content.decode()

    telefone = "+55 (00) 00000-0000"
    versao_empresa = cliente.get("/api/v1/empresa").json()["atualizado_em"]
    configuracao_empresa = cliente.put(
        "/api/v1/empresa",
        data=_payload_empresa(versao_empresa, telefone),
        content_type="application/json",
        **cabecalho_csrf,
    )
    configuracao_ia = cliente.put(
        "/api/v1/ia/configuracao",
        data=_payload_ia(),
        content_type="application/json",
        **cabecalho_csrf,
    )
    configuracao_whatsapp = cliente.put(
        "/api/v1/whatsapp/configuracao",
        data={
            "url_base": "https://evolution.example.com",
            "nome_instancia": "aceite",
            "chave_api": "evolution-aceite-nao-registrar",
        },
        content_type="application/json",
        **cabecalho_csrf,
    )
    assert configuracao_empresa.status_code == 200
    assert configuracao_ia.status_code == 200
    assert configuracao_whatsapp.status_code == 200

    with patch(
        "apps.ia.services.testar_configuracao.ProviderOpenAI",
        return_value=ProviderIAFalso(),
    ):
        teste_ia = cliente.post(
            "/api/v1/ia/teste",
            data={"modelo": "gpt-test", "chave_api": "sk-temporaria"},
            content_type="application/json",
            **cabecalho_csrf,
        )
    provider_whatsapp = ProviderWhatsAppFalso()
    with patch(
        "apps.whatsapp.services.configurar_instancia._obter_provider",
        return_value=provider_whatsapp,
    ):
        teste_whatsapp = cliente.post(
            "/api/v1/whatsapp/conectar",
            **cabecalho_csrf,
        )
    assert teste_ia.status_code == 200
    assert teste_whatsapp.status_code == 200

    token_webhook = gerar_token_webhook(empresa_id=empresa.id)
    rota_webhook = f"/api/v1/webhooks/evolution/{empresa.id}/{token_webhook}/"
    entrada_cliente = "conteudo-cliente-privado"
    with patch(
        "apps.whatsapp.services.receber_webhook.responder_conversa.delay"
    ) as enfileirar_ia:
        webhook = Client().post(
            rota_webhook,
            data=_payload_webhook("entrada-aceite-1", entrada_cliente),
            content_type="application/json",
            HTTP_X_CORRELATION_ID="aceite-webhook",
        )
    assert webhook.status_code == 200
    conversa_id, entrada_id, correlacao = enfileirar_ia.call_args.args

    with (
        patch(
            "apps.ia.services.gerar_resposta_atendimento.obter_provider",
            return_value=ProviderIAFalso(),
        ),
        patch("apps.whatsapp.services.enviar_mensagem.solicitar_envio"),
    ):
        assert responder_conversa.run(conversa_id, entrada_id, correlacao) is True
    mensagem_ia = Mensagem.objects.get(
        conversa_id=conversa_id,
        autor=Mensagem.Autor.IA,
    )
    with patch(
        "apps.whatsapp.services.enviar_mensagem.obter_provider",
        return_value=provider_whatsapp,
    ):
        assert executar_envio(
            mensagem_id=mensagem_ia.id,
            correlacao="aceite-envio-ia",
        )
    mensagem_ia.refresh_from_db()
    assert mensagem_ia.status == Mensagem.Status.ENVIADA

    conversa = Conversa.objects.get(pk=conversa_id)
    assumida = cliente.post(
        f"/api/v1/atendimento/conversas/{conversa.id}/assumir",
        data={"versao": conversa.versao, "justificativa": "Intervencao solicitada"},
        content_type="application/json",
        **cabecalho_csrf,
    )
    assert assumida.status_code == 200

    with patch(
        "apps.whatsapp.services.receber_webhook.responder_conversa.delay"
    ) as enfileirar_humano:
        segunda_entrada = Client().post(
            rota_webhook,
            data=_payload_webhook("entrada-aceite-2", "segunda-entrada-privada"),
            content_type="application/json",
        )
    assert segunda_entrada.status_code == 200
    argumentos_humano = enfileirar_humano.call_args.args
    assert responder_conversa.run(*argumentos_humano) is False

    texto_manual = "resposta-manual-privada"
    with patch(
        "apps.whatsapp.services.enviar_mensagem.solicitar_envio"
    ) as solicitar_manual:
        manual = cliente.post(
            f"/api/v1/atendimento/conversas/{conversa.id}/mensagens",
            data={"texto": texto_manual},
            content_type="application/json",
            **cabecalho_csrf,
        )
    assert manual.status_code == 202
    mensagem_manual = Mensagem.objects.get(pk=manual.json()["id"])
    solicitar_manual.assert_called_once()
    with patch(
        "apps.whatsapp.services.enviar_mensagem.obter_provider",
        return_value=provider_whatsapp,
    ):
        assert executar_envio(
            mensagem_id=mensagem_manual.id,
            correlacao="aceite-envio-manual",
        )

    conversa.refresh_from_db()
    finalizada = cliente.post(
        f"/api/v1/atendimento/conversas/{conversa.id}/finalizar",
        data={"versao": conversa.versao, "justificativa": "Atendimento concluido"},
        content_type="application/json",
        **cabecalho_csrf,
    )
    assert finalizada.status_code == 200
    assert finalizada.json()["estado"] == Conversa.Estado.FINALIZADA

    eventos = EventoAuditoria.objects.filter(empresa=empresa)
    assert eventos.count() >= 8
    assert RevisaoObjeto.objects.filter(empresa=empresa).exists()
    auditoria = json.dumps(
        [{"antes": evento.antes, "depois": evento.depois} for evento in eventos],
        ensure_ascii=False,
    )
    for sensivel in (
        telefone,
        "instrucao-privada",
        "sk-aceite-nao-registrar",
        "evolution-aceite-nao-registrar",
        entrada_cliente,
        "resposta-automatica",
        texto_manual,
    ):
        assert sensivel not in auditoria
        assert sensivel not in caplog.text
