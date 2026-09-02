"""Testes da orquestracao de respostas automaticas da IA."""

import logging
from dataclasses import dataclass

import pytest

from apps.atendimento.models import Conversa, Mensagem
from apps.atendimento.tests.factories import ConversaFactory, MensagemFactory
from apps.ia.integrations.protocolos import (
    CredencialIAInvalida,
    IAIndisponivel,
    LimiteIAExcedido,
    RespostaIA,
)
from apps.ia.models import ConfiguracaoIA


@dataclass
class ProviderFalso:
    """Controla a unica fronteira externa exercitada pelos testes."""

    resultado: RespostaIA | Exception
    chamadas: int = 0
    prompt: list[dict[str, str]] | None = None

    def gerar_resposta(
        self, mensagens: list[dict[str, str]], modelo: str
    ) -> RespostaIA:
        """Registra a chamada e entrega o resultado configurado."""
        self.chamadas += 1
        self.prompt = mensagens
        if isinstance(self.resultado, Exception):
            raise self.resultado
        return self.resultado


def _cenario_ativo() -> tuple[Conversa, Mensagem, ConfiguracaoIA]:
    """Cria uma entrada elegivel com configuracao operacional."""
    conversa = ConversaFactory()
    entrada = MensagemFactory(conversa=conversa, texto="Qual e o prazo?")
    configuracao = ConfiguracaoIA.objects.create(
        empresa=conversa.empresa,
        modelo="gpt-teste",
        respostas_automaticas_ativas=True,
        chave_api_criptografada="credencial-cifrada",
    )
    return conversa, entrada, configuracao


@pytest.mark.django_db
@pytest.mark.parametrize("bloqueio", ["humano", "finalizada", "inativa", "invalida"])
def test_estado_inelegivel_nao_chama_provider(
    monkeypatch: pytest.MonkeyPatch, bloqueio: str
) -> None:
    """Quebra se qualquer bloqueio operacional deixar a IA responder."""
    conversa, entrada, configuracao = _cenario_ativo()
    if bloqueio == "humano":
        conversa.modo = Conversa.Modo.HUMANO
        conversa.save(update_fields=("modo",))
    elif bloqueio == "finalizada":
        conversa.estado = Conversa.Estado.FINALIZADA
        conversa.save(update_fields=("estado",))
    elif bloqueio == "inativa":
        configuracao.respostas_automaticas_ativas = False
        configuracao.save(update_fields=("respostas_automaticas_ativas",))
    else:
        configuracao.modelo = ""
        configuracao.save(update_fields=("modelo",))

    from apps.ia.services import gerar_resposta_atendimento as modulo

    monkeypatch.setattr(
        modulo,
        "obter_provider",
        lambda empresa: pytest.fail("provider nao deveria ser chamado"),
    )

    with pytest.raises(modulo.RespostaAutomaticaNaoPermitida):
        modulo.gerar_resposta_atendimento(
            conversa_id=conversa.id,
            mensagem_entrada_id=entrada.id,
            correlacao="corr-bloqueio",
        )


