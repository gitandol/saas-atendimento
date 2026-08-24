"""Agrega endpoints HTTP de auditoria."""

from ninja import Router

from apps.auditoria.api.endpoints.historico import router as historico_router
from apps.auditoria.api.endpoints.restauracao import router as restauracao_router

router = Router()
router.add_router("", historico_router)
router.add_router("", restauracao_router)
