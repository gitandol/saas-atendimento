"""Testes dos services de configuracao e conexao do WhatsApp."""

from unittest.mock import patch
from uuid import UUID

import pytest
from django.core.exceptions import PermissionDenied

from apps.contas.models import Usuario
from apps.empresas.models import Empresa, MembroEmpresa


def _membro(empresa: Empresa, papel: str, email: str) -> Usuario:
    """Cria um membro ativo com papel explicito para os testes."""
    usuario = Usuario.objects.create_user(email=email)
    MembroEmpresa.objects.create(usuario=usuario, empresa=empresa, papel=papel)
    return usuario


def _dados(chave_api: str = "chave-evolution"):
    """Monta dados completos de uma configuracao Evolution segura."""
    from apps.whatsapp.services.configurar_instancia import DadosConfiguracaoWhatsApp

    return DadosConfiguracaoWhatsApp(
        url_base="https://evolution.example.com/",
        nome_instancia="empresa-principal",
        chave_api=chave_api,
    )


@pytest.mark.django_db
def test_atualizar_configuracao_criptografa_e_audita_sem_segredo(settings) -> None:
    """Persiste a credencial cifrada e audita somente seu indicador."""
    from apps.auditoria.models import EventoAuditoria, RevisaoObjeto
    from apps.whatsapp.models import ConfiguracaoWhatsApp
    from apps.whatsapp.services.configurar_instancia import atualizar_configuracao

    settings.IA_CHAVE_CRIPTOGRAFIA = "mestre-whatsapp"
    empresa = Empresa.objects.create(nome="Empresa configurada")
    ator = _membro(empresa, MembroEmpresa.Papel.ADMINISTRADOR, "admin-wa@example.com")

    saida = atualizar_configuracao(
        empresa=empresa,
        ator=ator,
        dados=_dados(),
        correlacao="corr-whatsapp",
    )

    configuracao = ConfiguracaoWhatsApp.objects.get(empresa=empresa)
    evento = EventoAuditoria.objects.get()
    revisao = RevisaoObjeto.objects.get()
    assert saida.url_base == "https://evolution.example.com"
    assert saida.chave_configurada is True
    assert "chave-evolution" not in configuracao.chave_api_criptografada
    assert "chave-evolution" not in str(evento.antes)
    assert "chave-evolution" not in str(evento.depois)
    assert "chave-evolution" not in str(revisao.snapshot)
    assert evento.depois["chave_configurada"] is True


@pytest.mark.django_db
def test_chave_vazia_preserva_credencial_existente(settings) -> None:
    """Distingue formulario sem chave nova de rotacao deliberada."""
    from apps.whatsapp.models import ConfiguracaoWhatsApp
    from apps.whatsapp.services.configurar_instancia import atualizar_configuracao

    settings.IA_CHAVE_CRIPTOGRAFIA = "mestre-preservacao"
    empresa = Empresa.objects.create(nome="Empresa preservada")
    ator = _membro(
        empresa, MembroEmpresa.Papel.ADMINISTRADOR, "preserva-wa@example.com"
    )
    atualizar_configuracao(
        empresa=empresa, ator=ator, dados=_dados(), correlacao="primeira"
    )
    cifra = ConfiguracaoWhatsApp.objects.get(empresa=empresa).chave_api_criptografada

    atualizar_configuracao(
        empresa=empresa, ator=ator, dados=_dados(chave_api=""), correlacao="segunda"
    )

    assert (
        ConfiguracaoWhatsApp.objects.get(empresa=empresa).chave_api_criptografada
        == cifra
    )


