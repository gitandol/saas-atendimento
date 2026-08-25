"""Testes HTTP da configuracao da empresa."""

from dataclasses import replace
from unittest.mock import patch

import pytest
from django.test import Client

from apps.contas.models import Usuario
from apps.empresas.models import Empresa, MembroEmpresa


def _cliente_membro(*, empresa: Empresa, papel: str) -> tuple[Client, Usuario]:
    """Autentica um membro ativo para exercitar a API real."""
    usuario = Usuario.objects.create_user(email=f"{papel.lower()}@example.com")
    MembroEmpresa.objects.create(usuario=usuario, empresa=empresa, papel=papel)
    cliente = Client()
    cliente.force_login(usuario)
    return cliente, usuario


def _payload(empresa: Empresa) -> dict[str, str]:
    """Monta uma atualizacao HTTP completa e versionada."""
    return {
        "nome": "Empresa pela API",
        "segmento": "Educacao",
        "descricao": "Cursos online",
        "horario_atendimento": "8h as 18h",
        "endereco": "Rua Escola, 10",
        "telefone": "+55 (68) 99999-1111",
        "site": "https://escola.example.com",
        "instrucoes_atendimento": "Informe os cursos disponiveis.",
        "atualizado_em": empresa.atualizado_em.isoformat(),
    }


@pytest.mark.django_db
def test_api_empresa_exige_sessao() -> None:
    """Recusa configuracao empresarial para cliente anonimo."""
    assert Client().get("/api/v1/empresa").status_code == 401
    assert (
        Client()
        .put("/api/v1/empresa", data={}, content_type="application/json")
        .status_code
        == 401
    )


@pytest.mark.django_db
def test_get_empresa_retorna_dados_da_empresa_ativa() -> None:
    """Consulta o perfil exclusivamente pelo service do tenant ativo."""
    empresa = Empresa.objects.create(nome="Empresa GET", segmento="Consultoria")
    cliente, _ = _cliente_membro(empresa=empresa, papel=MembroEmpresa.Papel.ATENDENTE)

    resposta = cliente.get("/api/v1/empresa")

    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Empresa GET"
    assert resposta.json()["segmento"] == "Consultoria"
    versao_publicada = empresa.atualizado_em.isoformat(timespec="milliseconds")
    assert resposta.json()["atualizado_em"] == versao_publicada.replace("+00:00", "Z")


@pytest.mark.django_db
def test_put_empresa_converte_schema_em_dados_de_dominio_e_delega() -> None:
    """Mantem o endpoint como adaptador sem regras de concorrencia ou persistencia."""
    from apps.empresas.services.obter_empresa import obter_empresa

    empresa = Empresa.objects.create(nome="Empresa PUT")
    cliente, usuario = _cliente_membro(
        empresa=empresa, papel=MembroEmpresa.Papel.ADMINISTRADOR
    )
    retorno = replace(obter_empresa(empresa=empresa, ator=usuario), nome="Delegada")

    with patch(
        "apps.empresas.api.endpoints.configuracao_empresa.atualizar_empresa",
        return_value=retorno,
    ) as atualizar:
        resposta = cliente.put(
            "/api/v1/empresa",
            data=_payload(empresa),
            content_type="application/json",
            HTTP_X_CORRELATION_ID="corr-http",
        )

    assert resposta.status_code == 200
    assert resposta.json()["nome"] == "Delegada"
    argumentos = atualizar.call_args.kwargs
    assert argumentos["empresa"] == empresa
    assert argumentos["ator"] == usuario
    assert argumentos["correlacao"] == "corr-http"
    assert argumentos["dados"].telefone == "+5568999991111"


@pytest.mark.django_db
def test_put_empresa_aceita_versao_publicada_pelo_get() -> None:
    """Permite salvar imediatamente a versao que a propria API entregou."""
    empresa = Empresa.objects.create(nome="Empresa integrada")
    cliente, _ = _cliente_membro(
        empresa=empresa, papel=MembroEmpresa.Papel.ADMINISTRADOR
    )
    versao = cliente.get("/api/v1/empresa").json()["atualizado_em"]
    payload = _payload(empresa)
    payload["atualizado_em"] = versao

    resposta = cliente.put(
        "/api/v1/empresa",
        data=payload,
        content_type="application/json",
    )

    assert resposta.status_code == 200
    empresa.refresh_from_db()
    assert empresa.nome == "Empresa pela API"


@pytest.mark.django_db
def test_put_empresa_recusa_atendente() -> None:
    """Traduz a autorizacao administrativa do service em resposta proibida."""
    empresa = Empresa.objects.create(nome="Empresa protegida")
    cliente, _ = _cliente_membro(empresa=empresa, papel=MembroEmpresa.Papel.ATENDENTE)

    resposta = cliente.put(
        "/api/v1/empresa",
        data=_payload(empresa),
        content_type="application/json",
    )

    assert resposta.status_code == 403
    assert resposta.json()["codigo"] == "permissao_negada"


@pytest.mark.django_db
def test_put_empresa_traduz_conflito_de_concorrencia() -> None:
    """Retorna mensagem compreensivel quando a versao enviada ficou obsoleta."""
    empresa = Empresa.objects.create(nome="Empresa concorrente")
    cliente, _ = _cliente_membro(
        empresa=empresa, papel=MembroEmpresa.Papel.ADMINISTRADOR
    )
    payload = _payload(empresa)
    payload["atualizado_em"] = "2020-01-01T00:00:00Z"

    resposta = cliente.put(
        "/api/v1/empresa",
        data=payload,
        content_type="application/json",
    )

    assert resposta.status_code == 409
    assert resposta.json() == {
        "codigo": "versao_obsoleta",
        "mensagem": "A empresa foi atualizada por outra pessoa. Recarregue os dados.",
    }
