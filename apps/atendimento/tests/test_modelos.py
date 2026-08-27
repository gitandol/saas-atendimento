"""Testes das invariantes persistidas do atendimento."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.empresas.models import Empresa


@pytest.mark.django_db
def test_contato_e_unico_por_empresa_e_numero_normalizado() -> None:
    """Impede contatos duplicados no tenant sem misturar empresas."""
    from apps.atendimento.models import Contato

    empresa = Empresa.objects.create(nome="Empresa principal")
    externa = Empresa.objects.create(nome="Empresa externa")
    Contato.objects.create(empresa=empresa, nome="Ana", numero_normalizado="5568999")
    Contato.objects.create(empresa=externa, nome="Ana", numero_normalizado="5568999")

    with pytest.raises(IntegrityError), transaction.atomic():
        Contato.objects.create(
            empresa=empresa,
            nome="Ana duplicada",
            numero_normalizado="5568999",
        )


@pytest.mark.django_db
def test_identificador_externo_e_unico_por_empresa_quando_informado() -> None:
    """Evita reprocessar uma mensagem externa e permite saidas ainda sem ID."""
    from apps.atendimento.models import Contato, Conversa, Mensagem

    empresa = Empresa.objects.create(nome="Empresa mensagens")
    contato = Contato.objects.create(
        empresa=empresa, nome="Bia", numero_normalizado="5568888"
    )
    conversa = Conversa.objects.create(empresa=empresa, contato=contato)
    dados = {
        "empresa": empresa,
        "conversa": conversa,
        "direcao": Mensagem.Direcao.ENTRADA,
        "autor": Mensagem.Autor.CLIENTE,
        "texto": "Ola",
        "status": Mensagem.Status.RECEBIDA,
    }
    Mensagem.objects.create(**dados, identificador_externo="wamid-1")
    Mensagem.objects.create(**dados, identificador_externo="")
    Mensagem.objects.create(**dados, identificador_externo="")

    with pytest.raises(IntegrityError), transaction.atomic():
        Mensagem.objects.create(**dados, identificador_externo="wamid-1")


@pytest.mark.django_db
def test_modelos_expoem_estados_e_preservam_exclusao_logica() -> None:
    """Mantem os estados contratuais e o contato excluido no historico."""
    from apps.atendimento.models import Contato, Conversa, Mensagem

    assert set(Conversa.Modo.values) == {"IA", "HUMANO"}
    assert set(Conversa.Estado.values) == {"ABERTA", "FINALIZADA"}
    assert set(Mensagem.Direcao.values) == {"ENTRADA", "SAIDA"}
    assert set(Mensagem.Autor.values) == {"CLIENTE", "IA", "ATENDENTE", "SISTEMA"}
    assert set(Mensagem.Status.values) == {
        "RECEBIDA",
        "PENDENTE",
        "ENVIADA",
        "ENTREGUE",
        "FALHA",
    }
    assert Contato._meta.get_field("excluido_em").null is True


@pytest.mark.django_db
@pytest.mark.parametrize("texto", ["", " " * 4, "x" * 4097])
def test_mensagem_de_saida_recusa_texto_invalido(texto: str) -> None:
    """Bloqueia envio vazio ou acima do limite textual do MVP."""
    from apps.atendimento.models import Contato, Conversa, Mensagem

    empresa = Empresa.objects.create(nome=f"Empresa texto {len(texto)}")
    contato = Contato.objects.create(
        empresa=empresa, nome="Caio", numero_normalizado=f"5568{len(texto)}"
    )
    conversa = Conversa.objects.create(empresa=empresa, contato=contato)
    mensagem = Mensagem(
        empresa=empresa,
        conversa=conversa,
        direcao=Mensagem.Direcao.SAIDA,
        autor=Mensagem.Autor.IA,
        texto=texto,
        status=Mensagem.Status.PENDENTE,
    )

    with pytest.raises(ValidationError):
        mensagem.full_clean()


@pytest.mark.django_db
def test_conversa_recusa_contato_de_outra_empresa_ao_salvar() -> None:
    """Impede persistir uma conversa ligada ao contato de outro tenant."""
    from apps.atendimento.models import Contato, Conversa

    local = Empresa.objects.create(nome="Empresa conversa local")
    externa = Empresa.objects.create(nome="Empresa conversa externa")
    contato_externo = Contato.objects.create(
        empresa=externa,
        nome="Contato externo",
        numero_normalizado="556811111111",
    )

    with pytest.raises(ValidationError):
        Conversa.objects.create(empresa=local, contato=contato_externo)


@pytest.mark.django_db
def test_mensagem_recusa_conversa_de_outra_empresa_ao_salvar() -> None:
    """Impede persistir uma mensagem ligada a conversa de outro tenant."""
    from apps.atendimento.models import Contato, Conversa, Mensagem

    local = Empresa.objects.create(nome="Empresa mensagem local")
    externa = Empresa.objects.create(nome="Empresa mensagem externa")
    contato = Contato.objects.create(
        empresa=externa,
        nome="Contato mensagem",
        numero_normalizado="556822222222",
    )
    conversa = Conversa.objects.create(empresa=externa, contato=contato)

    with pytest.raises(ValidationError):
        Mensagem.objects.create(
            empresa=local,
            conversa=conversa,
            direcao=Mensagem.Direcao.ENTRADA,
            autor=Mensagem.Autor.CLIENTE,
            texto="Tentativa cruzada",
            status=Mensagem.Status.RECEBIDA,
        )


@pytest.mark.django_db
def test_conversa_recusa_ultima_mensagem_de_outro_atendimento() -> None:
    """Impede apontar a ultima mensagem para outra conversa ou empresa."""
    from apps.atendimento.models import Contato, Conversa, Mensagem

    empresa = Empresa.objects.create(nome="Empresa ultima mensagem")
    primeiro_contato = Contato.objects.create(
        empresa=empresa,
        nome="Primeiro",
        numero_normalizado="556833333331",
    )
    segundo_contato = Contato.objects.create(
        empresa=empresa,
        nome="Segundo",
        numero_normalizado="556833333332",
    )
    primeira = Conversa.objects.create(empresa=empresa, contato=primeiro_contato)
    segunda = Conversa.objects.create(empresa=empresa, contato=segundo_contato)
    mensagem = Mensagem.objects.create(
        empresa=empresa,
        conversa=segunda,
        direcao=Mensagem.Direcao.ENTRADA,
        autor=Mensagem.Autor.CLIENTE,
        texto="Outra conversa",
        status=Mensagem.Status.RECEBIDA,
    )
    primeira.ultima_mensagem = mensagem

    with pytest.raises(ValidationError):
        primeira.save()


@pytest.mark.django_db
def test_listagem_nao_expoe_contato_cruzado_inserido_sem_save() -> None:
    """Filtra dados incoerentes mesmo quando bulk_create ignora validacao."""
    from apps.atendimento.models import Contato, Conversa
    from apps.atendimento.services.consultas.listar_conversas import (
        listar_conversas,
    )

    local = Empresa.objects.create(nome="Empresa listagem local")
    externa = Empresa.objects.create(nome="Empresa listagem externa")
    contato_externo = Contato.objects.create(
        empresa=externa,
        nome="Contato vazamento",
        numero_normalizado="556844444444",
    )
    Conversa.objects.bulk_create([Conversa(empresa=local, contato=contato_externo)])

    assert listar_conversas(empresa=local) == []
