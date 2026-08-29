"""Agrega os endpoints HTTP do painel operacional."""

from ninja import Router

from apps.painel.api.endpoints.dashboard import router as dashboard_router

router = Router()
router.add_router("", dashboard_router)
