"""Agrega endpoints HTTP de ajuda."""

from ninja import Router

from apps.ajuda.api.endpoints.topico import router as topico_router

router = Router()
router.add_router("", topico_router)
