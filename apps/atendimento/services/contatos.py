"""Cria e localiza contatos de forma idempotente por tenant."""

import re
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.atendimento.dto import ContatoDTO
from apps.atendimento.models import Contato
from apps.auditoria.models import EventoAuditoria
from apps.auditoria.services.registrar_alteracao import registrar_alteracao
from apps.contas.models import Usuario
from apps.empresas.models import Empresa


def normalizar_numero(numero_telefone: str) -> str:
    """Mantem somente digitos no identificador telefonico do contato."""
    numero = re.sub(r"\D", "", numero_telefone)
    if not numero:
        raise ValidationError({"numero_telefone": "O numero e obrigatorio."})
    return numero


def contato_para_dto(contato: Contato) -> ContatoDTO:
    """Converte o model persistido no contrato imutavel de leitura."""
    return ContatoDTO(
        id=contato.id,
        nome=contato.nome,
        numero_normalizado=contato.numero_normalizado,
        observacoes=contato.observacoes,
        primeiro_contato_em=contato.primeiro_contato_em,
        ultimo_contato_em=contato.ultimo_contato_em,
    )


def snapshot_contato(contato: Contato) -> dict[str, Any]:
    """Produz snapshot auditavel do contato sem objetos Django."""
    return {
        "nome": contato.nome,
        "numero_normalizado": contato.numero_normalizado,
        "observacoes": contato.observacoes,
        "primeiro_contato_em": (
            contato.primeiro_contato_em.isoformat()
            if contato.primeiro_contato_em
            else None
        ),
        "ultimo_contato_em": (
            contato.ultimo_contato_em.isoformat() if contato.ultimo_contato_em else None
        ),
        "excluido_em": contato.excluido_em.isoformat() if contato.excluido_em else None,
    }


@transaction.atomic
def obter_ou_criar_contato(
    *,
    empresa: Empresa,
    numero_telefone: str,
    nome: str,
    ator: Usuario | None,
    origem: str,
    correlacao: str,
) -> ContatoDTO:
    """Retorna o contato do numero ou cria e audita uma nova identidade."""
    type(empresa).objects.select_for_update().get(pk=empresa.pk)
    numero_normalizado = normalizar_numero(numero_telefone)
    existente = (
        Contato.objects.select_for_update()
        .filter(
            empresa=empresa,
            numero_normalizado=numero_normalizado,
        )
        .first()
    )
    if existente is not None:
        if existente.excluido_em is None:
            return contato_para_dto(existente)
        antes = snapshot_contato(existente)
        nome_normalizado = nome.strip()
        if nome_normalizado:
            existente.nome = nome_normalizado
        existente.excluido_em = None
        existente.save(update_fields=("nome", "excluido_em", "atualizado_em"))
        depois = snapshot_contato(existente)
        registrar_alteracao(
            empresa=empresa,
            objeto=existente,
            acao=EventoAuditoria.Acao.RESTAURACAO,
            antes=antes,
            depois=depois,
            campos_alterados=[
                campo for campo, valor in depois.items() if antes.get(campo) != valor
            ],
            ator=ator,
            origem=origem,
            correlacao=correlacao,
        )
        return contato_para_dto(existente)

    contato = Contato(
        empresa=empresa,
        nome=nome.strip(),
        numero_normalizado=numero_normalizado,
    )
    contato.full_clean()
    contato.save()
    depois = snapshot_contato(contato)
    registrar_alteracao(
        empresa=empresa,
        objeto=contato,
        acao=EventoAuditoria.Acao.CRIACAO,
        antes={},
        depois=depois,
        campos_alterados=list(depois),
        ator=ator,
        origem=origem,
        correlacao=correlacao,
    )
    return contato_para_dto(contato)
