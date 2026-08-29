"""Schemas de saida das metricas operacionais."""

from ninja import Schema


class MetricasAtendimentoSaidaSchema(Schema):
    """Publica o retrato operacional sem detalhes de persistencia."""

    conversas_abertas: int
    conversas_ia: int
    conversas_humano: int
    mensagens_recebidas_hoje: int
    mensagens_enviadas_hoje: int
    mensagens_com_falha: int
    estado_openai: str
    estado_evolution: str


class ErroPainelSchema(Schema):
    """Representa falha publica de autorizacao do painel."""

    codigo: str
    mensagem: str
