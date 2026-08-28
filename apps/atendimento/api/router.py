"""Agrega os endpoints HTTP do modulo de atendimento."""

from ninja import Router

from apps.atendimento.api.endpoints.conversas import router as conversas_router
from apps.atendimento.api.endpoints.mensagens import router as mensagens_router

router = Router()
router.add_router("", conversas_router)
router.add_router("", mensagens_router)
