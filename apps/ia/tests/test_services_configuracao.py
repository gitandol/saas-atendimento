"""Testes dos services de configuracao e selecao do provider de IA."""

from dataclasses import replace
from unittest.mock import patch

import pytest
from django.core.exceptions import PermissionDenied

from apps.contas.models import Usuario
from apps.empresas.models import Empresa, MembroEmpresa


def _membro(empresa: Empresa, papel: str, email: str = "ia@example.com") -> Usuario:
    """Cria um membro ativo da empresa com o papel solicitado."""
    usuario = Usuario.objects.create_user(email=email)
    MembroEmpresa.objects.create(usuario=usuario, empresa=empresa, papel=papel)
    return usuario


def _dados(chave_api: str = "sk-nova-chave", atualizado_em=None):
    """Monta uma alteracao completa de configuracao para os testes."""
    from apps.ia.services.configuracao import DadosConfiguracaoIA

    return DadosConfiguracaoIA(
        modelo="gpt-4.1-mini",
        nome_assistente="Lia",
        personalidade="Cordial",
        mensagem_saudacao="Ola!",
        mensagem_falha="Atendimento indisponivel.",
        respostas_automaticas_ativas=True,
        chave_api=chave_api,
        atualizado_em=atualizado_em,
    )


@pytest.mark.django_db
def test_atualizar_configuracao_criptografa_e_audita_sem_segredo(settings) -> None:
    """Persiste a credencial cifrada e registra somente seu estado booleano."""
    from apps.auditoria.models import EventoAuditoria, RevisaoObjeto
    from apps.ia.models import ConfiguracaoIA
    from apps.ia.services.configuracao import atualizar_configuracao

    settings.IA_CHAVE_CRIPTOGRAFIA = "mestre-testes"
    empresa = Empresa.objects.create(nome="Empresa configurada")
    ator = _membro(empresa, MembroEmpresa.Papel.ADMINISTRADOR)

    saida = atualizar_configuracao(
        empresa=empresa,
        ator=ator,
        dados=_dados(),
        correlacao="corr-ia",
    )

    configuracao = ConfiguracaoIA.objects.get(empresa=empresa)
    evento = EventoAuditoria.objects.get()
    revisao = RevisaoObjeto.objects.get()
    assert saida.chave_configurada is True
    assert saida.nome_assistente == "Lia"
    assert "sk-nova-chave" not in configuracao.chave_api_criptografada
    assert "sk-nova-chave" not in str(evento.antes)
    assert "sk-nova-chave" not in str(evento.depois)
    assert "sk-nova-chave" not in str(revisao.snapshot)
    assert evento.depois["chave_configurada"] is True
    assert evento.correlacao == "corr-ia"


@pytest.mark.django_db
def test_chave_vazia_preserva_existente_e_remocao_explicita_apaga(settings) -> None:
    """Distingue formulario sem nova chave da acao deliberada de remocao."""
    from apps.ia.models import ConfiguracaoIA
    from apps.ia.services.configuracao import atualizar_configuracao, remover_chave

    settings.IA_CHAVE_CRIPTOGRAFIA = "mestre-testes"
    empresa = Empresa.objects.create(nome="Empresa preservada")
    ator = _membro(empresa, MembroEmpresa.Papel.ADMINISTRADOR)
    atualizar_configuracao(
        empresa=empresa,
        ator=ator,
        dados=_dados(),
        correlacao="corr-primeira",
    )
    configuracao = ConfiguracaoIA.objects.get(empresa=empresa)
    cifra_original = configuracao.chave_api_criptografada

    atualizar_configuracao(
        empresa=empresa,
        ator=ator,
        dados=_dados(chave_api="", atualizado_em=configuracao.atualizado_em),
        correlacao="corr-preserva",
    )
    configuracao.refresh_from_db()
    assert configuracao.chave_api_criptografada == cifra_original

    saida = remover_chave(
        empresa=empresa,
        ator=ator,
        correlacao="corr-remove",
    )
    configuracao.refresh_from_db()
    assert configuracao.chave_api_criptografada == ""
    assert saida.chave_configurada is False


@pytest.mark.django_db
def test_services_respeitam_tenant_e_papel() -> None:
    """Recusa leitura entre empresas e mutacao por atendente."""
    from apps.ia.services.configuracao import atualizar_configuracao, obter_configuracao

    empresa = Empresa.objects.create(nome="Empresa protegida")
    externa = Empresa.objects.create(nome="Empresa externa")
    atendente = _membro(empresa, MembroEmpresa.Papel.ATENDENTE)
    externo = _membro(externa, MembroEmpresa.Papel.ADMINISTRADOR, "externo@example.com")

    with pytest.raises(PermissionDenied):
        atualizar_configuracao(
            empresa=empresa,
            ator=atendente,
            dados=_dados(),
            correlacao="negada",
        )
    with pytest.raises(PermissionDenied):
        obter_configuracao(empresa=empresa, ator=externo)