@pytest.mark.django_db
def test_services_respeitam_empresa_e_papel(settings) -> None:
    """Recusa leitura entre empresas e mutacao por atendente."""
    from apps.whatsapp.services.configurar_instancia import (
        atualizar_configuracao,
        obter_configuracao,
    )

    settings.IA_CHAVE_CRIPTOGRAFIA = "mestre-autorizacao"
    empresa = Empresa.objects.create(nome="Empresa protegida")
    externa = Empresa.objects.create(nome="Empresa externa")
    atendente = _membro(
        empresa, MembroEmpresa.Papel.ATENDENTE, "atendente-wa@example.com"
    )
    externo = _membro(
        externa, MembroEmpresa.Papel.ADMINISTRADOR, "externo-wa@example.com"
    )

    with pytest.raises(PermissionDenied):
        atualizar_configuracao(
            empresa=empresa,
            ator=atendente,
            dados=_dados(),
            correlacao="negada",
        )
    with pytest.raises(PermissionDenied):
        obter_configuracao(empresa=empresa, ator=externo)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url_base",
    [
        "http://evolution.example.com",
        "https://localhost:8080",
        "https://127.0.0.1",
        "https://169.254.169.254/latest/meta-data",
        "https://metadata.google.internal",
        "https://10.0.0.2",
        "https://[::1]",
    ],
)
def test_configuracao_recusa_url_insegura_em_producao(settings, url_base: str) -> None:
    """Exige HTTPS e bloqueia destinos locais, privados e de metadata."""
    from apps.whatsapp.services.configurar_instancia import (
        ConfiguracaoWhatsAppInvalida,
        DadosConfiguracaoWhatsApp,
        atualizar_configuracao,
    )

    settings.DEBUG = False
    settings.IA_CHAVE_CRIPTOGRAFIA = "mestre-url"
    empresa = Empresa.objects.create(nome=f"Empresa URL {url_base}")
    ator = _membro(
        empresa,
        MembroEmpresa.Papel.ADMINISTRADOR,
        f"url-{Empresa.objects.count()}@example.com",
    )
    dados = DadosConfiguracaoWhatsApp(
        url_base=url_base,
        nome_instancia="instancia",
        chave_api="chave",
    )

    with pytest.raises(ConfiguracaoWhatsAppInvalida):
        atualizar_configuracao(
            empresa=empresa, ator=ator, dados=dados, correlacao="url-insegura"
        )


@pytest.mark.django_db
def test_configuracao_aceita_http_apenas_para_host_interno_permitido(settings) -> None:
    """Libera o DNS privado gerenciado sem abrir HTTP para outros destinos."""
    from apps.whatsapp.services.configurar_instancia import (
        ConfiguracaoWhatsAppInvalida,
        DadosConfiguracaoWhatsApp,
        atualizar_configuracao,
    )

    settings.DEBUG = True
    settings.IA_CHAVE_CRIPTOGRAFIA = "mestre-interna"
    settings.WHATSAPP_HOSTS_INTERNOS_PERMITIDOS = frozenset({"evolution"})
    empresa = Empresa.objects.create(nome="Empresa Evolution interna")
    ator = _membro(
        empresa,
        MembroEmpresa.Papel.ADMINISTRADOR,
        "evolution-interna@example.com",
    )
    interna = DadosConfiguracaoWhatsApp(
        url_base="http://EVOLUTION.:8080/",
        nome_instancia="empresa-interna",
        chave_api="chave",
    )
    externa_http = DadosConfiguracaoWhatsApp(
        url_base="http://evolution.example.com:8080",
        nome_instancia="empresa-externa",
        chave_api="chave",
    )

    resultado = atualizar_configuracao(
        empresa=empresa,
        ator=ator,
        dados=interna,
        correlacao="interna",
    )
    assert resultado.url_base == "http://EVOLUTION.:8080"
    with pytest.raises(ConfiguracaoWhatsAppInvalida):
        atualizar_configuracao(
            empresa=empresa,
            ator=ator,
            dados=externa_http,
            correlacao="externa-http",
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("url_base", "host_permitido"),
    [
        ("http://evolution:8080/caminho invalido", "evolution"),
        ("http://evo_lution:8080", "evo_lution"),
    ],
)
def test_configuracao_recusa_url_interna_malformada(
    settings, url_base: str, host_permitido: str
) -> None:
    """Mantem as invariantes do URLField ao aceitar hostname sem TLD."""
    from apps.whatsapp.models import ConfiguracaoWhatsApp
    from apps.whatsapp.services.configurar_instancia import (
        ConfiguracaoWhatsAppInvalida,
        DadosConfiguracaoWhatsApp,
        atualizar_configuracao,
    )

    settings.IA_CHAVE_CRIPTOGRAFIA = "mestre-url-interna-invalida"
    settings.WHATSAPP_HOSTS_INTERNOS_PERMITIDOS = frozenset({host_permitido})
    empresa = Empresa.objects.create(nome="Empresa URL interna invalida")
    ator = _membro(
        empresa,
        MembroEmpresa.Papel.ADMINISTRADOR,
        "url-interna-invalida@example.com",
    )
    dados = DadosConfiguracaoWhatsApp(
        url_base=url_base,
        nome_instancia="instancia-interna",
        chave_api="chave",
    )

    with pytest.raises(ConfiguracaoWhatsAppInvalida):
        atualizar_configuracao(
            empresa=empresa,
            ator=ator,
            dados=dados,
            correlacao="url-interna-invalida",
        )
    assert not ConfiguracaoWhatsApp.objects.filter(empresa=empresa).exists()


