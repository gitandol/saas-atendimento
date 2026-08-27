"""Adapta a Evolution API ao protocolo interno de WhatsApp."""

import ipaddress
import json as json_lib
import socket
from collections.abc import Callable
from typing import Any, Protocol
from urllib.parse import quote, urlsplit

import requests

from apps.whatsapp.integrations.protocolos import (
    CredencialWhatsAppInvalida,
    EstadoConexao,
    InstanciaWhatsAppNaoEncontrada,
    LimiteWhatsAppExcedido,
    WhatsAppIndisponivel,
)


class RespostaHTTP(Protocol):
    """Descreve a resposta HTTP consumida pelo adaptador."""

    status_code: int
    headers: dict[str, str] | None

    def iter_content(self, chunk_size: int):
        """Entrega o corpo em blocos sem materializa-lo integralmente."""
        ...

    def close(self) -> None:
        """Libera a conexao HTTP apos a leitura limitada."""
        ...


class ClienteHTTP(Protocol):
    """Descreve a operacao HTTP injetavel usada pelo adaptador."""

    def request(self, metodo: str, url: str, **kwargs: object) -> RespostaHTTP:
        """Executa uma requisicao contra o fornecedor."""
        ...


Resolvedor = Callable[[str, int], set[str]]


def _endereco_privado_seguro(
    endereco: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> bool:
    """Aceita somente redes privadas sem classes especiais de endereco."""
    return (
        endereco.is_private
        and not endereco.is_global
        and not endereco.is_loopback
        and not endereco.is_link_local
        and not endereco.is_multicast
        and not endereco.is_unspecified
        and not endereco.is_reserved
    )


def _resolver_enderecos(host: str, porta: int) -> set[str]:
    """Resolve todos os enderecos usados para validar o destino externo."""
    try:
        resultados = socket.getaddrinfo(host, porta, type=socket.SOCK_STREAM)
    except OSError as erro:
        raise WhatsAppIndisponivel(
            "Nao foi possivel resolver a Evolution API."
        ) from erro
    return {resultado[4][0] for resultado in resultados}


class ProviderEvolution:
    """Implementa mensageria por meio da Evolution API."""

    def __init__(
        self,
        *,
        url_base: str,
        nome_instancia: str,
        chave_api: str,
        cliente: ClienteHTTP | None = None,
        resolvedor: Resolvedor | None = None,
        timeout: float = 15.0,
        limite_resposta: int = 1_000_000,
        hosts_internos_permitidos: frozenset[str] | None = None,
    ) -> None:
        """Configura destino, credencial e limites explicitos do transporte."""
        self.url_base = url_base.rstrip("/")
        self.nome_instancia = nome_instancia
        self._chave_api = chave_api
        self.cliente = cliente or requests.Session()
        self.resolvedor = resolvedor or _resolver_enderecos
        self.timeout = timeout
        self.limite_resposta = limite_resposta
        self.hosts_internos_permitidos = frozenset(
            host.rstrip(".").lower() for host in (hosts_internos_permitidos or ())
        )

    def __repr__(self) -> str:
        """Representa o provider sem revelar a credencial configurada."""
        return (
            "ProviderEvolution("
            f"url_base={self.url_base!r}, nome_instancia={self.nome_instancia!r})"
        )

    def _url(self, caminho: str) -> str:
        """Monta URL sem permitir que o nome da instancia altere o caminho."""
        instancia = quote(self.nome_instancia, safe="")
        return f"{self.url_base}/{caminho.format(instancia=instancia)}"

    def _validar_destino_resolvido(self) -> None:
        """Recusa qualquer endereco DNS que nao seja global antes da chamada."""
        try:
            partes = urlsplit(self.url_base)
            host = partes.hostname
            porta = partes.port
        except ValueError as erro:
            raise WhatsAppIndisponivel("A URL da Evolution e invalida.") from erro
        if not host:
            raise WhatsAppIndisponivel("A URL da Evolution e invalida.")
        host_normalizado = host.rstrip(".").lower()
        nomes_bloqueados = {
            "localhost",
            "metadata.google.internal",
            "metadata.google.com",
        }
        if host_normalizado in nomes_bloqueados or host_normalizado.endswith(
            ".localhost"
        ):
            raise WhatsAppIndisponivel("O destino da Evolution API nao e permitido.")
        try:
            endereco = ipaddress.ip_address(host_normalizado)
        except ValueError:
            endereco = None
        if endereco is not None and not endereco.is_global:
            raise WhatsAppIndisponivel("O destino da Evolution API nao e permitido.")
        esquema = partes.scheme.lower()
        host_interno = host_normalizado in self.hosts_internos_permitidos
        if esquema != "https" and not (esquema == "http" and host_interno):
            raise WhatsAppIndisponivel("O destino da Evolution API nao e permitido.")
        porta = porta or (443 if esquema == "https" else 80)
        enderecos = self.resolvedor(host, porta)
        if not enderecos:
            raise WhatsAppIndisponivel("A Evolution API nao possui endereco valido.")
        try:
            destinos = [ipaddress.ip_address(endereco) for endereco in enderecos]
        except ValueError as erro:
            raise WhatsAppIndisponivel(
                "A Evolution API resolveu para um endereco invalido."
            ) from erro
        if host_interno and any(
            not _endereco_privado_seguro(destino) for destino in destinos
        ):
            raise WhatsAppIndisponivel("O destino da Evolution API nao e permitido.")
        if not host_interno and any(not destino.is_global for destino in destinos):
            raise WhatsAppIndisponivel("O destino da Evolution API nao e permitido.")

    def _requisitar(
        self,
        metodo: str,
        caminho: str,
        *,
        json: dict[str, object] | None = None,
        chave_idempotencia: str = "",
    ) -> object:
        """Executa chamada limitada e traduz falhas externas conhecidas."""
        headers = {"apikey": self._chave_api}
        if chave_idempotencia:
            headers["Idempotency-Key"] = chave_idempotencia
        argumentos: dict[str, object] = {
            "headers": headers,
            "timeout": self.timeout,
        }
        if json is not None:
            argumentos["json"] = json
        self._validar_destino_resolvido()
        try:
            resposta = self.cliente.request(
                metodo,
                self._url(caminho),
                allow_redirects=False,
                stream=True,
                **argumentos,
            )
        except requests.Timeout as erro:
            raise WhatsAppIndisponivel(
                "A Evolution API excedeu o tempo limite."
            ) from erro
        except requests.RequestException as erro:
            raise WhatsAppIndisponivel(
                "Nao foi possivel acessar a Evolution API."
            ) from erro

        try:
            if resposta.status_code == 401:
                raise CredencialWhatsAppInvalida("A credencial Evolution foi recusada.")
            if resposta.status_code == 404:
                raise InstanciaWhatsAppNaoEncontrada("A instancia nao foi encontrada.")
            if resposta.status_code == 429:
                raise LimiteWhatsAppExcedido("O limite da Evolution API foi atingido.")
            if resposta.status_code < 200 or resposta.status_code >= 300:
                raise WhatsAppIndisponivel("A Evolution API esta indisponivel.")
            try:
                return self._ler_json_limitado(resposta)
            except requests.RequestException as erro:
                raise WhatsAppIndisponivel(
                    "A conexao com a Evolution falhou durante a resposta."
                ) from erro
        finally:
            resposta.close()

    def _ler_json_limitado(self, resposta: RespostaHTTP) -> object:
        """Interrompe o stream antes que o corpo ultrapasse o teto configurado."""
        headers_resposta = resposta.headers or {}
        tamanho_declarado = headers_resposta.get("Content-Length")
        if tamanho_declarado:
            try:
                if int(tamanho_declarado) > self.limite_resposta:
                    raise WhatsAppIndisponivel("A resposta da Evolution e excessiva.")
            except ValueError as erro:
                raise WhatsAppIndisponivel(
                    "A Evolution retornou cabecalhos invalidos."
                ) from erro

        corpo = bytearray()
        for bloco in resposta.iter_content(chunk_size=64 * 1024):
            if not bloco:
                continue
            if not isinstance(bloco, bytes):
                raise WhatsAppIndisponivel(
                    "A Evolution retornou uma resposta invalida."
                )
            if len(corpo) + len(bloco) > self.limite_resposta:
                raise WhatsAppIndisponivel("A resposta da Evolution e excessiva.")
            corpo.extend(bloco)
        try:
            return json_lib.loads(corpo.decode("utf-8"))
        except (UnicodeDecodeError, json_lib.JSONDecodeError) as erro:
            raise WhatsAppIndisponivel(
                "A Evolution retornou uma resposta invalida."
            ) from erro

    @staticmethod
    def _dicionario(payload: object) -> dict[str, Any]:
        """Exige um objeto JSON antes de acessar campos externos."""
        if not isinstance(payload, dict):
            raise WhatsAppIndisponivel("A Evolution retornou uma resposta invalida.")
        return payload

    def obter_qrcode(self) -> str:
        """Obtem o QR Code temporario sem persisti-lo localmente."""
        payload = self._dicionario(
            self._requisitar("GET", "instance/connect/{instancia}")
        )
        qrcode = payload.get("base64") or payload.get("code")
        if not isinstance(qrcode, str) or not qrcode.strip():
            raise WhatsAppIndisponivel("A Evolution nao retornou um QR Code valido.")
        return qrcode.strip()

    def consultar_estado(self) -> EstadoConexao:
        """Consulta e normaliza o estado externo da instancia."""
        payload = self._dicionario(
            self._requisitar("GET", "instance/connectionState/{instancia}")
        )
        instancia = payload.get("instance")
        estado = instancia.get("state") if isinstance(instancia, dict) else None
        mapa = {
            "open": EstadoConexao.CONECTADO,
            "connecting": EstadoConexao.AGUARDANDO_QR,
            "close": EstadoConexao.DESCONECTADO,
        }
        return mapa.get(estado, EstadoConexao.ERRO)

    def enviar_texto(self, numero: str, texto: str, chave_idempotencia: str) -> str:
        """Envia texto e retorna o identificador externo da mensagem."""
        payload = self._dicionario(
            self._requisitar(
                "POST",
                "message/sendText/{instancia}",
                json={"number": numero, "text": texto},
                chave_idempotencia=chave_idempotencia,
            )
        )
        chave = payload.get("key")
        identificador = chave.get("id") if isinstance(chave, dict) else None
        if not isinstance(identificador, str) or not identificador:
            raise WhatsAppIndisponivel(
                "A Evolution nao retornou o identificador da mensagem."
            )
        return identificador

    def conectar(self) -> None:
        """Cria a instancia e solicita a geracao de QR Code."""
        self._requisitar(
            "POST",
            "instance/create",
            json={
                "instanceName": self.nome_instancia,
                "qrcode": True,
                "integration": "WHATSAPP-BAILEYS",
            },
        )

    def desconectar(self) -> None:
        """Encerra a sessao ativa da instancia sem remover a configuracao."""
        self._requisitar("DELETE", "instance/logout/{instancia}")
