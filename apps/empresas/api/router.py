"""Agrega endpoints HTTP da configuracao empresarial."""

from ninja import Router

from apps.empresas.api.endpoints.configuracao_empresa import (
    router as configuracao_router,
)

router = Router()
router.add_router("", configuracao_router)