@pytest.mark.django_db
def test_sucesso_persiste_saida_pendente_metricas_e_agenda_apos_commit(
    monkeypatch: pytest.MonkeyPatch,
    django_capture_on_commit_callbacks,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Quebra se sucesso perder estado, metricas ou despacho pos-commit."""
    conversa, entrada, _ = _cenario_ativo()
    provider = ProviderFalso(
        RespostaIA(
            texto="O prazo e de tres dias.",
            modelo="gpt-teste-2026",
            tokens_entrada=21,
            tokens_saida=7,
        )
    )
    agendamentos: list[tuple[str, str]] = []

    from apps.ia.services import gerar_resposta_atendimento as modulo

    monkeypatch.setattr(modulo, "obter_provider", lambda empresa: provider)
    monkeypatch.setattr(
        modulo,
        "_solicitar_envio",
        lambda mensagem_id, correlacao: agendamentos.append((mensagem_id, correlacao)),
    )

    with (
        caplog.at_level(logging.INFO),
        django_capture_on_commit_callbacks(execute=True),
    ):
        mensagem = modulo.gerar_resposta_atendimento(
            conversa_id=conversa.id,
            mensagem_entrada_id=entrada.id,
            correlacao="corr-sucesso",
        )

    assert mensagem.autor == Mensagem.Autor.IA
    assert mensagem.direcao == Mensagem.Direcao.SAIDA
    assert mensagem.status == Mensagem.Status.PENDENTE
    assert mensagem.texto == "O prazo e de tres dias."
    assert mensagem.identificador_externo == f"ia:{entrada.id}"
    assert agendamentos == [(str(mensagem.id), "corr-sucesso")]
    registro = next(
        registro for registro in caplog.records if registro.msg == "resposta_ia_gerada"
    )
    assert registro.modelo == "gpt-teste-2026"
    assert registro.tokens_entrada == 21
    assert registro.tokens_saida == 7
    assert "Qual e o prazo?" not in caplog.text
    assert provider.prompt is not None


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("texto_provider", "texto_whatsapp"),
    [
        ("O prazo e de **tres dias**.", "O prazo e de *tres dias*."),
        ("Oferta ***especial***.", "Oferta *especial*."),
        ("Calcule 2 ** 3.", "Calcule 2 ** 3."),
    ],
)
def test_sucesso_converte_negrito_markdown_para_formato_do_whatsapp(
    monkeypatch: pytest.MonkeyPatch,
    texto_provider: str,
    texto_whatsapp: str,
) -> None:
    """Quebra se a resposta enviada mantiver o segundo asterisco visivel."""
    conversa, entrada, _ = _cenario_ativo()
    provider = ProviderFalso(
        RespostaIA(
            texto=texto_provider,
            modelo="gpt-teste",
            tokens_entrada=5,
            tokens_saida=6,
        )
    )

    from apps.ia.services import gerar_resposta_atendimento as modulo

    monkeypatch.setattr(modulo, "obter_provider", lambda empresa: provider)
    monkeypatch.setattr(modulo, "_solicitar_envio", lambda *args: None)

    mensagem = modulo.gerar_resposta_atendimento(
        conversa_id=conversa.id,
        mensagem_entrada_id=entrada.id,
        correlacao="corr-negrito-whatsapp",
    )

    assert mensagem.texto == texto_whatsapp


@pytest.mark.django_db
def test_modo_e_rechecado_depois_da_chamada_externa(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Quebra se a IA persistir depois de uma transferencia concorrente."""
    conversa, entrada, _ = _cenario_ativo()

    class ProviderQueTransfere:
        """Simula intervencao humana enquanto o provider esta em andamento."""

        def gerar_resposta(
            self, mensagens: list[dict[str, str]], modelo: str
        ) -> RespostaIA:
            """Transfere a conversa antes de devolver o texto."""
            Conversa.objects.filter(pk=conversa.id).update(modo=Conversa.Modo.HUMANO)
            return RespostaIA("Resposta tardia.", modelo, 3, 2)

    from apps.ia.services import gerar_resposta_atendimento as modulo

    monkeypatch.setattr(
        modulo, "obter_provider", lambda empresa: ProviderQueTransfere()
    )

    with pytest.raises(modulo.RespostaAutomaticaNaoPermitida):
        modulo.gerar_resposta_atendimento(
            conversa_id=conversa.id,
            mensagem_entrada_id=entrada.id,
            correlacao="corr-transferencia",
        )

    assert not Mensagem.objects.filter(
        conversa=conversa, autor=Mensagem.Autor.IA
    ).exists()


@pytest.mark.django_db
def test_repeticao_da_mesma_entrada_retorna_uma_unica_saida(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Quebra se duas execucoes puderem criar respostas automaticas duplicadas."""
    conversa, entrada, _ = _cenario_ativo()
    provider = ProviderFalso(RespostaIA("Resposta unica.", "gpt-teste", 2, 2))

    from apps.ia.services import gerar_resposta_atendimento as modulo

    monkeypatch.setattr(modulo, "obter_provider", lambda empresa: provider)
    monkeypatch.setattr(modulo, "_solicitar_envio", lambda *args: None)

    primeira = modulo.gerar_resposta_atendimento(
        conversa_id=conversa.id,
        mensagem_entrada_id=entrada.id,
        correlacao="corr-1",
    )
    segunda = modulo.gerar_resposta_atendimento(
        conversa_id=conversa.id,
        mensagem_entrada_id=entrada.id,
        correlacao="corr-2",
    )

    assert primeira.id == segunda.id
    assert provider.chamadas == 1
    assert (
        Mensagem.objects.filter(conversa=conversa, autor=Mensagem.Autor.IA).count() == 1
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "resultado",
    [
        IAIndisponivel("timeout externo"),
        LimiteIAExcedido("limite externo"),
        CredencialIAInvalida("credencial secreta recusada"),
        RespostaIA("   ", "gpt-teste", 1, 0),
        RespostaIA("x" * 4097, "gpt-teste", 1, 4097),
    ],
)
def test_falha_vira_estado_operacional_sem_agendar_envio(
    monkeypatch: pytest.MonkeyPatch,
    django_capture_on_commit_callbacks,
    resultado: RespostaIA | Exception,
) -> None:
    """Quebra se uma falha externa for apresentada como resposta ao cliente."""
    conversa, entrada, _ = _cenario_ativo()
    provider = ProviderFalso(resultado)
    agendamentos: list[str] = []

    from apps.ia.services import gerar_resposta_atendimento as modulo

    monkeypatch.setattr(modulo, "obter_provider", lambda empresa: provider)
    monkeypatch.setattr(
        modulo,
        "_solicitar_envio",
        lambda mensagem_id, correlacao: agendamentos.append(mensagem_id),
    )

    with django_capture_on_commit_callbacks(execute=True):
        mensagem = modulo.gerar_resposta_atendimento(
            conversa_id=conversa.id,
            mensagem_entrada_id=entrada.id,
            correlacao="corr-falha",
        )

    assert mensagem.autor == Mensagem.Autor.SISTEMA
    assert mensagem.status == Mensagem.Status.FALHA
    assert mensagem.identificador_externo == f"ia-falha:{entrada.id}"
    assert mensagem.erro_sanitizado
    assert "credencial secreta" not in mensagem.texto
    assert agendamentos == []
    assert not Mensagem.objects.filter(
        conversa=conversa, autor=Mensagem.Autor.IA
    ).exists()


@pytest.mark.django_db
def test_falha_operacional_permite_tentativa_posterior_bem_sucedida(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Quebra se o estado recuperavel bloquear a proxima tentativa da entrada."""
    conversa, entrada, _ = _cenario_ativo()
    resultados = iter(
        (
            ProviderFalso(IAIndisponivel("timeout")),
            ProviderFalso(RespostaIA("Resposta recuperada.", "gpt-teste", 4, 2)),
        )
    )

    from apps.ia.services import gerar_resposta_atendimento as modulo

    monkeypatch.setattr(modulo, "obter_provider", lambda empresa: next(resultados))
    monkeypatch.setattr(modulo, "_solicitar_envio", lambda *args: None)

    falha = modulo.gerar_resposta_atendimento(
        conversa_id=conversa.id,
        mensagem_entrada_id=entrada.id,
        correlacao="corr-falha",
    )
    sucesso = modulo.gerar_resposta_atendimento(
        conversa_id=conversa.id,
        mensagem_entrada_id=entrada.id,
        correlacao="corr-recuperada",
    )

    assert falha.autor == Mensagem.Autor.SISTEMA
    assert sucesso.autor == Mensagem.Autor.IA
    assert (
        Mensagem.objects.filter(conversa=conversa, autor=Mensagem.Autor.IA).count() == 1
    )


@pytest.mark.django_db
def test_interleaving_antes_da_persistencia_mantem_uma_saida(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Quebra se duas execucoes na janela externa persistirem saidas distintas."""
    conversa, entrada, _ = _cenario_ativo()
    resposta_interna = ProviderFalso(
        RespostaIA("Resposta vencedora.", "gpt-teste", 3, 2)
    )

    from apps.ia.services import gerar_resposta_atendimento as modulo

    class ProviderIntercalado:
        """Executa uma segunda geracao antes da primeira persistir."""

        def gerar_resposta(
            self, mensagens: list[dict[str, str]], modelo: str
        ) -> RespostaIA:
            """Faz a execucao concorrente vencer a janela de persistencia."""
            monkeypatch.setattr(
                modulo, "obter_provider", lambda empresa: resposta_interna
            )
            modulo.gerar_resposta_atendimento(
                conversa_id=conversa.id,
                mensagem_entrada_id=entrada.id,
                correlacao="corr-interna",
            )
            return RespostaIA("Resposta atrasada.", modelo, 5, 2)

    monkeypatch.setattr(modulo, "obter_provider", lambda empresa: ProviderIntercalado())
    monkeypatch.setattr(modulo, "_solicitar_envio", lambda *args: None)

    resultado = modulo.gerar_resposta_atendimento(
        conversa_id=conversa.id,
        mensagem_entrada_id=entrada.id,
        correlacao="corr-externa",
    )

    assert resultado.texto == "Resposta vencedora."
    assert (
        Mensagem.objects.filter(conversa=conversa, autor=Mensagem.Autor.IA).count() == 1
    )