@pytest.mark.django_db
def test_obter_provider_recupera_credencial_sem_expo_la(settings) -> None:
    """Constroi o provider contratado a partir da configuracao cifrada."""
    from apps.ia.integrations.openai import ProviderOpenAI
    from apps.ia.services.configuracao import atualizar_configuracao
    from apps.ia.services.obter_provider import obter_provider

    settings.IA_CHAVE_CRIPTOGRAFIA = "mestre-testes"
    empresa = Empresa.objects.create(nome="Empresa provider")
    ator = _membro(empresa, MembroEmpresa.Papel.ADMINISTRADOR)
    atualizar_configuracao(
        empresa=empresa,
        ator=ator,
        dados=_dados(chave_api="sk-provider"),
        correlacao="corr-provider",
    )

    provider = obter_provider(empresa)

    assert isinstance(provider, ProviderOpenAI)
    assert "sk-provider" not in repr(provider)


@pytest.mark.django_db
def test_testar_configuracao_usa_provider_sem_salvar_chave(settings) -> None:
    """Valida uma credencial informada sem transforma-la em configuracao persistida."""
    from apps.ia.integrations.protocolos import RespostaIA
    from apps.ia.services.testar_configuracao import testar_configuracao

    settings.IA_CHAVE_CRIPTOGRAFIA = "mestre-testes"
    empresa = Empresa.objects.create(nome="Empresa teste")
    ator = _membro(empresa, MembroEmpresa.Papel.ADMINISTRADOR)

    with patch("apps.ia.services.testar_configuracao.ProviderOpenAI") as classe:
        classe.return_value.gerar_resposta.return_value = RespostaIA(
            texto="OK",
            modelo="gpt-4.1-mini",
            tokens_entrada=5,
            tokens_saida=1,
        )
        resultado = testar_configuracao(
            empresa=empresa,
            ator=ator,
            chave_api="sk-temporaria",
            modelo="gpt-4.1-mini",
        )

    assert resultado.sucesso is True
    assert resultado.mensagem == "Conexao com a OpenAI realizada com sucesso."
    assert not hasattr(empresa, "configuracao_ia")


@pytest.mark.django_db
def test_rotacao_de_chave_gera_evento_sem_expor_segredo(settings) -> None:
    """Audita a substituicao mesmo quando o indicador continua verdadeiro."""
    from apps.auditoria.models import EventoAuditoria
    from apps.ia.models import ConfiguracaoIA
    from apps.ia.services.configuracao import atualizar_configuracao

    settings.IA_CHAVE_CRIPTOGRAFIA = "mestre-rotacao"
    empresa = Empresa.objects.create(nome="Empresa rotacao")
    ator = _membro(empresa, MembroEmpresa.Papel.ADMINISTRADOR)
    atualizar_configuracao(
        empresa=empresa,
        ator=ator,
        dados=_dados(chave_api="sk-antiga"),
        correlacao="corr-antiga",
    )
    configuracao = ConfiguracaoIA.objects.get(empresa=empresa)
    atualizar_configuracao(
        empresa=empresa,
        ator=ator,
        dados=_dados(chave_api="sk-nova", atualizado_em=configuracao.atualizado_em),
        correlacao="corr-rotacao",
    )
    evento = EventoAuditoria.objects.get(correlacao="corr-rotacao")
    assert "chave_api" in evento.campos_alterados
    assert "sk-antiga" not in str(evento.antes)
    assert "sk-nova" not in str(evento.depois)


@pytest.mark.django_db
def test_atualizacao_recusa_versao_obsoleta(settings) -> None:
    """Impede que um formulario antigo sobrescreva uma edicao recente."""
    from apps.ia.models import ConfiguracaoIA
    from apps.ia.services.configuracao import (
        ConflitoAtualizacaoIA,
        atualizar_configuracao,
    )

    settings.IA_CHAVE_CRIPTOGRAFIA = "mestre-concorrencia"
    empresa = Empresa.objects.create(nome="Empresa concorrente")
    ator = _membro(empresa, MembroEmpresa.Papel.ADMINISTRADOR)
    atualizar_configuracao(
        empresa=empresa, ator=ator, dados=_dados(), correlacao="corr-inicial"
    )
    configuracao = ConfiguracaoIA.objects.get(empresa=empresa)
    versao_antiga = configuracao.atualizado_em
    atualizar_configuracao(
        empresa=empresa,
        ator=ator,
        dados=replace(
            _dados(chave_api="", atualizado_em=versao_antiga),
            nome_assistente="Edicao recente",
        ),
        correlacao="corr-recente",
    )
    with pytest.raises(ConflitoAtualizacaoIA):
        atualizar_configuracao(
            empresa=empresa,
            ator=ator,
            dados=_dados(chave_api="", atualizado_em=versao_antiga),
            correlacao="corr-obsoleta",
        )
