"""Testes dos services transacionais do atendimento."""

import pytest
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from apps.atendimento.models import Conversa, Mensagem
from apps.atendimento.tests.factories import (
    ContatoFactory,
    ConversaFactory,
    EmpresaFactory,
    UsuarioFactory,
)
from apps.empresas.models import MembroEmpresa


@pytest.mark.django_db
def test_obter_ou_criar_contato_normaliza_e_nao_duplica() -> None:
    """Normaliza o telefone e retorna a mesma identidade no tenant."""
    from apps.atendimento.services.contatos import obter_ou_criar_contato
    from apps.auditoria.models import EventoAuditoria

    empresa = EmpresaFactory()
    ator = UsuarioFactory()
    primeiro = obter_ou_criar_contato(
        empresa=empresa,
        numero_telefone="+55 (68) 9999-0000",
        nome="Ana",
        ator=ator,
        origem="teste",
        correlacao="contato-1",
    )
    segundo = obter_ou_criar_contato(
        empresa=empresa,
        numero_telefone="556899990000",
        nome="Nome ignorado",
        ator=ator,
        origem="teste",
        correlacao="contato-2",
    )

    assert primeiro.id == segundo.id
    assert segundo.numero_normalizado == "556899990000"
    assert EventoAuditoria.objects.filter(correlacao="contato-1").count() == 1
    assert not EventoAuditoria.objects.filter(correlacao="contato-2").exists()


@pytest.mark.django_db
def test_conversa_e_aberta_finalizada_e_reaberta_explicitamente() -> None:
    """Reutiliza o historico finalizado apenas pelo service de abertura."""
    from apps.atendimento.services.assumir_conversa import assumir_conversa
    from apps.atendimento.services.conversas import obter_ou_abrir_conversa
    from apps.atendimento.services.finalizar_conversa import finalizar_conversa

    contato = ContatoFactory()
    ator = UsuarioFactory()
    MembroEmpresa.objects.create(
        empresa=contato.empresa,
        usuario=ator,
        papel=MembroEmpresa.Papel.ATENDENTE,
    )
    aberta = obter_ou_abrir_conversa(
        empresa=contato.empresa,
        contato_id=contato.id,
        ator=ator,
        origem="teste",
        correlacao="abrir",
    )
    assumida = assumir_conversa(
        empresa=contato.empresa,
        conversa_id=aberta.id,
        ator=ator,
        versao=aberta.versao,
        justificativa="",
        origem="teste",
        correlacao="assumir",
    )
    finalizada = finalizar_conversa(
        empresa=contato.empresa,
        conversa_id=aberta.id,
        ator=ator,
        versao=assumida.versao,
        justificativa="",
        origem="teste",
        correlacao="finalizar",
    )
    reaberta = obter_ou_abrir_conversa(
        empresa=contato.empresa,
        contato_id=contato.id,
        ator=ator,
        origem="webhook",
        correlacao="reabrir",
    )

    assert aberta.id == reaberta.id
    assert finalizada.estado == Conversa.Estado.FINALIZADA
    assert reaberta.estado == Conversa.Estado.ABERTA
    assert reaberta.modo == Conversa.Modo.IA
    assert reaberta.atendente_id is None
    assert reaberta.versao == finalizada.versao + 1
    assert reaberta.finalizada_em is None


@pytest.mark.django_db
def test_registrar_entrada_atualiza_conversa_contato_e_e_idempotente() -> None:
    """Atualiza agregados uma vez e nao duplica o identificador externo."""
    from apps.atendimento.models import Contato
    from apps.atendimento.services.mensagens import registrar_mensagem
    from apps.auditoria.models import EventoAuditoria

    conversa = ConversaFactory()
    ator = UsuarioFactory()
    argumentos = {
        "empresa": conversa.empresa,
        "conversa_id": conversa.id,
        "direcao": Mensagem.Direcao.ENTRADA,
        "autor": Mensagem.Autor.CLIENTE,
        "texto": "Preciso de ajuda",
        "identificador_externo": "wamid-entrada-1",
        "status": Mensagem.Status.RECEBIDA,
        "ator": ator,
        "origem": "webhook",
        "correlacao": "mensagem-1",
    }

    primeira = registrar_mensagem(**argumentos)
    repetida = registrar_mensagem(**argumentos)

    conversa.refresh_from_db()
    contato = Contato.objects.get(pk=conversa.contato_id)
    assert primeira.id == repetida.id
    assert Mensagem.objects.filter(empresa=conversa.empresa).count() == 1
    assert conversa.ultima_mensagem_id == primeira.id
    assert conversa.contagem_nao_lida == 1
    assert conversa.contagem_nao_respondida == 1
    assert contato.primeiro_contato_em == primeira.criado_em
    assert contato.ultimo_contato_em == primeira.criado_em
    assert EventoAuditoria.objects.filter(
        empresa=conversa.empresa,
        objeto_id=str(primeira.id),
    ).exists()


