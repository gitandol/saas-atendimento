"""Testes da coordenacao Celery da resposta automatica."""

import pytest

from apps.atendimento.tests.factories import ConversaFactory, MensagemFactory


@pytest.mark.django_db
def test_task_delega_uuids_e_correlacao_ao_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Quebra se a task alterar o contrato de dominio ou nao o executar."""
    conversa = ConversaFactory()
    entrada = MensagemFactory(conversa=conversa)
    chamadas: list[dict[str, object]] = []

    from apps.ia.tasks import responder_conversa as modulo

    monkeypatch.setattr(
        modulo,
        "gerar_resposta_atendimento",
        lambda **kwargs: chamadas.append(kwargs),
    )

    assert modulo.responder_conversa.run(str(conversa.id), str(entrada.id), "corr-task")
    assert chamadas == [
        {
            "conversa_id": conversa.id,
            "mensagem_entrada_id": entrada.id,
            "correlacao": "corr-task",
        }
    ]


def test_task_recusa_uuid_invalido_sem_chamar_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Quebra se payload Celery invalido chegar ao service."""
    from apps.ia.tasks import responder_conversa as modulo

    monkeypatch.setattr(
        modulo,
        "gerar_resposta_atendimento",
        lambda **kwargs: pytest.fail("service nao deveria ser chamado"),
    )

    assert not modulo.responder_conversa.run("invalido", "tambem-invalido", "corr")
