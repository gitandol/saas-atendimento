"""Testes do provider Evolution isolado por uma fronteira HTTP falsa."""

from dataclasses import dataclass

import pytest
import requests


@dataclass
class RespostaHTTPFalsa:
    """Representa a parte da resposta HTTP consumida pelo provider."""

    status_code: int
    payload: object
    content: bytes = b"{}"
    headers: dict[str, str] | None = None

    def json(self) -> object:
        """Entrega o payload configurado pelo caso de teste."""
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload

    def iter_content(self, chunk_size: int) -> list[bytes]:
        """Entrega o corpo em blocos como uma resposta requests em streaming."""
        return [
            self.content[indice : indice + chunk_size]
            for indice in range(0, len(self.content), chunk_size)
        ]

    def close(self) -> None:
        """Simula a liberacao da conexao HTTP."""


class RespostaStreamingFalsa:
    """Prova que o provider limita blocos sem acessar corpo bufferizado."""

    status_code = 200
    headers: dict[str, str] = {}

    @property
    def content(self) -> bytes:
        """Falha caso a implementacao tente materializar todo o corpo."""
        raise AssertionError("o corpo nao pode ser bufferizado antes do limite")

    def iter_content(self, chunk_size: int):
        """Entrega blocos sem Content-Length ate exceder o teto."""
        del chunk_size
        yield b"x" * 80
        yield b"y" * 49

    def close(self) -> None:
        """Simula a liberacao da conexao HTTP."""


class RespostaStreamingComFalha:
    """Simula timeout ocorrido depois que os cabecalhos foram recebidos."""

    status_code = 200
    headers: dict[str, str] = {}

    def __init__(self) -> None:
        """Inicia a resposta ainda nao liberada."""
        self.fechada = False

    def iter_content(self, chunk_size: int):
        """Falha durante a leitura do primeiro bloco do corpo."""
        del chunk_size
        raise requests.Timeout("timeout durante o stream")
        yield b""  # pragma: no cover

    def close(self) -> None:
        """Registra que a conexao foi liberada mesmo depois da falha."""
        self.fechada = True


class ClienteHTTPFalso:
    """Registra chamadas e devolve respostas controladas sem rede."""

    def __init__(self, resultados: list[object]) -> None:
        """Guarda os resultados devolvidos na ordem das chamadas."""
        self.resultados = list(resultados)
        self.chamadas: list[dict[str, object]] = []

    def request(self, metodo: str, url: str, **kwargs: object) -> RespostaHTTPFalsa:
        """Simula uma requisicao externa com metodo e argumentos observaveis."""
        self.chamadas.append({"metodo": metodo, "url": url, **kwargs})
        resultado = self.resultados.pop(0)
        if isinstance(resultado, Exception):
            raise resultado
        return resultado  # type: ignore[return-value]


def _provider(*resultados: object):
    """Cria o provider real com transporte HTTP controlado."""
    from apps.whatsapp.integrations.evolution import ProviderEvolution

    return ProviderEvolution(
        url_base="https://evolution.example.com/",
        nome_instancia="empresa-1",
        chave_api="chave-evolution",
        cliente=ClienteHTTPFalso(list(resultados)),
        resolvedor=lambda _host, _porta: {"93.184.216.34"},
        timeout=6.0,
        limite_resposta=128,
    )


def test_provider_obtem_qrcode_sem_persistir_payload_externo() -> None:
    """Extrai o QR Code temporario e envia credencial apenas no cabecalho."""
    resposta = RespostaHTTPFalsa(
        200,
        {"base64": "data:image/png;base64,QUJD"},
        content=b'{"base64":"data:image/png;base64,QUJD"}',
        headers={"Content-Length": "44"},
    )
    provider = _provider(resposta)

    qrcode = provider.obter_qrcode()

    assert qrcode == "data:image/png;base64,QUJD"
    chamada = provider.cliente.chamadas[0]
    assert chamada["metodo"] == "GET"
    assert chamada["url"] == "https://evolution.example.com/instance/connect/empresa-1"
    assert chamada["headers"]["apikey"] == "chave-evolution"
    from uuid import UUID

    UUID(chamada["headers"]["X-Correlation-ID"])
    assert chamada["timeout"] == 6.0


@pytest.mark.parametrize(
    ("estado_externo", "estado_esperado"),
    [
        ("open", "CONECTADO"),
        ("connecting", "AGUARDANDO_QR"),
        ("close", "DESCONECTADO"),
        ("desconhecido", "ERRO"),
    ],
)
def test_provider_normaliza_estado(estado_externo: str, estado_esperado: str) -> None:
    """Converte estados do fornecedor no conjunto estavel do dominio."""
    from apps.whatsapp.integrations.protocolos import EstadoConexao

    provider = _provider(
        RespostaHTTPFalsa(
            200,
            {"instance": {"state": estado_externo}},
            content=(f'{{"instance":{{"state":"{estado_externo}"}}}}'.encode()),
        )
    )

    assert provider.consultar_estado() == EstadoConexao(estado_esperado)