@pytest.mark.django_db
def test_registrar_saida_zera_nao_respondidas_e_preserva_nao_lidas() -> None:
    """Uma resposta resolve as pendencias sem fingir que as entradas foram lidas."""
    from apps.atendimento.services.mensagens import registrar_mensagem

    conversa = ConversaFactory(contagem_nao_lida=3, contagem_nao_respondida=3)
    ator = UsuarioFactory()
    conversa.modo = Conversa.Modo.HUMANO
    conversa.atendente = ator
    conversa.save(update_fields=("modo", "atendente"))
    mensagem = registrar_mensagem(
        empresa=conversa.empresa,
        conversa_id=conversa.id,
        direcao=Mensagem.Direcao.SAIDA,
        autor=Mensagem.Autor.ATENDENTE,
        texto="Vamos ajudar",
        identificador_externo="",
        status=Mensagem.Status.PENDENTE,
        ator=ator,
        origem="api",
        correlacao="saida-1",
    )

    conversa.refresh_from_db()
    assert conversa.ultima_mensagem_id == mensagem.id
    assert conversa.contagem_nao_lida == 3
    assert conversa.contagem_nao_respondida == 0


@pytest.mark.django_db
def test_saida_operacional_nao_zera_mensagens_pendentes_de_resposta() -> None:
    """Uma falha interna nao conta como resposta entregue ao cliente."""
    from apps.atendimento.services.mensagens import registrar_mensagem

    conversa = ConversaFactory(contagem_nao_lida=2, contagem_nao_respondida=2)
    registrar_mensagem(
        empresa=conversa.empresa,
        conversa_id=conversa.id,
        direcao=Mensagem.Direcao.SAIDA,
        autor=Mensagem.Autor.SISTEMA,
        texto="Falha operacional",
        identificador_externo="falha-contador-1",
        status=Mensagem.Status.FALHA,
        ator=None,
        origem="task_ia",
        correlacao="falha-contador-1",
    )

    conversa.refresh_from_db()
    assert conversa.contagem_nao_respondida == 2


@pytest.mark.django_db
def test_registrar_saida_reforca_condutor_atual_da_conversa() -> None:
    """Recusa IA em modo humano e atendente sem responsabilidade."""
    from django.core.exceptions import PermissionDenied

    from apps.atendimento.services.mensagens import registrar_mensagem

    conversa = ConversaFactory()
    responsavel = UsuarioFactory()
    outro = UsuarioFactory()
    conversa.modo = Conversa.Modo.HUMANO
    conversa.atendente = responsavel
    conversa.save(update_fields=("modo", "atendente"))

    with pytest.raises(ValidationError):
        registrar_mensagem(
            empresa=conversa.empresa,
            conversa_id=conversa.id,
            direcao=Mensagem.Direcao.SAIDA,
            autor=Mensagem.Autor.IA,
            texto="IA bloqueada",
            identificador_externo="",
            status=Mensagem.Status.PENDENTE,
            ator=None,
            origem="task_ia",
            correlacao="ia-bloqueada",
        )
    with pytest.raises(PermissionDenied):
        registrar_mensagem(
            empresa=conversa.empresa,
            conversa_id=conversa.id,
            direcao=Mensagem.Direcao.SAIDA,
            autor=Mensagem.Autor.ATENDENTE,
            texto="Terceiro bloqueado",
            identificador_externo="",
            status=Mensagem.Status.PENDENTE,
            ator=outro,
            origem="api",
            correlacao="terceiro-bloqueado",
        )


@pytest.mark.django_db
def test_services_recusam_objetos_de_outra_empresa() -> None:
    """Nao revela nem altera contato ou conversa de outro tenant."""
    from apps.atendimento.services.conversas import obter_ou_abrir_conversa
    from apps.atendimento.services.mensagens import registrar_mensagem

    contato = ContatoFactory()
    conversa = ConversaFactory()
    local = EmpresaFactory()
    ator = UsuarioFactory()

    with pytest.raises(ObjectDoesNotExist):
        obter_ou_abrir_conversa(
            empresa=local,
            contato_id=contato.id,
            ator=ator,
            origem="teste",
            correlacao="isolamento-contato",
        )
    with pytest.raises(ObjectDoesNotExist):
        registrar_mensagem(
            empresa=local,
            conversa_id=conversa.id,
            direcao=Mensagem.Direcao.ENTRADA,
            autor=Mensagem.Autor.CLIENTE,
            texto="Ataque",
            identificador_externo="ataque-1",
            status=Mensagem.Status.RECEBIDA,
            ator=ator,
            origem="teste",
            correlacao="isolamento-mensagem",
        )


@pytest.mark.django_db
@pytest.mark.parametrize("texto", ["", "   ", "x" * 4097])
def test_registrar_saida_recusa_texto_invalido(texto: str) -> None:
    """Aplica o limite do MVP antes de persistir uma saida."""
    from apps.atendimento.services.mensagens import registrar_mensagem

    conversa = ConversaFactory()
    with pytest.raises(ValidationError):
        registrar_mensagem(
            empresa=conversa.empresa,
            conversa_id=conversa.id,
            direcao=Mensagem.Direcao.SAIDA,
            autor=Mensagem.Autor.IA,
            texto=texto,
            identificador_externo="",
            status=Mensagem.Status.PENDENTE,
            ator=None,
            origem="celery",
            correlacao="saida-invalida",
        )


