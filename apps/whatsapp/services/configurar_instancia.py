"""Configura e aciona a instancia Evolution da empresa autorizada."""

import ipaddress
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.auditoria.models import EventoAuditoria
from apps.auditoria.services.registrar_alteracao import registrar_alteracao
from apps.contas.models import Usuario
from apps.empresas.models import Empresa, MembroEmpresa
from apps.empresas.services.obter_empresa import autorizar_membro
from apps.whatsapp.integrations.evolution import ProviderEvolution
from apps.whatsapp.integrations.protocolos import (
    CredencialWhatsAppInvalida,
    EstadoConexao,
    InstanciaWhatsAppNaoEncontrada,
    ProviderWhatsApp,
)
from apps.whatsapp.models import ConfiguracaoWhatsApp
from apps.whatsapp.services.criptografia import (
    ChaveCriptografadaInvalida,
    criptografar_chave,
    descriptografar_chave,
)


class ConfiguracaoWhatsAppInvalida(Exception):
    """Indica que destino ou identificadores nao sao seguros e validos."""


@dataclass(frozen=True)
class DadosConfiguracaoWhatsApp:
    """Agrupa os dados editaveis recebidos pela camada de dominio."""

    url_base: str
    nome_instancia: str
    chave_api: str = ""


@dataclass(frozen=True)
class ConfiguracaoWhatsAppPublica:
    """Expoe configuracao e estado sem carregar a credencial persistida."""

    url_base: str
    nome_instancia: str
    chave_configurada: bool
    ativo: bool
    estado: EstadoConexao
    atualizado_em: datetime | None = None


def _publicar(
    configuracao: ConfiguracaoWhatsApp | None,
) -> ConfiguracaoWhatsAppPublica:
    """Converte o model em representacao publica sem segredo."""
    if configuracao is None:
        return ConfiguracaoWhatsAppPublica(
            url_base=settings.EVOLUTION_INTERNAL_URL,
            nome_instancia="",
            chave_configurada=False,
            ativo=False,
            estado=EstadoConexao.DESCONECTADO,
        )
    return ConfiguracaoWhatsAppPublica(
        url_base=configuracao.url_base,
        nome_instancia=configuracao.nome_instancia,
        chave_configurada=bool(configuracao.chave_api_criptografada),
        ativo=configuracao.ativo,
        estado=EstadoConexao(configuracao.estado),
        atualizado_em=configuracao.atualizado_em,
    )


def _snapshot(configuracao: ConfiguracaoWhatsApp | None) -> dict[str, Any]:
    """Produz estado auditavel sem cifra, credencial ou QR Code."""
    publica = _publicar(configuracao)
    return {
        "url_base": publica.url_base,
        "nome_instancia": publica.nome_instancia,
        "chave_configurada": publica.chave_configurada,
        "ativo": publica.ativo,
        "estado": publica.estado,
    }


def _exigir_administrador(*, empresa: Empresa, ator: Usuario) -> None:
    """Exige papel administrativo ativo dentro da empresa informada."""
    membro = autorizar_membro(empresa=empresa, ator=ator)
    if membro.papel != MembroEmpresa.Papel.ADMINISTRADOR:
        raise PermissionDenied


def _validar_url(url_base: str) -> str:
    """Normaliza HTTPS e bloqueia alvos locais, privados e de metadata."""
    valor = url_base.strip().rstrip("/")
    try:
        partes = urlsplit(valor)
        hostname = partes.hostname
        porta = partes.port
    except ValueError as erro:
        raise ConfiguracaoWhatsAppInvalida("A URL da Evolution e invalida.") from erro
    if (
        not hostname
        or partes.username
        or partes.password
        or partes.query
        or partes.fragment
        or porta is not None
        and not 1 <= porta <= 65535
    ):
        raise ConfiguracaoWhatsAppInvalida("A URL da Evolution e invalida.")
    host_interno = _host_interno_permitido(hostname)
    if partes.scheme.lower() != "https" and not (
        partes.scheme.lower() == "http" and host_interno
    ):
        raise ConfiguracaoWhatsAppInvalida(
            "A URL da Evolution deve usar HTTPS ou um host interno permitido."
        )

    host = hostname.rstrip(".").lower()
    nomes_bloqueados = {
        "localhost",
        "metadata.google.internal",
        "metadata.google.com",
    }
    if host in nomes_bloqueados or host.endswith(".localhost"):
        raise ConfiguracaoWhatsAppInvalida("O host da Evolution nao e permitido.")
    try:
        endereco = ipaddress.ip_address(host)
    except ValueError:
        endereco = None
    if endereco is not None and not endereco.is_global:
        raise ConfiguracaoWhatsAppInvalida("O host da Evolution nao e permitido.")
    return valor


def _host_interno_permitido(host: str) -> bool:
    """Compara hostname normalizado com a allowlist gerenciada."""
    normalizado = host.rstrip(".").lower()
    return normalizado in settings.WHATSAPP_HOSTS_INTERNOS_PERMITIDOS


def obter_configuracao(
    *, empresa: Empresa, ator: Usuario
) -> ConfiguracaoWhatsAppPublica:
    """Consulta somente a configuracao da empresa autorizada."""
    autorizar_membro(empresa=empresa, ator=ator)
    configuracao = ConfiguracaoWhatsApp.objects.filter(empresa=empresa).first()
    return _publicar(configuracao)