@pytest.mark.parametrize(
    ("resultado", "nome_excecao"),
    [
        (requests.Timeout("tempo excedido"), "WhatsAppIndisponivel"),
        (RespostaHTTPFalsa(401, {}, content=b"{}"), "CredencialWhatsAppInvalida"),
        (RespostaHTTPFalsa(404, {}, content=b"{}"), "InstanciaWhatsAppNaoEncontrada"),
        (RespostaHTTPFalsa(429, {}, content=b"{}"), "LimiteWhatsAppExcedido"),
        (RespostaHTTPFalsa(503, {}, content=b"{}"), "WhatsAppIndisponivel"),
        (RespostaHTTPFalsa(200, {}, content=b"{"), "WhatsAppIndisponivel"),
    ],
)
def test_provider_traduz_falhas_externas(resultado: object, nome_excecao: str) -> None:
    """Converte transporte, status e JSON invalido em erros de dominio."""
    from apps.whatsapp.integrations import protocolos

    with pytest.raises(getattr(protocolos, nome_excecao)):
        _provider(resultado).consultar_estado()


def test_provider_recusa_resposta_acima_do_limite() -> None:
    """Impede que uma resposta externa excessiva seja carregada no dominio."""
    from apps.whatsapp.integrations.protocolos import WhatsAppIndisponivel

    resposta = RespostaHTTPFalsa(
        200,
        {"instance": {"state": "open"}},
        content=b"x" * 129,
        headers={"Content-Length": "129"},
    )
    with pytest.raises(WhatsAppIndisponivel):
        _provider(resposta).consultar_estado()


def test_provider_interrompe_stream_sem_content_length_antes_de_bufferizar() -> None:
    """Corta resposta em blocos assim que o limite total e ultrapassado."""
    from apps.whatsapp.integrations.protocolos import WhatsAppIndisponivel

    with pytest.raises(WhatsAppIndisponivel):
        _provider(RespostaStreamingFalsa()).consultar_estado()


def test_provider_traduz_timeout_durante_stream_e_fecha_resposta() -> None:
    """Mantem o contrato de indisponibilidade quando a leitura HTTP falha."""
    from apps.whatsapp.integrations.protocolos import WhatsAppIndisponivel

    resposta = RespostaStreamingComFalha()
    with pytest.raises(WhatsAppIndisponivel):
        _provider(resposta).consultar_estado()
    assert resposta.fechada is True


def test_provider_recusa_hostname_resolvido_para_rede_privada_antes_da_chamada() -> (
    None
):
    """Bloqueia DNS que direciona um hostname publico para destino interno."""
    from apps.whatsapp.integrations.evolution import ProviderEvolution
    from apps.whatsapp.integrations.protocolos import WhatsAppIndisponivel

    cliente = ClienteHTTPFalso([])
    provider = ProviderEvolution(
        url_base="https://evolution.example.com",
        nome_instancia="empresa-1",
        chave_api="chave",
        cliente=cliente,
        resolvedor=lambda _host, _porta: {"127.0.0.1"},
    )

    with pytest.raises(WhatsAppIndisponivel):
        provider.consultar_estado()
    assert cliente.chamadas == []


def test_provider_aceita_dns_privado_somente_para_host_interno_permitido() -> None:
    """Permite a rede Docker explicitamente confiada e preserva o bloqueio geral."""
    from apps.whatsapp.integrations.evolution import ProviderEvolution
    from apps.whatsapp.integrations.protocolos import EstadoConexao

    resposta = RespostaHTTPFalsa(
        200,
        {"instance": {"state": "open"}},
        content=b'{"instance":{"state":"open"}}',
    )
    provider = ProviderEvolution(
        url_base="http://evolution:8080",
        nome_instancia="empresa-1",
        chave_api="chave",
        cliente=ClienteHTTPFalso([resposta]),
        resolvedor=lambda _host, _porta: {"172.20.0.5"},
        hosts_internos_permitidos=frozenset({"evolution"}),
    )

    assert provider.consultar_estado() == EstadoConexao.CONECTADO


@pytest.mark.parametrize(
    "endereco_resolvido",
    ["127.0.0.1", "169.254.169.254", "::1"],
)
def test_provider_recusa_hostname_interno_resolvido_para_destino_inseguro(
    endereco_resolvido: str,
) -> None:
    """Nao amplia a allowlist de hostname para loopback ou metadata."""
    from apps.whatsapp.integrations.evolution import ProviderEvolution
    from apps.whatsapp.integrations.protocolos import WhatsAppIndisponivel

    cliente = ClienteHTTPFalso(
        [
            RespostaHTTPFalsa(
                200,
                {"instance": {"state": "open"}},
                content=b'{"instance":{"state":"open"}}',
            )
        ]
    )
    provider = ProviderEvolution(
        url_base="http://evolution:8080",
        nome_instancia="empresa-1",
        chave_api="chave",
        cliente=cliente,
        resolvedor=lambda _host, _porta: {endereco_resolvido},
        hosts_internos_permitidos=frozenset({"evolution"}),
    )

    with pytest.raises(WhatsAppIndisponivel):
        provider.consultar_estado()
    assert cliente.chamadas == []


