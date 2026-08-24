"""Testa a preservacao do ator referenciado pela trilha imutavel."""

import pytest
from django.db.models.deletion import ProtectedError


@pytest.mark.django_db
def test_usuario_com_evento_auditado_nao_pode_ser_excluido() -> None:
    """Mantem a autoria sem exigir atualizacao de um evento append-only."""
    from apps.auditoria.models import EventoAuditoria
    from apps.auditoria.services.registrar_alteracao import registrar_alteracao
    from apps.contas.models import Usuario
    from apps.empresas.models import Empresa

    empresa = Empresa.objects.create(nome="Preserva ator")
    ator = Usuario.objects.create_user(email="ator-protegido@example.com")
    registrar_alteracao(
        empresa=empresa,
        objeto=empresa,
        acao=EventoAuditoria.Acao.CRIACAO,
        antes={},
        depois={"nome": empresa.nome},
        campos_alterados=["nome"],
        ator=ator,
        origem="teste",
        correlacao="corr-ator-protegido",
    )

    with pytest.raises(ProtectedError):
        ator.delete()
