"""Testa variantes usuais de nomes de segredos."""


def test_sanitiza_variantes_normalizadas_de_segredos() -> None:
    """Evita persistir credenciais com nomes externos comuns."""
    from apps.auditoria.services.sanitizar_snapshot import sanitizar_snapshot

    assert sanitizar_snapshot(
        {
            "password": "a",
            "access_token": "b",
            "client-secret": "c",
            "secretKey": "d",
        }
    ) == {
        "password": "[PROTEGIDO]",
        "access_token": "[PROTEGIDO]",
        "client-secret": "[PROTEGIDO]",
        "secretKey": "[PROTEGIDO]",
    }
