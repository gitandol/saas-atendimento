"""Testes HTTP da configuracao e conexao de IA."""

from unittest.mock import patch

import pytest
from django.test import Client

from apps.contas.models import Usuario
from apps.empresas.models import Empresa, MembroEmpresa


def _cliente(empresa: Empresa, papel: str) -> Client:
    """Autentica um membro para exercitar a API real."""
    usuario = Usuario.objects.create_user(email=f"{papel.lower()}-api@example.com")
    MembroEmpresa.objects.create(usuario=usuario, empresa=empresa, papel=papel)
    cliente = Client()
    cliente.force_login(usuario)
    return cliente


def _payload(chave_api: str = "sk-api") -> dict[str, object]:
    """Monta um payload HTTP completo e valido."""
    return {
        "modelo": "gpt-4.1-mini",
        "nome_assistente": "Lia",
        "personalidade": "Cordial",
        "mensagem_saudacao": "Ola!",
        "mensagem_falha": "Tente novamente.",
        "respostas_automaticas_ativas": True,
        "chave_api": chave_api,
        "atualizado_em": None,
    }


@pytest.mark.django_db
def test_api_ia_exige_sessao_com_erro_padronizado() -> None:
    """Recusa clientes anonimos sem devolver o formato interno do framework."""
    resposta = Client().get("/api/v1/ia/configuracao")

    assert resposta.status_code == 401
    assert resposta.json()["codigo"] == "nao_autenticado"


@pytest.mark.django_db
def test_get_e_put_nao_devolvem_chave_e_put_vazio_preserva(settings) -> None:
    """Publica apenas o indicador da credencial e preserva a cifra existente."""
    from apps.ia.models import ConfiguracaoIA

    settings.IA_CHAVE_CRIPTOGRAFIA = "mestre-api"
    empresa = Empresa.objects.create(nome="Empresa API")
    cliente = _cliente(empresa, MembroEmpresa.Papel.ADMINISTRADOR)
    primeira = cliente.put(
        "/api/v1/ia/configuracao",
        data=_payload(),
        content_type="application/json",
    )
    cifra = ConfiguracaoIA.objects.get(empresa=empresa).chave_api_criptografada

    payload_preservacao = _payload(chave_api="")
    payload_preservacao["atualizado_em"] = primeira.json()["atualizado_em"]
    segunda = cliente.put(
        "/api/v1/ia/configuracao",
        data=payload_preservacao,
        content_type="application/json",
    )
    consulta = cliente.get("/api/v1/ia/configuracao")

    assert primeira.status_code == 200
    assert segunda.status_code == 200
    assert consulta.status_code == 200
    for resposta in (primeira, segunda, consulta):
        assert "chave_api" not in resposta.json()
        assert resposta.json()["chave_configurada"] is True
    assert ConfiguracaoIA.objects.get(empresa=empresa).chave_api_criptografada == cifra


@pytest.mark.django_db
def test_api_remove_chave_somente_por_acao_explicita(settings) -> None:
    """Oferece uma acao dedicada que apaga a credencial existente."""
    settings.IA_CHAVE_CRIPTOGRAFIA = "mestre-api"
    empresa = Empresa.objects.create(nome="Empresa remocao")
    cliente = _cliente(empresa, MembroEmpresa.Papel.ADMINISTRADOR)
    cliente.put(
        "/api/v1/ia/configuracao",
        data=_payload(),
        content_type="application/json",
    )

    resposta = cliente.delete("/api/v1/ia/configuracao/chave")

    assert resposta.status_code == 200
    assert resposta.json()["chave_configurada"] is False


