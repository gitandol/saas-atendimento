"""Gerencia conhecimento textual e FAQ com isolamento e auditoria."""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from django.core.exceptions import PermissionDenied
from django.db import models, transaction
from django.utils import timezone

from apps.auditoria.models import EventoAuditoria
from apps.auditoria.services.registrar_alteracao import registrar_alteracao
from apps.contas.models import Usuario
from apps.empresas.models import Empresa, MembroEmpresa
from apps.empresas.services.obter_empresa import autorizar_membro
from apps.ia.models import DocumentoTextual, PerguntaFrequente


@dataclass(frozen=True)
class DadosDocumentoTextual:
    """Agrupa campos editaveis de um documento textual."""

    titulo: str
    conteudo: str
    ativo: bool
    ordem: int


@dataclass(frozen=True)
class DadosPerguntaFrequente:
    """Agrupa campos editaveis de uma pergunta frequente."""

    pergunta: str
    resposta: str
    ativo: bool
    ordem: int


@dataclass(frozen=True)
class DocumentoTextualPublico:
    """Representa um documento textual publicado pelo dominio."""

    id: int
    titulo: str
    conteudo: str
    ativo: bool
    ordem: int
    atualizado_em: datetime


@dataclass(frozen=True)
class PerguntaFrequentePublica:
    """Representa uma pergunta frequente publicada pelo dominio."""

    id: int
    pergunta: str
    resposta: str
    ativo: bool
    ordem: int
    atualizado_em: datetime


@dataclass(frozen=True)
class PaginaConhecimento:
    """Representa uma pagina de documentos ou perguntas frequentes."""

    itens: list[DocumentoTextualPublico] | list[PerguntaFrequentePublica]
    pagina: int
    tamanho: int
    total: int


def _exigir_administrador(*, empresa: Empresa, ator: Usuario) -> None:
    """Exige associacao administrativa ativa na empresa."""
    membro = autorizar_membro(empresa=empresa, ator=ator)
    if membro.papel != MembroEmpresa.Papel.ADMINISTRADOR:
        raise PermissionDenied


def _snapshot(objeto: models.Model) -> dict[str, Any]:
    """Produz o estado funcional restauravel do conhecimento."""
    if isinstance(objeto, DocumentoTextual):
        nomes = ("titulo", "conteudo", "ativo", "ordem", "excluido_em")
    else:
        nomes = ("pergunta", "resposta", "ativo", "ordem", "excluido_em")
    snapshot = {nome: getattr(objeto, nome) for nome in nomes}
    excluido_em = snapshot["excluido_em"]
    if excluido_em is not None:
        snapshot["excluido_em"] = excluido_em.isoformat()
    return snapshot


def _publicar_documento(objeto: DocumentoTextual) -> DocumentoTextualPublico:
    """Converte um documento persistido em tipo publico."""
    return DocumentoTextualPublico(
        objeto.pk,
        objeto.titulo,
        objeto.conteudo,
        objeto.ativo,
        objeto.ordem,
        objeto.atualizado_em,
    )


def _publicar_faq(objeto: PerguntaFrequente) -> PerguntaFrequentePublica:
    """Converte uma FAQ persistida em tipo publico."""
    return PerguntaFrequentePublica(
        objeto.pk,
        objeto.pergunta,
        objeto.resposta,
        objeto.ativo,
        objeto.ordem,
        objeto.atualizado_em,
    )


def _pagina(consulta, publicar, pagina: int, tamanho: int) -> PaginaConhecimento:
    """Pagina uma consulta ordenada usando o publicador informado."""
    total = consulta.count()
    inicio = (pagina - 1) * tamanho
    return PaginaConhecimento(
        [publicar(item) for item in consulta[inicio : inicio + tamanho]],
        pagina,
        tamanho,
        total,
    )


def listar_documentos(
    *, empresa: Empresa, ator: Usuario, pagina: int, tamanho: int
) -> PaginaConhecimento:
    """Lista somente documentos nao excluidos do tenant autorizado."""
    autorizar_membro(empresa=empresa, ator=ator)
    consulta = DocumentoTextual.objects.filter(
        empresa=empresa, excluido_em__isnull=True
    )
    return _pagina(consulta, _publicar_documento, pagina, tamanho)


def listar_perguntas_frequentes(
    *, empresa: Empresa, ator: Usuario, pagina: int, tamanho: int
) -> PaginaConhecimento:
    """Lista somente FAQ nao excluidas do tenant autorizado."""
    autorizar_membro(empresa=empresa, ator=ator)
    consulta = PerguntaFrequente.objects.filter(
        empresa=empresa, excluido_em__isnull=True
    )
    return _pagina(consulta, _publicar_faq, pagina, tamanho)


def _auditar(
    *,
    empresa: Empresa,
    objeto: models.Model,
    acao: str,
    antes: dict[str, Any],
    ator: Usuario,
    correlacao: str,
) -> None:
    """Registra alteracao e snapshot funcional do objeto."""
    depois = _snapshot(objeto)
    registrar_alteracao(
        empresa=empresa,
        objeto=objeto,
        acao=acao,
        antes=antes,
        depois=depois,
        campos_alterados=[
            nome for nome, valor in depois.items() if antes.get(nome) != valor
        ],
        ator=ator,
        origem="api",
        correlacao=correlacao,
    )


