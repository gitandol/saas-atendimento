"""Testes HTTP do conhecimento textual e perguntas frequentes."""

import pytest
from django.test import Client

from apps.contas.models import Usuario
from apps.empresas.models import Empresa, MembroEmpresa


def _cliente(empresa: Empresa, papel: str, email: str) -> Client:
    """Autentica um membro para exercitar a API real."""
    usuario = Usuario.objects.create_user(email=email)
    MembroEmpresa.objects.create(usuario=usuario, empresa=empresa, papel=papel)
    cliente = Client()
    cliente.force_login(usuario)
    return cliente


@pytest.mark.django_db
def test_api_documentos_cria_lista_edita_e_exclui() -> None:
    """Expoe o ciclo CRUD paginado somente ao administrador para mutacoes."""
    empresa = Empresa.objects.create(nome="Empresa API documentos")
    admin = _cliente(
        empresa, MembroEmpresa.Papel.ADMINISTRADOR, "admin-api-doc@example.com"
    )
    criada = admin.post(
        "/api/v1/ia/conhecimentos",
        data={"titulo": "Entrega", "conteudo": "Em 3 dias.", "ativo": True, "ordem": 2},
        content_type="application/json",
    )
    documento_id = criada.json()["id"]
    listagem = admin.get("/api/v1/ia/conhecimentos?pagina=1&tamanho=10")
    editada = admin.put(
        f"/api/v1/ia/conhecimentos/{documento_id}",
        data={
            "titulo": "Entrega expressa",
            "conteudo": "Em 1 dia.",
            "ativo": False,
            "ordem": 1,
        },
        content_type="application/json",
    )
    excluida = admin.delete(f"/api/v1/ia/conhecimentos/{documento_id}")

    assert criada.status_code == 201
    assert listagem.status_code == 200
    assert listagem.json()["total"] == 1
    assert listagem.json()["itens"][0]["titulo"] == "Entrega"
    assert editada.status_code == 200
    assert (editada.json()["ativo"], editada.json()["ordem"]) == (False, 1)
    assert excluida.status_code == 204
    assert admin.get("/api/v1/ia/conhecimentos").json()["total"] == 0


@pytest.mark.django_db
def test_api_faq_atendente_consulta_mas_nao_edita() -> None:
    """Permite leitura operacional e recusa mutacao sem papel administrativo."""
    empresa = Empresa.objects.create(nome="Empresa API FAQ")
    admin = _cliente(
        empresa, MembroEmpresa.Papel.ADMINISTRADOR, "admin-api-faq@example.com"
    )
    criada = admin.post(
        "/api/v1/ia/perguntas-frequentes",
        data={"pergunta": "Aceita PIX?", "resposta": "Sim.", "ativo": True, "ordem": 1},
        content_type="application/json",
    )
    atendente = _cliente(
        empresa, MembroEmpresa.Papel.ATENDENTE, "atendente-api-faq@example.com"
    )
    consulta = atendente.get("/api/v1/ia/perguntas-frequentes")
    negada = atendente.put(
        f"/api/v1/ia/perguntas-frequentes/{criada.json()['id']}",
        data={"pergunta": "Alterar?", "resposta": "Nao.", "ativo": False, "ordem": 2},
        content_type="application/json",
    )

    assert consulta.status_code == 200
    assert consulta.json()["itens"][0]["pergunta"] == "Aceita PIX?"
    assert negada.status_code == 403
    assert negada.json()["codigo"] == "permissao_negada"


@pytest.mark.django_db
def test_api_recusa_schema_invalido_e_id_externo() -> None:
    """Valida o corpo e oculta recursos de outra empresa."""
    from apps.ia.models import DocumentoTextual

    empresa = Empresa.objects.create(nome="Empresa local API")
    externa = Empresa.objects.create(nome="Empresa externa API")
    admin = _cliente(
        empresa, MembroEmpresa.Papel.ADMINISTRADOR, "admin-local-api@example.com"
    )
    externo = DocumentoTextual.objects.create(
        empresa=externa, titulo="Privado", conteudo="Segredo"
    )

    invalida = admin.post(
        "/api/v1/ia/conhecimentos",
        data={"titulo": "", "conteudo": "", "ativo": True, "ordem": -1},
        content_type="application/json",
    )
    nao_encontrada = admin.put(
        f"/api/v1/ia/conhecimentos/{externo.pk}",
        data={"titulo": "Ataque", "conteudo": "Alterado", "ativo": True, "ordem": 1},
        content_type="application/json",
    )

    assert invalida.status_code == 422
    assert invalida.json()["codigo"] == "dados_invalidos"
    assert nao_encontrada.status_code == 404
    assert DocumentoTextual.objects.get(pk=externo.pk).titulo == "Privado"
