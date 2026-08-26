"""Testes HTTP da configuracao e conexao do WhatsApp."""

import ast
from pathlib import Path
from unittest.mock import patch

import pytest
from django.test import Client

from apps.contas.models import Usuario
from apps.empresas.models import Empresa, MembroEmpresa


def _cliente(empresa: Empresa, papel: str) -> Client:
    """Autentica um membro para exercitar a API real."""
    usuario = Usuario.objects.create_user(
        email=f"{papel.lower()}-{empresa.pk}-wa-api@example.com"
    )
    MembroEmpresa.objects.create(usuario=usuario, empresa=empresa, papel=papel)
    cliente = Client()
    cliente.force_login(usuario)
    return cliente


def _payload(chave_api: str = "chave-api-evolution") -> dict[str, object]:
    """Monta uma configuracao HTTP completa e valida."""
    return {
        "url_base": "https://evolution.example.com",
        "nome_instancia": "empresa-api",
        "chave_api": chave_api,
    }


@pytest.mark.django_db
def test_api_whatsapp_exige_sessao() -> None:
    """Recusa cliente anonimo com o contrato HTTP comum."""
    resposta = Client().get("/api/v1/whatsapp/configuracao")

    assert resposta.status_code == 401
    assert resposta.json()["codigo"] == "nao_autenticado"


@pytest.mark.django_db
def test_put_e_get_configuracao_nao_expoem_chave(settings) -> None:
    """Publica somente o indicador da credencial Evolution persistida."""
    settings.IA_CHAVE_CRIPTOGRAFIA = "mestre-api-whatsapp"
    empresa = Empresa.objects.create(nome="Empresa API WhatsApp")
    cliente = _cliente(empresa, MembroEmpresa.Papel.ADMINISTRADOR)

    atualizacao = cliente.put(
        "/api/v1/whatsapp/configuracao",
        data=_payload(),
        content_type="application/json",
    )
    consulta = cliente.get("/api/v1/whatsapp/configuracao")

    assert atualizacao.status_code == 200
    assert consulta.status_code == 200
    for resposta in (atualizacao, consulta):
        assert "chave_api" not in resposta.json()
        assert resposta.json()["chave_configurada"] is True
        assert "chave-api-evolution" not in resposta.content.decode()


@pytest.mark.django_db
def test_api_expoe_qrcode_estado_conectar_e_desconectar() -> None:
    """Delega as quatro operacoes da conexao da empresa ativa."""
    from apps.whatsapp.integrations.protocolos import EstadoConexao
    from apps.whatsapp.services.configurar_instancia import ConfiguracaoWhatsAppPublica

    empresa = Empresa.objects.create(nome="Empresa operacoes API")
    cliente = _cliente(empresa, MembroEmpresa.Papel.ADMINISTRADOR)
    saida = ConfiguracaoWhatsAppPublica(
        url_base="https://evolution.example.com",
        nome_instancia="empresa-api",
        chave_configurada=True,
        ativo=True,
        estado=EstadoConexao.CONECTADO,
    )
    with (
        patch(
            "apps.whatsapp.api.endpoints.estado_conexao.consultar_estado",
            return_value=saida,
        ),
        patch(
            "apps.whatsapp.api.endpoints.qrcode.obter_qrcode",
            return_value="data:image/png;base64,QUJD",
        ),
        patch(
            "apps.whatsapp.api.endpoints.configuracao.conectar_instancia",
            return_value=saida,
        ),
        patch(
            "apps.whatsapp.api.endpoints.configuracao.desconectar_instancia",
            return_value=saida,
        ),
    ):
        estado = cliente.get("/api/v1/whatsapp/estado")
        qrcode = cliente.get("/api/v1/whatsapp/qrcode")
        conectar = cliente.post("/api/v1/whatsapp/conectar")
        desconectar = cliente.post("/api/v1/whatsapp/desconectar")

    assert estado.status_code == 200
    assert estado.json()["estado"] == "CONECTADO"
    assert qrcode.status_code == 200
    assert qrcode.json()["qrcode"] == "data:image/png;base64,QUJD"
    assert conectar.status_code == 200
    assert desconectar.status_code == 200


@pytest.mark.django_db
def test_api_qrcode_proibe_cache_do_conteudo_sensivel() -> None:
    """Evita que navegador ou intermediario retenha o QR temporario."""
    empresa = Empresa.objects.create(nome="Empresa QR sem cache")
    cliente = _cliente(empresa, MembroEmpresa.Papel.ADMINISTRADOR)

    with patch(
        "apps.whatsapp.api.endpoints.qrcode.obter_qrcode",
        return_value="data:image/png;base64,QUJD",
    ):
        resposta = cliente.get("/api/v1/whatsapp/qrcode")

    assert resposta.status_code == 200
    assert resposta.headers["Cache-Control"] == "no-store, private"
    assert resposta.headers["Pragma"] == "no-cache"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("nome_excecao", "status", "codigo"),
    [
        ("CredencialWhatsAppInvalida", 400, "credencial_whatsapp_invalida"),
        ("InstanciaWhatsAppNaoEncontrada", 404, "instancia_nao_encontrada"),
        ("LimiteWhatsAppExcedido", 429, "limite_whatsapp_excedido"),
        ("WhatsAppIndisponivel", 503, "whatsapp_indisponivel"),
    ],
)
def test_api_mapeia_falhas_externas_sem_vazar_detalhes(
    nome_excecao: str, status: int, codigo: str
) -> None:
    """Traduz erros do provider no contrato HTTP comum e seguro."""
    from apps.whatsapp.integrations import protocolos

    empresa = Empresa.objects.create(nome=f"Empresa erro {nome_excecao}")
    cliente = _cliente(empresa, MembroEmpresa.Papel.ADMINISTRADOR)
    excecao = getattr(protocolos, nome_excecao)("detalhe externo sensivel")

    with patch(
        "apps.whatsapp.api.endpoints.estado_conexao.consultar_estado",
        side_effect=excecao,
    ):
        resposta = cliente.get("/api/v1/whatsapp/estado")

    assert resposta.status_code == status
    assert resposta.json()["codigo"] == codigo
    assert "detalhe externo sensivel" not in resposta.content.decode()


@pytest.mark.django_db
def test_api_recusa_atendente_em_mutacoes() -> None:
    """Mantem configuracao e acoes remotas exclusivas de administrador."""
    empresa = Empresa.objects.create(nome="Empresa atendente API")
    cliente = _cliente(empresa, MembroEmpresa.Papel.ATENDENTE)

    configuracao = cliente.put(
        "/api/v1/whatsapp/configuracao",
        data=_payload(),
        content_type="application/json",
    )
    conexao = cliente.post("/api/v1/whatsapp/conectar")

    assert configuracao.status_code == 403
    assert conexao.status_code == 403


def test_endpoints_nao_importam_models_nem_provider_evolution() -> None:
    """Garante que a fronteira HTTP delega acesso persistente e externo."""
    importacoes: set[str] = set()
    for arquivo in Path("apps/whatsapp/api/endpoints").glob("*.py"):
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if isinstance(no, ast.ImportFrom) and no.module:
                importacoes.add(no.module)
            elif isinstance(no, ast.Import):
                importacoes.update(alias.name for alias in no.names)

    assert not {modulo for modulo in importacoes if ".models" in modulo}
    assert "apps.whatsapp.integrations.evolution" not in importacoes
