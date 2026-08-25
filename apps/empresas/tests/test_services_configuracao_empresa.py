"""Testes dos services da configuracao da empresa."""

from dataclasses import replace
from datetime import timedelta

import pytest
from django.core.exceptions import PermissionDenied

from apps.contas.models import Usuario
from apps.empresas.models import Empresa, MembroEmpresa


def _criar_usuario(
    *, empresa: Empresa, papel: str, email: str = "ator@example.com"
) -> Usuario:
    """Cria um membro ativo com o papel solicitado."""
    usuario = Usuario.objects.create_user(email=email, password="senha")
    MembroEmpresa.objects.create(usuario=usuario, empresa=empresa, papel=papel)
    return usuario


def _dados_atualizacao(empresa: Empresa):
    """Monta dados de dominio completos com a versao persistida."""
    from apps.empresas.services.atualizar_empresa import DadosAtualizacaoEmpresa

    return DadosAtualizacaoEmpresa(
        nome="Empresa Atualizada",
        segmento="Tecnologia",
        descricao="Atendimento digital",
        horario_atendimento="Todos os dias, 8h as 20h",
        endereco="Avenida Central, 200",
        telefone="+5568999990000",
        site="https://atualizada.example.com",
        instrucoes_atendimento="Confirme o nome do cliente.",
        atualizado_em=empresa.atualizado_em,
    )


@pytest.mark.django_db
def test_obter_empresa_permite_membro_ativo_do_mesmo_tenant() -> None:
    """Entrega a configuracao somente a membro ativo da empresa informada."""
    from apps.empresas.services.obter_empresa import obter_empresa

    empresa = Empresa.objects.create(nome="Empresa Permitida", segmento="Varejo")
    ator = _criar_usuario(empresa=empresa, papel=MembroEmpresa.Papel.ATENDENTE)

    configuracao = obter_empresa(empresa=empresa, ator=ator)

    assert configuracao.nome == "Empresa Permitida"
    assert configuracao.segmento == "Varejo"
    assert configuracao.atualizado_em == empresa.atualizado_em


@pytest.mark.django_db
def test_obter_empresa_recusa_usuario_de_outro_tenant() -> None:
    """Evita leitura da configuracao por membro de empresa externa."""
    from apps.empresas.services.obter_empresa import obter_empresa

    empresa = Empresa.objects.create(nome="Protegida")
    externa = Empresa.objects.create(nome="Externa")
    ator = _criar_usuario(empresa=externa, papel=MembroEmpresa.Papel.ADMINISTRADOR)

    with pytest.raises(PermissionDenied):
        obter_empresa(empresa=empresa, ator=ator)


@pytest.mark.django_db
def test_atualizar_empresa_persiste_diff_e_auditoria_atomica() -> None:
    """Atualiza somente o tenant autorizado e registra antes e depois."""
    from apps.auditoria.models import EventoAuditoria, RevisaoObjeto
    from apps.empresas.services.atualizar_empresa import atualizar_empresa

    empresa = Empresa.objects.create(nome="Empresa Antiga", segmento="Varejo")
    ator = _criar_usuario(empresa=empresa, papel=MembroEmpresa.Papel.ADMINISTRADOR)

    configuracao = atualizar_empresa(
        empresa=empresa,
        dados=_dados_atualizacao(empresa),
        ator=ator,
        correlacao="corr-empresa-1",
    )

    empresa.refresh_from_db()
    evento = EventoAuditoria.objects.get()
    revisao = RevisaoObjeto.objects.get()
    assert configuracao.nome == "Empresa Atualizada"
    assert empresa.telefone == "+5568999990000"
    assert evento.campos_alterados == [
        "nome",
        "segmento",
        "descricao",
        "horario_atendimento",
        "endereco",
        "telefone",
        "site",
        "instrucoes_atendimento",
    ]
    assert evento.antes["nome"] == "Empresa Antiga"
    assert evento.depois["nome"] == "Empresa Atualizada"
    assert evento.ator == ator
    assert evento.correlacao == "corr-empresa-1"
    assert revisao.snapshot["nome"] == "Empresa Atualizada"


@pytest.mark.django_db
def test_atualizar_empresa_recusa_atendente_sem_gravar() -> None:
    """Restringe a mutacao ao administrador ativo do mesmo tenant."""
    from apps.auditoria.models import EventoAuditoria
    from apps.empresas.services.atualizar_empresa import atualizar_empresa

    empresa = Empresa.objects.create(nome="Sem alteracao")
    ator = _criar_usuario(empresa=empresa, papel=MembroEmpresa.Papel.ATENDENTE)

    with pytest.raises(PermissionDenied):
        atualizar_empresa(
            empresa=empresa,
            dados=_dados_atualizacao(empresa),
            ator=ator,
            correlacao="corr-negada",
        )

    empresa.refresh_from_db()
    assert empresa.nome == "Sem alteracao"
    assert not EventoAuditoria.objects.exists()


@pytest.mark.django_db
def test_atualizar_empresa_rejeita_versao_obsoleta() -> None:
    """Impede que uma edicao concorrente sobrescreva dados recentes."""
    from apps.auditoria.models import EventoAuditoria
    from apps.empresas.services.atualizar_empresa import (
        ConflitoAtualizacaoEmpresa,
        atualizar_empresa,
    )

    empresa = Empresa.objects.create(nome="Versao atual")
    ator = _criar_usuario(empresa=empresa, papel=MembroEmpresa.Papel.ADMINISTRADOR)
    dados = replace(
        _dados_atualizacao(empresa),
        atualizado_em=empresa.atualizado_em - timedelta(seconds=1),
    )

    with pytest.raises(ConflitoAtualizacaoEmpresa, match="atualizada por outra pessoa"):
        atualizar_empresa(
            empresa=empresa,
            dados=dados,
            ator=ator,
            correlacao="corr-conflito",
        )

    assert not EventoAuditoria.objects.exists()


@pytest.mark.django_db
def test_revisao_da_empresa_pode_ser_restaurada() -> None:
    """Reaplica valores anteriores por meio do historico auditavel existente."""
    from apps.auditoria.services.restaurar_revisao import restaurar_revisao
    from apps.empresas.services.atualizar_empresa import atualizar_empresa

    empresa = Empresa.objects.create(nome="Nome original", segmento="Original")
    ator = _criar_usuario(empresa=empresa, papel=MembroEmpresa.Papel.ADMINISTRADOR)
    primeira = atualizar_empresa(
        empresa=empresa,
        dados=_dados_atualizacao(empresa),
        ator=ator,
        correlacao="corr-primeira",
    )
    revisao = empresa.revisoes_objetos.get(numero=1)
    empresa.refresh_from_db()
    atualizar_empresa(
        empresa=empresa,
        dados=replace(_dados_atualizacao(empresa), nome="Outro nome"),
        ator=ator,
        correlacao="corr-segunda",
    )

    restaurar_revisao(
        empresa=empresa,
        revisao=revisao,
        ator=ator,
        origem="api",
        correlacao="corr-restauracao",
    )

    empresa.refresh_from_db()
    assert primeira.nome == "Empresa Atualizada"
    assert empresa.nome == "Empresa Atualizada"
