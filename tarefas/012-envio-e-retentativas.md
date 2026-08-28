# Tarefa 012 — Envio e retentativas de mensagens

**Objetivo:** entregar respostas de IA e atendentes ao WhatsApp com status observável e repetição segura.

**Dependências:** tarefas 008, 009 e 011.

**Arquivos:**

- Criar: `apps/whatsapp/services/enviar_mensagem.py`.
- Criar: `apps/whatsapp/tasks/enviar_mensagem.py`.
- Criar: `apps/whatsapp/services/atualizar_status_entrega.py`.
- Modificar: normalizador/webhook para eventos de entrega.
- Criar: `apps/whatsapp/api/endpoints/reenvio_mensagem.py`, `apps/whatsapp/api/schemas/reenvio_mensagem.py`.
- Criar: testes espelhados.

**Produz:** `solicitar_envio(mensagem_id, correlacao)`, task idempotente `enviar_mensagem_whatsapp` e endpoint `POST /api/v1/whatsapp/mensagens/{id}/reenviar`.

## Ciclo TDD

- [x] Testar envio de mensagem `PENDENTE` com número normalizado, texto e UUID como chave de idempotência.
- [x] Testar transições válidas: `PENDENTE -> ENVIADA -> ENTREGUE` e `PENDENTE/ENVIADA -> FALHA`.
- [x] Testar que mensagem já enviada não é reenviada por task repetida.
- [x] Testar retentativas exponenciais em timeout, 429 e 5xx; não repetir 400/401 sem alteração de configuração.
- [x] Testar máximo de cinco tentativas e erro final sanitizado.
- [x] Testar atualização idempotente de recibo de entrega recebido por webhook.
- [x] Confirmar falhas antes da implementação.
- [x] Implementar task Celery com `autoretry_for` somente para exceções transitórias e jitter.
- [x] Auditar falha/reenvio manual e emitir logs/métricas por empresa sem conteúdo sensível.
- [x] Testar que o endpoint de reenvio apenas autoriza, converte o UUID e chama o service; elegibilidade, auditoria e enfileiramento ficam no service.
- [x] Executar testes e regressão.

## Critérios de aceite

- Painel pode distinguir pendente, enviada, entregue e falha.
- Retentativa nunca cria nova entidade `Mensagem`.
- Reenvio manual exige permissão e mantém histórico das tentativas.

**Commit sugerido:** `feat: envia mensagens com retentativas seguras`

## Registro de execução

- Data: 2026-08-27
- Vermelho observado: 12 testes falharam pela ausência dos services, task, endpoint, normalização de recibos e classificação permanente de HTTP 400; o teste de webhook também confirmou que recibos eram ignorados. Um segundo ciclo vermelho confirmou que somente a falha final, e não cada tentativa, possuía histórico persistente.
- Implementação realizada: envio idempotente pelo UUID, transições auditadas, cinco tentativas Celery com backoff exponencial e jitter, classificação de falhas transitórias e permanentes, recibos idempotentes pelo webhook e endpoint autenticado de reenvio da mesma `Mensagem`.
- Refatorações: códigos de erro externos foram sanitizados; logs e metadados de auditoria passaram a registrar empresa, correlação e resultado sem conteúdo da mensagem; cada tentativa automática ganhou uma revisão persistente.
- Comandos e resultados: testes focados `44 passed`; testes da task `3 passed`; `ruff check .` sem erros; `ruff format --check .` formatado; `python manage.py check` sem problemas; `uv run pytest` com `320 passed`.
- Commit: `feat: envia mensagens com retentativas seguras`
