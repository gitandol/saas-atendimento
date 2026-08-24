"""Agrega endpoints HTTP pertencentes a contas."""

from ninja import Router

from apps.contas.api.endpoints.autenticacao import router as autenticacao_router
from apps.contas.api.endpoints.perfil import router as perfil_router
from apps.contas.api.endpoints.preferencia_visual import router as preferencia_router

router = Router()
router.add_router("/autenticacao", autenticacao_router)
router.add_router("/perfil", perfil_router)
router.add_router("/preferencias/visual", preferencia_router)
