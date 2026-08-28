"""Testes das transicoes entre IA e atendimento humano."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.db import close_old_connections, connection

from apps.atendimento.models import Conversa
from apps.atendimento.tests.factories import (
    ConversaFactory,
    EmpresaFactory,
    UsuarioFactory,
)
from apps.empresas.models import MembroEmpresa


def _membro(empresa, *, papel=MembroEmpresa.Papel.ATENDENTE):
    """Cria um membro ativo com o papel solicitado."""
    usuario = UsuarioFactory()
    MembroEmpresa.objects.create(empresa=empresa, usuario=usuario, papel=papel)
    return usuario


@pytest.mark.django_db
def test_assumir_conversa_aberta_da_ia_define_responsavel_e_audita() -> None:
    """Falha se assumir nao trocar modo, responsavel, versao e historico."""
    from apps.atendimento.services.assumir_conversa import assumir_conversa
    from apps.auditoria.models import EventoAuditoria

    conversa = ConversaFactory()
    ator = _membro(conversa.empresa)
    resultado = assumir_conversa(
        empresa=conversa.empresa,
        conversa_id=conversa.id,
        ator=ator,
        versao=conversa.versao,
        justificativa="Cliente pediu uma pessoa",
        origem="api_transferencia",
        correlacao="assumir-1",
    )

    conversa.refresh_from_db()
    evento = EventoAuditoria.objects.get(correlacao="assumir-1")
    assert resultado.modo == Conversa.Modo.HUMANO
    assert conversa.atendente_id == ator.id
    assert conversa.versao == 2
    assert evento.ator_id == ator.id
    assert evento.origem == "api_transferencia"
    assert evento.justificativa == "Cliente pediu uma pessoa"
    assert evento.revisao.snapshot["versao"] == 2


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("estado", "modo"),
    [
        (Conversa.Estado.FINALIZADA, Conversa.Modo.IA),
        (Conversa.Estado.ABERTA, Conversa.Modo.HUMANO),
    ],
)
def test_assumir_recusa_transicoes_invalidas(estado: str, modo: str) -> None:
    """Falha se uma conversa fora de IA/ABERTA puder ser assumida."""
    from apps.atendimento.services.assumir_conversa import (
        ConflitoTransicaoConversa,
        assumir_conversa,
    )

    conversa = ConversaFactory(estado=estado, modo=modo)
    ator = _membro(conversa.empresa)
    with pytest.raises(ConflitoTransicaoConversa):
        assumir_conversa(
            empresa=conversa.empresa,
            conversa_id=conversa.id,
            ator=ator,
            versao=conversa.versao,
            justificativa="",
            origem="teste",
            correlacao="assumir-invalida",
        )


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason="select_for_update concorrente exige PostgreSQL",
)
def test_dois_atendentes_assumem_com_mesma_versao_e_apenas_um_vence() -> None:
    """Falha se concorrencia permitir dois vencedores para a mesma versao."""
    from apps.atendimento.services.assumir_conversa import (
        ConflitoTransicaoConversa,
        assumir_conversa,
    )

    conversa = ConversaFactory()
    atores = [_membro(conversa.empresa), _membro(conversa.empresa)]

    def tentar(ator_id):
        """Executa a disputa em uma conexao de banco independente."""
        close_old_connections()
        try:
            empresa = EmpresaFactory._meta.model.objects.get(pk=conversa.empresa_id)
            ator = UsuarioFactory._meta.model.objects.get(pk=ator_id)
            return assumir_conversa(
                empresa=empresa,
                conversa_id=conversa.id,
                ator=ator,
                versao=1,
                justificativa="",
                origem="teste_concorrencia",
                correlacao=f"corr-{ator_id}",
            ).atendente_id
        except ConflitoTransicaoConversa:
            return None
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        resultados = list(executor.map(tentar, [ator.id for ator in atores]))

    conversa.refresh_from_db()
    assert sum(resultado is not None for resultado in resultados) == 1
    assert conversa.atendente_id in {ator.id for ator in atores}
    assert conversa.versao == 2


@pytest.mark.django_db
def test_devolver_exige_responsavel_ou_administrador_e_limpa_atendente() -> None:
    """Falha se terceiro devolver ou se a IA conservar um responsavel humano."""
    from apps.atendimento.services.devolver_para_ia import devolver_para_ia

    conversa = ConversaFactory()
    responsavel = _membro(conversa.empresa)
    terceiro = _membro(conversa.empresa)
    conversa.modo = Conversa.Modo.HUMANO
    conversa.atendente = responsavel
    conversa.save(update_fields=("modo", "atendente"))

    with pytest.raises(PermissionDenied):
        devolver_para_ia(
            empresa=conversa.empresa,
            conversa_id=conversa.id,
            ator=terceiro,
            versao=conversa.versao,
            justificativa="",
            origem="teste",
            correlacao="devolver-negada",
        )

    administrador = _membro(conversa.empresa, papel=MembroEmpresa.Papel.ADMINISTRADOR)
    resultado = devolver_para_ia(
        empresa=conversa.empresa,
        conversa_id=conversa.id,
        ator=administrador,
        versao=conversa.versao,
        justificativa="Fim da intervencao",
        origem="teste",
        correlacao="devolver-admin",
    )
    assert resultado.modo == Conversa.Modo.IA
    assert resultado.atendente_id is None


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("acao", "estado", "modo"),
    [
        ("devolver", Conversa.Estado.ABERTA, Conversa.Modo.IA),
        ("devolver", Conversa.Estado.FINALIZADA, Conversa.Modo.HUMANO),
        ("finalizar", Conversa.Estado.FINALIZADA, Conversa.Modo.IA),
        ("reabrir", Conversa.Estado.ABERTA, Conversa.Modo.IA),
    ],
)
def test_demais_transicoes_recusam_estado_ou_modo_incompativel(
    acao: str, estado: str, modo: str
) -> None:
    """Falha se devolver, finalizar ou reabrir aceitarem origem invalida."""
    from apps.atendimento.services.devolver_para_ia import devolver_para_ia
    from apps.atendimento.services.finalizar_conversa import finalizar_conversa
    from apps.atendimento.services.reabrir_conversa import reabrir_conversa
    from apps.atendimento.services.transicoes_conversa import (
        ConflitoTransicaoConversa,
    )

    conversa = ConversaFactory(estado=estado, modo=modo)
    ator = _membro(conversa.empresa)
    if modo == Conversa.Modo.HUMANO:
        conversa.atendente = ator
        conversa.save(update_fields=("atendente",))
    servicos = {
        "devolver": devolver_para_ia,
        "finalizar": finalizar_conversa,
        "reabrir": reabrir_conversa,
    }
    with pytest.raises(ConflitoTransicaoConversa):
        servicos[acao](
            empresa=conversa.empresa,
            conversa_id=conversa.id,
            ator=ator,
            versao=conversa.versao,
            justificativa="",
            origem="teste",
            correlacao=f"{acao}-invalida",
        )


@pytest.mark.django_db
def test_finalizar_e_reabrir_exigem_transicoes_explicitas() -> None:
    """Falha se finalizar/reabrir perder modo, responsavel ou versao."""
    from apps.atendimento.services.finalizar_conversa import finalizar_conversa
    from apps.atendimento.services.reabrir_conversa import reabrir_conversa

    conversa = ConversaFactory()
    ator = _membro(conversa.empresa)
    finalizada = finalizar_conversa(
        empresa=conversa.empresa,
        conversa_id=conversa.id,
        ator=ator,
        versao=conversa.versao,
        justificativa="Resolvido",
        origem="teste",
        correlacao="finalizar-1",
    )
    assert finalizada.estado == Conversa.Estado.FINALIZADA
    assert finalizada.finalizada_em is not None

    reaberta = reabrir_conversa(
        empresa=conversa.empresa,
        conversa_id=conversa.id,
        ator=ator,
        versao=finalizada.versao,
        modo=Conversa.Modo.HUMANO,
        justificativa="Cliente retornou",
        origem="teste",
        correlacao="reabrir-1",
    )
    assert reaberta.estado == Conversa.Estado.ABERTA
    assert reaberta.modo == Conversa.Modo.HUMANO
    assert reaberta.atendente_id == ator.id
    assert reaberta.finalizada_em is None

    with pytest.raises(ValidationError):
        reabrir_conversa(
            empresa=conversa.empresa,
            conversa_id=conversa.id,
            ator=ator,
            versao=reaberta.versao,
            modo="DESCONHECIDO",
            justificativa="",
            origem="teste",
            correlacao="reabrir-invalida",
        )


@pytest.mark.django_db
def test_transferencia_isola_empresa() -> None:
    """Falha se um identificador de outro tenant puder ser transferido."""
    from apps.atendimento.services.assumir_conversa import assumir_conversa

    conversa = ConversaFactory()
    outra_empresa = EmpresaFactory()
    ator = _membro(outra_empresa)
    with pytest.raises(ObjectDoesNotExist):
        assumir_conversa(
            empresa=outra_empresa,
            conversa_id=conversa.id,
            ator=ator,
            versao=conversa.versao,
            justificativa="",
            origem="teste",
            correlacao="isolamento",
        )


@pytest.mark.django_db
def test_restauracao_preserva_invariantes_e_incrementa_versao() -> None:
    """Falha se restaurar atendente quebrar coerencia ou regredir a versao."""
    from apps.atendimento.services.assumir_conversa import assumir_conversa
    from apps.atendimento.services.conversas import snapshot_conversa
    from apps.auditoria.models import EventoAuditoria
    from apps.auditoria.services.registrar_alteracao import registrar_alteracao
    from apps.auditoria.services.restaurar_revisao import restaurar_revisao

    conversa = ConversaFactory()
    ator = _membro(conversa.empresa)
    inicial = registrar_alteracao(
        empresa=conversa.empresa,
        objeto=conversa,
        acao=EventoAuditoria.Acao.CRIACAO,
        antes={},
        depois=snapshot_conversa(conversa),
        campos_alterados=list(snapshot_conversa(conversa)),
        ator=ator,
        origem="teste",
        correlacao="revisao-inicial",
    ).revisao
    assumir_conversa(
        empresa=conversa.empresa,
        conversa_id=conversa.id,
        ator=ator,
        versao=1,
        justificativa="",
        origem="teste",
        correlacao="assumir-restauracao",
    )

    restaurar_revisao(
        empresa=conversa.empresa,
        revisao=inicial,
        ator=ator,
        origem="teste",
        correlacao="restaurar-conversa",
    )

    conversa.refresh_from_db()
    evento = EventoAuditoria.objects.get(correlacao="restaurar-conversa")
    assert conversa.modo == Conversa.Modo.IA
    assert conversa.atendente_id is None
    assert conversa.versao == 3
    assert evento.depois["versao"] == 3