def test_provider_recusa_http_para_host_externo_antes_da_chamada() -> None:
    """Impede HTTP direto para host global fora da allowlist gerenciada."""
    from apps.whatsapp.integrations.evolution import ProviderEvolution
    from apps.whatsapp.integrations.protocolos import WhatsAppIndisponivel

    cliente = ClienteHTTPFalso(
        [
            RespostaHTTPFalsa(
                200,
                {"instance": {"state": "open"}},
                content=b'{"instance":{"state":"open"}}',
            )
        ]
    )
    resolucoes: list[tuple[str, int]] = []

    def resolver(host: str, porta: int) -> set[str]:
        resolucoes.append((host, porta))
        return {"93.184.216.34"}

    provider = ProviderEvolution(
        url_base="http://evolution.example.com",
        nome_instancia="empresa-1",
        chave_api="chave",
        cliente=cliente,
        resolvedor=resolver,
        hosts_internos_permitidos=frozenset({"evolution"}),
    )

    with pytest.raises(WhatsAppIndisponivel):
        provider.consultar_estado()
    assert cliente.chamadas == []
    assert resolucoes == []


@pytest.mark.parametrize(
    ("url_base", "host_permitido"),
    [
        ("http://127.0.0.1:8080", "127.0.0.1"),
        ("http://[::1]:8080", "::1"),
        ("http://metadata.google.internal:8080", "metadata.google.internal"),
    ],
)
def test_provider_recusa_destino_bloqueado_mesmo_na_allowlist(
    url_base: str, host_permitido: str
) -> None:
    """Mantem metadata e IPs locais bloqueados apesar da allowlist fornecida."""
    from apps.whatsapp.integrations.evolution import ProviderEvolution
    from apps.whatsapp.integrations.protocolos import WhatsAppIndisponivel

    cliente = ClienteHTTPFalso([])
    provider = ProviderEvolution(
        url_base=url_base,
        nome_instancia="empresa-1",
        chave_api="chave",
        cliente=cliente,
        resolvedor=lambda _host, _porta: {"127.0.0.1"},
        hosts_internos_permitidos=frozenset({host_permitido}),
    )

    with pytest.raises(WhatsAppIndisponivel):
        provider.consultar_estado()
    assert cliente.chamadas == []


def test_provider_desabilita_redirects_para_impedir_salto_ssrf() -> None:
    """Nao segue redirecionamento externo para um destino nao validado."""
    from apps.whatsapp.integrations.protocolos import WhatsAppIndisponivel

    provider = _provider(
        RespostaHTTPFalsa(
            302,
            {},
            content=b"{}",
            headers={"Location": "http://127.0.0.1/admin"},
        )
    )

    with pytest.raises(WhatsAppIndisponivel):
        provider.consultar_estado()
    assert provider.cliente.chamadas[0]["allow_redirects"] is False


def test_provider_envia_texto_com_chave_de_idempotencia() -> None:
    """Preserva numero, texto e idempotencia no contrato de envio."""
    provider = _provider(
        RespostaHTTPFalsa(
            201,
            {"key": {"id": "mensagem-123"}},
            content=b'{"key":{"id":"mensagem-123"}}',
        )
    )

    identificador = provider.enviar_texto("69999999999", "Ola", "evento-1")

    assert identificador == "mensagem-123"
    chamada = provider.cliente.chamadas[0]
    assert chamada["metodo"] == "POST"
    assert chamada["json"] == {"number": "69999999999", "text": "Ola"}
    assert chamada["headers"]["apikey"] == "chave-evolution"
    assert chamada["headers"]["Idempotency-Key"] == "evento-1"
    from uuid import UUID

    UUID(chamada["headers"]["X-Correlation-ID"])


def test_provider_classifica_400_como_falha_permanente() -> None:
    """Falha se erro de requisicao do cliente entrar na politica de retry."""
    from apps.whatsapp.integrations.protocolos import RequisicaoWhatsAppInvalida

    provider = _provider(RespostaHTTPFalsa(400, {}, content=b"{}"))

    with pytest.raises(RequisicaoWhatsAppInvalida):
        provider.enviar_texto("69999999999", "Ola", "evento-400")


def test_provider_propaga_correlacao_ao_evolution() -> None:
    """Permite rastrear a chamada Evolution pelo mesmo identificador."""
    from apps.nucleo.middleware.correlacao import (
        definir_correlacao,
        restaurar_correlacao,
    )

    provider = _provider(
        RespostaHTTPFalsa(
            200,
            {"instance": {"state": "open"}},
            content=b'{"instance":{"state":"open"}}',
        )
    )
    token = definir_correlacao("corr-evolution")
    try:
        provider.consultar_estado()
    finally:
        restaurar_correlacao(token)

    assert (
        provider.cliente.chamadas[0]["headers"]["X-Correlation-ID"] == "corr-evolution"
    )
