"""Agrega endpoints HTTP do modulo de inteligencia artificial."""

from ninja import Router

from apps.ia.api.endpoints.configuracao_ia import router as configuracao_router

router = Router()
router.add_router("", configuracao_router)
