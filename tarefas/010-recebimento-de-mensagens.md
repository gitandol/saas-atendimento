# Tarefa 010 — Recebimento idempotente de mensagens

**Objetivo:** receber webhook Evolution, validar, registrar e enfileirar processamento sem duplicidade.

**Dependências:** tarefas 008 e 009.

**Arquivos:**

- Criar: `apps/whatsapp/api/endpoints/webhook_evolution.py`, `apps/whatsapp/api/schemas/webhook_evolution.py`.
- Criar: `apps/whatsapp/services/{validar_webhook,normalizar_evento}.py`.
- Criar: `apps/whatsapp/services/receber_webhook.py`.
- Criar: `apps/whatsapp/tasks/processar_mensagem_recebida.py`.
- Modificar: `apps/whatsapp/api/router.py` e criar testes espelhados em `apps/whatsapp/tests/api/` e `services/`.
- Criar: `docs/api/webhook-evolution.md`.

**Produz:** endpoint Ninja `POST /api/v1/webhooks/evolution/<uuid_empresa>/<token>/` e `EventoMensagemRecebida` normalizado.

## Contrato normalizado

```python
@dataclass(frozen=True)
class EventoMensagemRecebida:
    """Representa somente os dados confiáveis usados pelo domínio."""
    identificador_externo: str
    numero_remetente: str
    nome_remetente: str
    texto: str
    enviado_pela_instancia: bool
    ocorrido_em: datetime
```

## Ciclo TDD

- [ ] Testar token inválido, configuração inativa, payload grande, JSON inválido, evento desconhecido e mensagem sem texto.
- [ ] Testar payload válido criando contato, conversa e mensagem uma única vez.
- [ ] Repetir exatamente o mesmo webhook e confirmar `200` sem nova mensagem nem nova tarefa.
- [ ] Testar que `enviado_pela_instancia=True` não aciona resposta automática, evitando loop.
- [ ] Mockar `.delay()` do Celery; não exigir broker real.
- [ ] Confirmar todos os testes falhando antes da implementação.
- [ ] Implementar endpoint fino que valida tamanho/tipo HTTP e delega autenticação, normalização, persistência idempotente e enfileiramento ao service; resposta deve ocorrer em até 2 segundos.
- [ ] Testar o endpoint como contrato externo e o service separadamente, comprovando que o módulo `api` não importa models nem tasks diretamente.
- [ ] Registrar correlação e logs estruturados sem texto integral/segredos.
- [ ] Executar testes unitários, teste de integração HTTP local e regressão.

## Critérios de aceite

- Webhook é idempotente e não confia em empresa fornecida dentro do payload.
- Mensagens de mídia são registradas como evento não suportado, sem quebrar o endpoint e sem resposta de IA.
- Falha de Celery após persistência pode ser reprocessada de forma segura.

**Commit sugerido:** `feat: recebe mensagens evolution com idempotencia`