@pytest.mark.django_db
def test_configuracao_vazia_publica_url_interna_padrao(settings) -> None:
    """Preenche a tela inicial sem expor qualquer credencial."""
    from apps.whatsapp.services.configurar_instancia import obter_configuracao

    settings.EVOLUTION_INTERNAL_URL = "http://evolution:8080"
    empresa = Empresa.objects.create(nome="Empresa sem configuracao")
    ator = _membro(
        empresa,
        MembroEmpresa.Papel.ADMINISTRADOR,
        "sem-configuracao@example.com",
    )

    resultado = obter_configuracao(empresa=empresa, ator=ator)

    assert resultado.url_base == "http://evolution:8080"
    assert resultado.chave_configurada is False


@pytest.mark.django_db
def test_configuracao_recusa_url_acima_do_limite_do_modelo(settings) -> None:
    """Preserva o limite do campo ao liberar o hostname Docker sem TLD."""
    from apps.whatsapp.services.configurar_instancia import (
        ConfiguracaoWhatsAppInvalida,
        DadosConfiguracaoWhatsApp,
        atualizar_configuracao,
    )

    settings.IA_CHAVE_CRIPTOGRAFIA = "mestre-limite-url"
    settings.WHATSAPP_HOSTS_INTERNOS_PERMITIDOS = frozenset({"evolution"})
    empresa = Empresa.objects.create(nome="Empresa URL longa")
    ator = _membro(
        empresa,
        MembroEmpresa.Papel.ADMINISTRADOR,
        "url-longa@example.com",
    )
    dados = DadosConfiguracaoWhatsApp(
        url_base="http://evolution:8080/" + "a" * 500,
        nome_instancia="instancia-longa",
        chave_api="chave",
    )

    with pytest.raises(ConfiguracaoWhatsAppInvalida):
        atualizar_configuracao(
            empresa=empresa,
            ator=ator,
            dados=dados,
            correlacao="url-longa",
        )


@pytest.mark.django_db
def test_conectar_e_desconectar_atualizam_estado_e_auditoria(settings) -> None:
    """Reflete as acoes remotas no estado local auditavel da empresa."""
    from apps.auditoria.models import EventoAuditoria
    from apps.whatsapp.integrations.protocolos import EstadoConexao
    from apps.whatsapp.services.configurar_instancia import (
        atualizar_configuracao,
        conectar_instancia,
        desconectar_instancia,
    )

    settings.IA_CHAVE_CRIPTOGRAFIA = "mestre-acoes"
    empresa = Empresa.objects.create(nome="Empresa acoes")
    ator = _membro(empresa, MembroEmpresa.Papel.ADMINISTRADOR, "acoes-wa@example.com")
    atualizar_configuracao(
        empresa=empresa, ator=ator, dados=_dados(), correlacao="configura"
    )

    with patch(
        "apps.whatsapp.services.configurar_instancia.ProviderEvolution"
    ) as provider:
        conectado = conectar_instancia(empresa=empresa, ator=ator, correlacao="conecta")
        desconectado = desconectar_instancia(
            empresa=empresa, ator=ator, correlacao="desconecta"
        )

    assert provider.return_value.conectar.call_count == 1
    assert provider.return_value.desconectar.call_count == 1
    assert conectado.ativo is True
    assert conectado.estado == EstadoConexao.AGUARDANDO_QR
    assert desconectado.ativo is False
    assert desconectado.estado == EstadoConexao.DESCONECTADO
    assert EventoAuditoria.objects.filter(correlacao="conecta").exists()
    assert EventoAuditoria.objects.filter(correlacao="desconecta").exists()


