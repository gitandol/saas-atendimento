"""Agrega endpoints HTTP do modulo WhatsApp."""

from ninja import Router

from apps.whatsapp.api.endpoints.configuracao import router as configuracao_router
from apps.whatsapp.api.endpoints.estado_conexao import router as estado_router
from apps.whatsapp.api.endpoints.qrcode import router as qrcode_router

router = Router()
router.add_router("", configuracao_router)
router.add_router("", qrcode_router)
router.add_router("", estado_router)
