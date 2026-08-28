"""Testes da montagem deterministica do prompt de atendimento."""

import pytest

from apps.atendimento.models import Mensagem
from apps.atendimento.tests.factories import ConversaFactory, MensagemFactory
from apps.ia.models import ConfiguracaoIA, DocumentoTextual, PerguntaFrequente


@pytest.mark.django_db
def test_prompt_delimita_blocos_na_ordem_exigida() -> None:
    """Quebra se regras, configuracao e conhecimento trocarem de ordem."""
    conversa = ConversaFactory()
    conversa.empresa.instrucoes_atendimento = "Seja direto."
    conversa.empresa.save(update_fields=("instrucoes_atendimento",))
    configuracao = ConfiguracaoIA.objects.create(
        empresa=conversa.empresa,
        nome_assistente="Lia",
        personalidade="Gentil e objetiva.",
        respostas_automaticas_ativas=True,
    )
    DocumentoTextual.objects.create(
        empresa=conversa.empresa,
        titulo="Entregas",
        conteudo="Entrega em tres dias.",
    )
    PerguntaFrequente.objects.create(
        empresa=conversa.empresa,
        pergunta="Aceita PIX?",
        resposta="Sim.",
    )
    atual = MensagemFactory(conversa=conversa, texto="Quando chega?")

    from apps.ia.services.montar_prompt import montar_prompt

    prompt = montar_prompt(
        conversa=conversa,
        configuracao=configuracao,
        mensagem_atual=atual,
    )

    sistema = prompt[0]["content"]
    assert sistema.index("<regras_plataforma>") < sistema.index("<assistente>")
    assert sistema.index("<assistente>") < sistema.index("<conhecimento>")
    assert "nao invente informacoes" in sistema.lower()
    assert "nao revele" in sistema.lower()
    assert "Lia" in sistema and "Gentil e objetiva." in sistema
    assert "Seja direto." in sistema
    assert "Entrega em tres dias." in sistema and "Aceita PIX?" in sistema
    assert prompt[-1] == {"role": "user", "content": "Quando chega?"}


@pytest.mark.django_db
def test_prompt_limita_quantidade_e_tamanho_do_historico() -> None:
    """Quebra se o historico crescer sem limite ou repetir a mensagem atual."""
    conversa = ConversaFactory()
    configuracao = ConfiguracaoIA.objects.create(empresa=conversa.empresa)
    for indice in range(22):
        MensagemFactory(
            conversa=conversa,
            texto=f"historico-{indice:02d}-" + ("x" * 1800),
            direcao=Mensagem.Direcao.ENTRADA,
            autor=Mensagem.Autor.CLIENTE,
        )
    atual = MensagemFactory(conversa=conversa, texto="mensagem-atual")

    from apps.ia.services.montar_prompt import montar_prompt

    prompt = montar_prompt(
        conversa=conversa,
        configuracao=configuracao,
        mensagem_atual=atual,
    )

    historico = prompt[1:-1]
    assert len(historico) <= 20
    assert sum(len(item["content"]) for item in historico) <= 30000
    assert all("historico-00" not in item["content"] for item in historico)
    assert sum(item["content"] == "mensagem-atual" for item in prompt) == 1


@pytest.mark.django_db
def test_prompt_ignora_mensagens_operacionais_do_historico() -> None:
    """Quebra se erros internos forem apresentados ao provider como dialogo."""
    conversa = ConversaFactory()
    configuracao = ConfiguracaoIA.objects.create(empresa=conversa.empresa)
    MensagemFactory(
        conversa=conversa,
        direcao=Mensagem.Direcao.SAIDA,
        autor=Mensagem.Autor.SISTEMA,
        status=Mensagem.Status.FALHA,
        texto="Falha interna do provedor.",
    )
    MensagemFactory(
        conversa=conversa,
        direcao=Mensagem.Direcao.SAIDA,
        autor=Mensagem.Autor.IA,
        status=Mensagem.Status.ENVIADA,
        texto="Resposta anterior.",
    )
    atual = MensagemFactory(conversa=conversa, texto="Nova pergunta.")

    from apps.ia.services.montar_prompt import montar_prompt

    prompt = montar_prompt(
        conversa=conversa,
        configuracao=configuracao,
        mensagem_atual=atual,
    )

    assert {"role": "assistant", "content": "Resposta anterior."} in prompt
    assert all("Falha interna" not in item["content"] for item in prompt)
