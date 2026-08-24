"""Agrega endpoints HTTP pertencentes ao nucleo."""

from ninja import Router

from apps.nucleo.api.endpoints.saude import router as saude_router

router = Router()
router.add_router("", saude_router)