@pytest.mark.django_db
def test_api_recusa_atendente_e_payload_invalido() -> None:
    """Traduz autorizacao e schema para respostas HTTP padronizadas."""
    empresa = Empresa.objects.create(nome="Empresa validacao")
    cliente = _cliente(empresa, MembroEmpresa.Papel.ATENDENTE)

    proibida = cliente.put(
        "/api/v1/ia/configuracao",
        data=_payload(),
        content_type="application/json",
    )
    invalida = cliente.post(
        "/api/v1/ia/teste",
        data={"modelo": "", "chave_api": ""},
        content_type="application/json",
    )

    assert proibida.status_code == 403
    assert proibida.json()["codigo"] == "permissao_negada"
    assert invalida.status_code == 422
    assert invalida.json()["codigo"] == "dados_invalidos"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("excecao", "status", "codigo"),
    [
        ("LimiteIAExcedido", 429, "limite_ia_excedido"),
        ("IAIndisponivel", 503, "ia_indisponivel"),
        ("CredencialIAInvalida", 400, "credencial_ia_invalida"),
    ],
)
def test_api_teste_traduz_falhas_externas(
    excecao: str, status: int, codigo: str
) -> None:
    """Transforma excecoes de provider em erros acionaveis e sem segredo."""
    from apps.ia.integrations import protocolos

    empresa = Empresa.objects.create(nome="Empresa conexao")
    cliente = _cliente(empresa, MembroEmpresa.Papel.ADMINISTRADOR)
    tipo = getattr(protocolos, excecao)

    with patch(
        "apps.ia.api.endpoints.configuracao_ia.testar_configuracao",
        side_effect=tipo("detalhe externo sensivel"),
    ):
        resposta = cliente.post(
            "/api/v1/ia/teste",
            data={"modelo": "gpt-4.1-mini", "chave_api": "sk-nao-vazar"},
            content_type="application/json",
        )

    assert resposta.status_code == status
    assert resposta.json()["codigo"] == codigo
    assert "sk-nao-vazar" not in resposta.content.decode()
    assert "detalhe externo sensivel" not in resposta.content.decode()


@pytest.mark.django_db
def test_api_rejeita_atualizacao_obsoleta_com_409(settings) -> None:
    """Traduz conflito otimista sem sobrescrever a configuracao recente."""
    settings.IA_CHAVE_CRIPTOGRAFIA = "mestre-api-concorrencia"
    empresa = Empresa.objects.create(nome="Empresa concorrencia API")
    cliente = _cliente(empresa, MembroEmpresa.Papel.ADMINISTRADOR)
    primeira = cliente.put(
        "/api/v1/ia/configuracao", data=_payload(), content_type="application/json"
    )
    versao = primeira.json()["atualizado_em"]
    recente = _payload(chave_api="")
    recente["nome_assistente"] = "Edicao recente"
    recente["atualizado_em"] = versao
    assert (
        cliente.put(
            "/api/v1/ia/configuracao", data=recente, content_type="application/json"
        ).status_code
        == 200
    )
    obsoleta = _payload(chave_api="")
    obsoleta["nome_assistente"] = "Edicao obsoleta"
    obsoleta["atualizado_em"] = versao
    resposta = cliente.put(
        "/api/v1/ia/configuracao", data=obsoleta, content_type="application/json"
    )
    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "versao_obsoleta"


@pytest.mark.django_db
def test_correlacao_muito_longa_e_substituida(settings) -> None:
    """Evita erro de persistencia causado por cabecalho fora do contrato."""
    from apps.auditoria.models import EventoAuditoria

    settings.IA_CHAVE_CRIPTOGRAFIA = "mestre-correlacao"
    empresa = Empresa.objects.create(nome="Empresa correlacao")
    cliente = _cliente(empresa, MembroEmpresa.Papel.ADMINISTRADOR)
    resposta = cliente.put(
        "/api/v1/ia/configuracao",
        data=_payload(),
        content_type="application/json",
        HTTP_X_CORRELATION_ID="x" * 81,
    )
    assert resposta.status_code == 200
    assert len(EventoAuditoria.objects.get().correlacao) <= 80


@pytest.mark.django_db
def test_primeiro_put_aceita_versao_vazia_enviada_pelo_formulario(settings) -> None:
    """Normaliza o campo oculto vazio antes da primeira configuracao."""
    settings.IA_CHAVE_CRIPTOGRAFIA = "mestre-primeiro-put"
    empresa = Empresa.objects.create(nome="Empresa primeiro PUT")
    cliente = _cliente(empresa, MembroEmpresa.Papel.ADMINISTRADOR)
    payload = _payload()
    payload["atualizado_em"] = ""

    resposta = cliente.put(
        "/api/v1/ia/configuracao",
        data=payload,
        content_type="application/json",
    )

    assert resposta.status_code == 200
