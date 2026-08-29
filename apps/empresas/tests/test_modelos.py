"""Testes dos modelos que vinculam usuarios a empresas."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.contas.models import Usuario
from apps.empresas.models import Empresa, MembroEmpresa


@pytest.fixture
def usuario(db):
    """Cria um usuario para associacao com uma empresa."""
    return Usuario.objects.create_user(email="membro@example.com", password="senha")


@pytest.fixture
def empresa(db):
    """Cria uma empresa para associacao com um usuario."""
    return Empresa.objects.create(nome="Empresa de teste")


@pytest.mark.django_db
def test_empresa_tem_uuid_e_registra_data_de_criacao(empresa):
    """Registra automaticamente o momento de criacao da empresa."""
    assert empresa.criado_em is not None


@pytest.mark.django_db
def test_empresa_armazena_configuracao_e_versao_de_atualizacao() -> None:
    """Persiste o perfil operacional com uma versao para concorrencia."""
    empresa = Empresa.objects.create(
        nome="Clinica Exemplo",
        segmento="Saude",
        descricao="Atendimento humanizado.",
        horario_atendimento="Segunda a sexta, das 8h as 18h.",
        endereco="Rua Principal, 100",
        telefone="+5568999990000",
        site="https://clinica.example.com",
        instrucoes_atendimento="Priorize urgencias.",
    )

    assert empresa.segmento == "Saude"
    assert empresa.descricao == "Atendimento humanizado."
    assert empresa.horario_atendimento == "Segunda a sexta, das 8h as 18h."
    assert empresa.endereco == "Rua Principal, 100"
    assert empresa.telefone == "+5568999990000"
    assert empresa.site == "https://clinica.example.com"
    assert empresa.instrucoes_atendimento == "Priorize urgencias."
    assert empresa.atualizado_em is not None


@pytest.mark.django_db
def test_empresa_define_fuso_horario_operacional() -> None:
    """Falha se a empresa nao possuir fuso IANA valido com padrao seguro."""
    empresa = Empresa.objects.create(nome="Empresa do Acre")

    assert empresa.fuso_horario == "America/Rio_Branco"

    empresa.fuso_horario = "America/Sao_Paulo"
    empresa.full_clean()
    empresa.save()
    empresa.refresh_from_db()

    assert empresa.fuso_horario == "America/Sao_Paulo"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "fuso_invalido",
    ["Marte/Olympus", "/America/Sao_Paulo"],
)
def test_empresa_recusa_fuso_horario_desconhecido(fuso_invalido: str) -> None:
    """Falha se um identificador que ZoneInfo desconhece for persistido."""
    empresa = Empresa(nome="Empresa invalida", fuso_horario=fuso_invalido)

    with pytest.raises(ValidationError, match="Fuso horario invalido"):
        empresa.full_clean()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "papel",
    [MembroEmpresa.Papel.ADMINISTRADOR, MembroEmpresa.Papel.ATENDENTE],
)
def test_associacao_aceita_os_papeis_previstos(usuario, empresa, papel):
    """Persiste os dois papeis de acesso definidos para uma empresa."""
    membro = MembroEmpresa.objects.create(usuario=usuario, empresa=empresa, papel=papel)

    assert membro.papel == papel


@pytest.mark.django_db
def test_associacao_e_unica_por_usuario_e_empresa(usuario, empresa):
    """Impede que um usuario tenha duas associacoes com a mesma empresa."""
    MembroEmpresa.objects.create(
        usuario=usuario,
        empresa=empresa,
        papel=MembroEmpresa.Papel.ATENDENTE,
    )

    with pytest.raises(IntegrityError):
        MembroEmpresa.objects.create(
            usuario=usuario,
            empresa=empresa,
            papel=MembroEmpresa.Papel.ADMINISTRADOR,
        )