@pytest.mark.django_db
def test_conectar_configura_webhook_da_empresa(settings) -> None:
    """Impede conectar uma instancia incapaz de entregar mensagens recebidas."""
    from apps.whatsapp.services.configurar_instancia import (
        atualizar_configuracao,
        conectar_instancia,
    )

    settings.IA_CHAVE_CRIPTOGRAFIA = "mestre-webhook"
    settings.EVOLUTION_WEBHOOK_BASE_URL = "http://web:8000"
    empresa = Empresa.objects.create(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        nome="Empresa webhook automatico",
    )
    ator = _membro(
        empresa,
        MembroEmpresa.Papel.ADMINISTRADOR,
        "webhook-automatico@example.com",
    )
    atualizar_configuracao(
        empresa=empresa,
        ator=ator,
        dados=_dados(),
        correlacao="configura-webhook",
    )

    with (
        patch(
            "apps.whatsapp.services.configurar_instancia.ProviderEvolution"
        ) as provider,
        patch(
            "apps.whatsapp.services.validar_webhook.gerar_token_webhook",
            return_value="token-fixo",
        ),
    ):
        conectar_instancia(
            empresa=empresa,
            ator=ator,
            correlacao="conecta-webhook",
        )

    provider.return_value.conectar.assert_called_once_with(
        "http://web:8000/api/v1/webhooks/evolution/"
        "11111111-1111-1111-1111-111111111111/token-fixo/"
    )
    provider.return_value.configurar_webhook.assert_not_called()


@pytest.mark.django_db
def test_consulta_atualiza_estado_e_qrcode_nunca_e_persistido(settings) -> None:
    """Publica estado e QR temporario sem colocar o QR em banco ou auditoria."""
    from apps.auditoria.models import EventoAuditoria, RevisaoObjeto
    from apps.whatsapp.integrations.protocolos import EstadoConexao
    from apps.whatsapp.models import ConfiguracaoWhatsApp
    from apps.whatsapp.services.configurar_instancia import atualizar_configuracao
    from apps.whatsapp.services.consultar_conexao import (
        consultar_estado,
        obter_qrcode,
    )

    settings.IA_CHAVE_CRIPTOGRAFIA = "mestre-consulta"
    empresa = Empresa.objects.create(nome="Empresa consulta")
    ator = _membro(
        empresa, MembroEmpresa.Papel.ADMINISTRADOR, "consulta-wa@example.com"
    )
    atualizar_configuracao(
        empresa=empresa, ator=ator, dados=_dados(), correlacao="configura-consulta"
    )
    qrcode = "data:image/png;base64,QR-TEMPORARIO"
    with patch(
        "apps.whatsapp.services.configurar_instancia.ProviderEvolution"
    ) as provider:
        provider.return_value.consultar_estado.return_value = EstadoConexao.CONECTADO
        provider.return_value.obter_qrcode.return_value = qrcode
        estado = consultar_estado(
            empresa=empresa, ator=ator, correlacao="consulta-estado"
        )
        resultado_qr = obter_qrcode(empresa=empresa, ator=ator)

    configuracao = ConfiguracaoWhatsApp.objects.get(empresa=empresa)
    assert estado.estado == EstadoConexao.CONECTADO
    assert resultado_qr == qrcode
    assert qrcode not in str(configuracao.__dict__)
    assert qrcode not in str(list(EventoAuditoria.objects.values()))
    assert qrcode not in str(list(RevisaoObjeto.objects.values()))