@transaction.atomic
def atualizar_configuracao(
    *,
    empresa: Empresa,
    ator: Usuario,
    dados: DadosConfiguracaoWhatsApp,
    correlacao: str,
) -> ConfiguracaoWhatsAppPublica:
    """Persiste destino e credencial cifrada com auditoria segura."""
    empresa = Empresa.objects.select_for_update().get(pk=empresa.pk)
    _exigir_administrador(empresa=empresa, ator=ator)
    url_base = _validar_url(dados.url_base)
    nome_instancia = dados.nome_instancia.strip()
    if not nome_instancia or len(nome_instancia) > 120:
        raise ConfiguracaoWhatsAppInvalida("Informe um nome de instancia valido.")
    configuracao = (
        ConfiguracaoWhatsApp.objects.select_for_update().filter(empresa=empresa).first()
    )
    criada = configuracao is None
    if configuracao is None:
        configuracao = ConfiguracaoWhatsApp(empresa=empresa)
    antes = {} if criada else _snapshot(configuracao)
    destino_alterado = (
        configuracao.url_base != url_base
        or configuracao.nome_instancia != nome_instancia
    )
    configuracao.url_base = url_base
    configuracao.nome_instancia = nome_instancia
    if destino_alterado:
        configuracao.ativo = False
        configuracao.estado = EstadoConexao.DESCONECTADO
    chave_alterada = bool(dados.chave_api.strip())
    if chave_alterada:
        configuracao.chave_api_criptografada = criptografar_chave(
            dados.chave_api.strip()
        )
    configuracao.full_clean(exclude=["url_base"])
    configuracao.save()
    depois = _snapshot(configuracao)
    campos_alterados = [
        campo for campo, valor in depois.items() if antes.get(campo) != valor
    ]
    if chave_alterada and not criada:
        campos_alterados.append("chave_api")
    registrar_alteracao(
        empresa=empresa,
        objeto=configuracao,
        acao=EventoAuditoria.Acao.CRIACAO
        if criada
        else EventoAuditoria.Acao.ATUALIZACAO,
        antes=antes,
        depois=depois,
        campos_alterados=campos_alterados,
        ator=ator,
        origem="api",
        correlacao=correlacao,
    )
    return _publicar(configuracao)


def _obter_provider(empresa: Empresa) -> ProviderWhatsApp:
    """Constroi o provider sem expor credenciais ao consumidor."""
    configuracao = ConfiguracaoWhatsApp.objects.filter(empresa=empresa).first()
    if configuracao is None:
        raise InstanciaWhatsAppNaoEncontrada("Configure uma instancia de WhatsApp.")
    if not configuracao.chave_api_criptografada:
        raise CredencialWhatsAppInvalida("Configure a credencial Evolution.")
    try:
        chave_api = descriptografar_chave(configuracao.chave_api_criptografada)
    except ChaveCriptografadaInvalida as erro:
        raise CredencialWhatsAppInvalida(
            "A credencial Evolution precisa ser configurada novamente."
        ) from erro
    return ProviderEvolution(
        url_base=configuracao.url_base,
        nome_instancia=configuracao.nome_instancia,
        chave_api=chave_api,
        hosts_internos_permitidos=settings.WHATSAPP_HOSTS_INTERNOS_PERMITIDOS,
    )


def _registrar_estado(
    *,
    configuracao: ConfiguracaoWhatsApp,
    empresa: Empresa,
    ator: Usuario,
    correlacao: str,
    ativo: bool,
    estado: EstadoConexao,
) -> ConfiguracaoWhatsAppPublica:
    """Atualiza estado operacional e registra sua transicao."""
    antes = _snapshot(configuracao)
    configuracao.ativo = ativo
    configuracao.estado = estado
    configuracao.save(update_fields=["ativo", "estado", "atualizado_em"])
    depois = _snapshot(configuracao)
    campos_alterados = [
        campo for campo, valor in depois.items() if antes.get(campo) != valor
    ]
    if campos_alterados:
        registrar_alteracao(
            empresa=empresa,
            objeto=configuracao,
            acao=EventoAuditoria.Acao.ATUALIZACAO,
            antes=antes,
            depois=depois,
            campos_alterados=campos_alterados,
            ator=ator,
            origem="api",
            correlacao=correlacao,
        )
    return _publicar(configuracao)


@transaction.atomic
def conectar_instancia(
    *, empresa: Empresa, ator: Usuario, correlacao: str
) -> ConfiguracaoWhatsAppPublica:
    """Aciona a instancia remota e marca espera pelo QR Code."""
    _exigir_administrador(empresa=empresa, ator=ator)
    configuracao = (
        ConfiguracaoWhatsApp.objects.select_for_update().filter(empresa=empresa).first()
    )
    if configuracao is None:
        raise InstanciaWhatsAppNaoEncontrada("Configure uma instancia de WhatsApp.")
    _obter_provider(empresa).conectar()
    return _registrar_estado(
        configuracao=configuracao,
        empresa=empresa,
        ator=ator,
        correlacao=correlacao,
        ativo=True,
        estado=EstadoConexao.AGUARDANDO_QR,
    )


@transaction.atomic
def desconectar_instancia(
    *, empresa: Empresa, ator: Usuario, correlacao: str
) -> ConfiguracaoWhatsAppPublica:
    """Encerra a sessao remota e marca a instancia desconectada."""
    _exigir_administrador(empresa=empresa, ator=ator)
    configuracao = (
        ConfiguracaoWhatsApp.objects.select_for_update().filter(empresa=empresa).first()
    )
    if configuracao is None:
        raise InstanciaWhatsAppNaoEncontrada("Configure uma instancia de WhatsApp.")
    _obter_provider(empresa).desconectar()
    return _registrar_estado(
        configuracao=configuracao,
        empresa=empresa,
        ator=ator,
        correlacao=correlacao,
        ativo=False,
        estado=EstadoConexao.DESCONECTADO,
    )
