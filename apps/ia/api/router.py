"""Agrega endpoints HTTP do modulo de inteligencia artificial."""

from ninja import Router

from apps.ia.api.endpoints.configuracao_ia import router as configuracao_router
from apps.ia.api.endpoints.conhecimento import router as conhecimento_router
from apps.ia.api.endpoints.perguntas_frequentes import router as perguntas_router

router = Router()
router.add_router("", configuracao_router)
router.add_router("", conhecimento_router)
router.add_router("", perguntas_router)
