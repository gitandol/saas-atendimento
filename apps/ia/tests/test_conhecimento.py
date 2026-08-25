"""Testes do dominio de conhecimento textual e FAQ."""

import pytest
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied

from apps.contas.models import Usuario
from apps.empresas.models import Empresa, MembroEmpresa


def _membro(empresa: Empresa, papel: str, email: str) -> Usuario:
    """Cria um membro ativo com o papel solicitado."""
    usuario = Usuario.objects.create_user(email=email)
    MembroEmpresa.objects.create(usuario=usuario, empresa=empresa, papel=papel)
    return usuario


@pytest.mark.django_db
def test_documentos_ordenam_isolam_e_auditam_exclusao_logica() -> None:
    """Protege o tenant e conserva historico ao remover um documento."""
    from apps.auditoria.models import EventoAuditoria, RevisaoObjeto
    from apps.ia.models import DocumentoTextual
    from apps.ia.services.gerenciar_conhecimento import (
        DadosDocumentoTextual,
        criar_documento,
        excluir_documento,
        listar_documentos,
    )

    empresa = Empresa.objects.create(nome="Empresa conhecimento")
    externa = Empresa.objects.create(nome="Empresa externa")
    admin = _membro(empresa, MembroEmpresa.Papel.ADMINISTRADOR, "admin-doc@example.com")
    externo = _membro(
        externa, MembroEmpresa.Papel.ADMINISTRADOR, "externo-doc@example.com"
    )
    segundo = criar_documento(
        empresa=empresa,
        ator=admin,
        dados=DadosDocumentoTextual("Segundo", "Conteudo 2", True, 2),
        correlacao="doc-2",
    )
    primeiro = criar_documento(
        empresa=empresa,
        ator=admin,
        dados=DadosDocumentoTextual("Primeiro", "Conteudo 1", True, 1),
        correlacao="doc-1",
    )
    pagina = listar_documentos(empresa=empresa, ator=admin, pagina=1, tamanho=20)
    assert [item.id for item in pagina.itens] == [primeiro.id, segundo.id]
    with pytest.raises(PermissionDenied):
        listar_documentos(empresa=empresa, ator=externo, pagina=1, tamanho=20)
    excluir_documento(
        empresa=empresa, ator=admin, documento_id=primeiro.id, correlacao="doc-excluir"
    )
    assert DocumentoTextual.objects.get(pk=primeiro.id).excluido_em is not None
    assert (
        listar_documentos(empresa=empresa, ator=admin, pagina=1, tamanho=20).total == 1
    )
    assert EventoAuditoria.objects.filter(
        objeto_id=str(primeiro.id), acao=EventoAuditoria.Acao.EXCLUSAO
    ).exists()
    assert RevisaoObjeto.objects.filter(objeto_id=str(primeiro.id)).count() == 2


@pytest.mark.django_db
def test_faq_permite_consulta_por_atendente_e_mutacao_apenas_por_admin() -> None:
    """Mantem leitura operacional e restringe alteracoes administrativas."""
    from apps.ia.services.gerenciar_conhecimento import (
        DadosPerguntaFrequente,
        criar_pergunta_frequente,
        listar_perguntas_frequentes,
    )

    empresa = Empresa.objects.create(nome="Empresa FAQ")
    admin = _membro(empresa, MembroEmpresa.Papel.ADMINISTRADOR, "admin-faq@example.com")
    atendente = _membro(
        empresa, MembroEmpresa.Papel.ATENDENTE, "atendente-faq@example.com"
    )
    faq = criar_pergunta_frequente(
        empresa=empresa,
        ator=admin,
        dados=DadosPerguntaFrequente("Qual o horario?", "Das 8h as 18h.", True, 3),
        correlacao="faq-criar",
    )
    assert listar_perguntas_frequentes(
        empresa=empresa, ator=atendente, pagina=1, tamanho=20
    ).itens == [faq]
    with pytest.raises(PermissionDenied):
        criar_pergunta_frequente(
            empresa=empresa,
            ator=atendente,
            dados=DadosPerguntaFrequente("Outra?", "Nao.", True, 1),
            correlacao="faq-negada",
        )


@pytest.mark.django_db
def test_atualizacao_recusa_id_de_outra_empresa() -> None:
    """Nao revela nem altera conhecimento pertencente a outro tenant."""
    from apps.ia.services.gerenciar_conhecimento import (
        DadosDocumentoTextual,
        atualizar_documento,
        criar_documento,
    )

    empresa = Empresa.objects.create(nome="Empresa local")
    externa = Empresa.objects.create(nome="Empresa remota")
    admin = _membro(
        empresa, MembroEmpresa.Papel.ADMINISTRADOR, "admin-local@example.com"
    )
    admin_externo = _membro(
        externa, MembroEmpresa.Papel.ADMINISTRADOR, "admin-remoto@example.com"
    )
    documento = criar_documento(
        empresa=externa,
        ator=admin_externo,
        dados=DadosDocumentoTextual("Remoto", "Privado", True, 1),
        correlacao="remoto",
    )
    with pytest.raises(ObjectDoesNotExist):
        atualizar_documento(
            empresa=empresa,
            ator=admin,
            documento_id=documento.id,
            dados=DadosDocumentoTextual("Ataque", "Alterado", True, 1),
            correlacao="tentativa",
        )


@pytest.mark.django_db
def test_restaura_revisao_anterior_de_documento() -> None:
    """Reaplica estado auditado mantendo as invariantes atuais do modelo."""
    from apps.auditoria.models import RevisaoObjeto
    from apps.auditoria.services.restaurar_revisao import restaurar_revisao
    from apps.ia.models import DocumentoTextual
    from apps.ia.services.gerenciar_conhecimento import (
        DadosDocumentoTextual,
        atualizar_documento,
        criar_documento,
    )

    empresa = Empresa.objects.create(nome="Empresa restauracao")
    admin = _membro(
        empresa, MembroEmpresa.Papel.ADMINISTRADOR, "admin-restaura@example.com"
    )
    documento = criar_documento(
        empresa=empresa,
        ator=admin,
        dados=DadosDocumentoTextual("Original", "Texto original", True, 1),
        correlacao="original",
    )
    revisao = RevisaoObjeto.objects.get(objeto_id=str(documento.id), numero=1)
    atualizar_documento(
        empresa=empresa,
        ator=admin,
        documento_id=documento.id,
        dados=DadosDocumentoTextual("Novo", "Texto novo", False, 4),
        correlacao="novo",
    )
    restaurar_revisao(
        empresa=empresa,
        revisao=revisao,
        ator=admin,
        origem="teste",
        correlacao="restaurar",
    )
    restaurado = DocumentoTextual.objects.get(pk=documento.id)
    assert (
        restaurado.titulo,
        restaurado.conteudo,
        restaurado.ativo,
        restaurado.ordem,
    ) == ("Original", "Texto original", True, 1)
