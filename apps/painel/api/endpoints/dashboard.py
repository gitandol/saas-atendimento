"""Expoe as metricas operacionais da empresa ativa."""

from dataclasses import asdict

from django.http import HttpRequest
from django.shortcuts import render
from django.utils import timezone
from ninja import Router
from ninja.responses import Status
from ninja.security import SessionAuth

from apps.empresas.services.empresa_ativa import (
    EmpresaAtivaAusente,
    exigir_empresa_ativa,
)
from apps.painel.api.schemas.dashboard import (
    ErroPainelSchema,
    MetricasAtendimentoSaidaSchema,
)
from apps.painel.services.metricas_atendimento import obter_metricas_do_dia

router = Router(tags=["painel"], auth=SessionAuth())


@router.get(
    "/painel/metricas",
    response={200: MetricasAtendimentoSaidaSchema, 403: ErroPainelSchema},
)
def consultar_metricas(request: HttpRequest):
    """Resolve o tenant e adapta as metricas para JSON ou parcial HTMX."""
    try:
        empresa = exigir_empresa_ativa(request)
    except EmpresaAtivaAusente:
        return Status(
            403,
            {"codigo": "permissao_negada", "mensagem": "Acesso negado."},
        )

    metricas = obter_metricas_do_dia(empresa=empresa, agora=timezone.now())
    if request.headers.get("HX-Request") == "true":
        return render(
            request,
            "painel/parciais/metricas.html",
            {"metricas": metricas},
        )
    return asdict(metricas)