@transaction.atomic
def criar_documento(
    *,
    empresa: Empresa,
    ator: Usuario,
    dados: DadosDocumentoTextual,
    correlacao: str,
) -> DocumentoTextualPublico:
    """Cria e audita um documento na empresa autorizada."""
    _exigir_administrador(empresa=empresa, ator=ator)
    objeto = DocumentoTextual(empresa=empresa, **asdict(dados))
    objeto.full_clean()
    objeto.save()
    _auditar(
        empresa=empresa,
        objeto=objeto,
        acao=EventoAuditoria.Acao.CRIACAO,
        antes={},
        ator=ator,
        correlacao=correlacao,
    )
    return _publicar_documento(objeto)


@transaction.atomic
def atualizar_documento(
    *,
    empresa: Empresa,
    ator: Usuario,
    documento_id: int,
    dados: DadosDocumentoTextual,
    correlacao: str,
) -> DocumentoTextualPublico:
    """Atualiza e audita um documento existente do tenant."""
    _exigir_administrador(empresa=empresa, ator=ator)
    objeto = DocumentoTextual.objects.select_for_update().get(
        pk=documento_id, empresa=empresa, excluido_em__isnull=True
    )
    antes = _snapshot(objeto)
    for nome, valor in asdict(dados).items():
        setattr(objeto, nome, valor)
    objeto.full_clean()
    objeto.save()
    _auditar(
        empresa=empresa,
        objeto=objeto,
        acao=EventoAuditoria.Acao.ATUALIZACAO,
        antes=antes,
        ator=ator,
        correlacao=correlacao,
    )
    return _publicar_documento(objeto)


@transaction.atomic
def excluir_documento(
    *, empresa: Empresa, ator: Usuario, documento_id: int, correlacao: str
) -> None:
    """Marca um documento como excluido sem apagar seu historico."""
    _exigir_administrador(empresa=empresa, ator=ator)
    objeto = DocumentoTextual.objects.select_for_update().get(
        pk=documento_id, empresa=empresa, excluido_em__isnull=True
    )
    antes = _snapshot(objeto)
    objeto.ativo = False
    objeto.excluido_em = timezone.now()
    objeto.save(update_fields=("ativo", "excluido_em", "atualizado_em"))
    _auditar(
        empresa=empresa,
        objeto=objeto,
        acao=EventoAuditoria.Acao.EXCLUSAO,
        antes=antes,
        ator=ator,
        correlacao=correlacao,
    )


@transaction.atomic
def criar_pergunta_frequente(
    *,
    empresa: Empresa,
    ator: Usuario,
    dados: DadosPerguntaFrequente,
    correlacao: str,
) -> PerguntaFrequentePublica:
    """Cria e audita uma FAQ na empresa autorizada."""
    _exigir_administrador(empresa=empresa, ator=ator)
    objeto = PerguntaFrequente(empresa=empresa, **asdict(dados))
    objeto.full_clean()
    objeto.save()
    _auditar(
        empresa=empresa,
        objeto=objeto,
        acao=EventoAuditoria.Acao.CRIACAO,
        antes={},
        ator=ator,
        correlacao=correlacao,
    )
    return _publicar_faq(objeto)


@transaction.atomic
def atualizar_pergunta_frequente(
    *,
    empresa: Empresa,
    ator: Usuario,
    pergunta_id: int,
    dados: DadosPerguntaFrequente,
    correlacao: str,
) -> PerguntaFrequentePublica:
    """Atualiza e audita uma FAQ existente do tenant."""
    _exigir_administrador(empresa=empresa, ator=ator)
    objeto = PerguntaFrequente.objects.select_for_update().get(
        pk=pergunta_id, empresa=empresa, excluido_em__isnull=True
    )
    antes = _snapshot(objeto)
    for nome, valor in asdict(dados).items():
        setattr(objeto, nome, valor)
    objeto.full_clean()
    objeto.save()
    _auditar(
        empresa=empresa,
        objeto=objeto,
        acao=EventoAuditoria.Acao.ATUALIZACAO,
        antes=antes,
        ator=ator,
        correlacao=correlacao,
    )
    return _publicar_faq(objeto)


@transaction.atomic
def excluir_pergunta_frequente(
    *, empresa: Empresa, ator: Usuario, pergunta_id: int, correlacao: str
) -> None:
    """Marca uma FAQ como excluida sem apagar seu historico."""
    _exigir_administrador(empresa=empresa, ator=ator)
    objeto = PerguntaFrequente.objects.select_for_update().get(
        pk=pergunta_id, empresa=empresa, excluido_em__isnull=True
    )
    antes = _snapshot(objeto)
    objeto.ativo = False
    objeto.excluido_em = timezone.now()
    objeto.save(update_fields=("ativo", "excluido_em", "atualizado_em"))
    _auditar(
        empresa=empresa,
        objeto=objeto,
        acao=EventoAuditoria.Acao.EXCLUSAO,
        antes=antes,
        ator=ator,
        correlacao=correlacao,
    )