@pytest.mark.django_db
def test_obter_contato_excluido_restaura_a_mesma_identidade() -> None:
    """Reativa o contato sem duplicar nem perder seu historico."""
    from django.utils import timezone

    from apps.atendimento.models import Contato
    from apps.atendimento.services.contatos import obter_ou_criar_contato
    from apps.auditoria.models import EventoAuditoria

    contato = ContatoFactory()
    Contato.objects.filter(pk=contato.id).update(excluido_em=timezone.now())
    ator = UsuarioFactory()

    restaurado = obter_ou_criar_contato(
        empresa=contato.empresa,
        numero_telefone=contato.numero_normalizado,
        nome="Nome reativado",
        ator=ator,
        origem="webhook",
        correlacao="restaurar-contato",
    )

    contato.refresh_from_db()
    assert restaurado.id == contato.id
    assert contato.excluido_em is None
    assert EventoAuditoria.objects.filter(
        objeto_id=str(contato.id),
        acao=EventoAuditoria.Acao.RESTAURACAO,
        correlacao="restaurar-contato",
    ).exists()


@pytest.mark.django_db
def test_obter_conversa_prioriza_a_aberta_sobre_finalizada_recente() -> None:
    """Evita reabrir outra conversa quando ja existe atendimento aberto."""
    from datetime import timedelta

    from django.utils import timezone

    from apps.atendimento.services.conversas import obter_ou_abrir_conversa

    contato = ContatoFactory()
    aberta = ConversaFactory(
        empresa=contato.empresa,
        contato=contato,
        estado=Conversa.Estado.ABERTA,
    )
    finalizada = ConversaFactory(
        empresa=contato.empresa,
        contato=contato,
        estado=Conversa.Estado.FINALIZADA,
        finalizada_em=timezone.now(),
    )
    agora = timezone.now()
    Conversa.objects.filter(pk=aberta.id).update(
        atualizado_em=agora - timedelta(minutes=1)
    )
    Conversa.objects.filter(pk=finalizada.id).update(atualizado_em=agora)

    resultado = obter_ou_abrir_conversa(
        empresa=contato.empresa,
        contato_id=contato.id,
        ator=UsuarioFactory(),
        origem="webhook",
        correlacao="manter-aberta",
    )

    finalizada.refresh_from_db()
    assert resultado.id == aberta.id
    assert finalizada.estado == Conversa.Estado.FINALIZADA


@pytest.mark.django_db
def test_falha_na_auditoria_desfaz_mensagem_e_agregados() -> None:
    """Reverte toda a operação quando o registro auditável falha."""
    from unittest.mock import patch

    from apps.atendimento.models import Contato
    from apps.atendimento.services.mensagens import registrar_mensagem

    conversa = ConversaFactory()

    with (
        patch(
            "apps.atendimento.services.mensagens.registrar_alteracao",
            side_effect=RuntimeError("falha auditavel"),
        ),
        pytest.raises(RuntimeError, match="falha auditavel"),
    ):
        registrar_mensagem(
            empresa=conversa.empresa,
            conversa_id=conversa.id,
            direcao=Mensagem.Direcao.ENTRADA,
            autor=Mensagem.Autor.CLIENTE,
            texto="Deve sofrer rollback",
            identificador_externo="rollback-1",
            status=Mensagem.Status.RECEBIDA,
            ator=UsuarioFactory(),
            origem="webhook",
            correlacao="rollback-mensagem",
        )

    conversa.refresh_from_db()
    contato = Contato.objects.get(pk=conversa.contato_id)
    assert not Mensagem.objects.filter(identificador_externo="rollback-1").exists()
    assert conversa.ultima_mensagem_id is None
    assert conversa.contagem_nao_lida == 0
    assert contato.primeiro_contato_em is None
    assert contato.ultimo_contato_em is None


@pytest.mark.django_db
def test_marcar_como_lida_bloqueia_apenas_a_conversa(monkeypatch) -> None:
    """Evita FOR UPDATE nos relacionamentos opcionais carregados por LEFT JOIN."""
    from django.db.models.query import QuerySet

    from apps.atendimento.services.conversas import marcar_como_lida

    conversa = ConversaFactory(contagem_nao_lida=2)
    ator = UsuarioFactory()
    MembroEmpresa.objects.create(
        empresa=conversa.empresa,
        usuario=ator,
        papel=MembroEmpresa.Papel.ATENDENTE,
    )
    original = QuerySet.select_for_update
    argumentos: list[dict] = []

    def registrar_argumentos(self, *args, **kwargs):
        argumentos.append(kwargs)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(QuerySet, "select_for_update", registrar_argumentos)

    marcar_como_lida(
        empresa=conversa.empresa,
        conversa_id=conversa.id,
        ator=ator,
        correlacao="teste-bloqueio-leitura",
    )

    assert {"of": ("self",)} in argumentos
