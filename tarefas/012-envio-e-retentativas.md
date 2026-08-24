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

- [ ] Testar envio de mensagem `PENDENTE` com número normalizado, texto e UUID como chave de idempotência.
- [ ] Testar transições válidas: `PENDENTE -> ENVIADA -> ENTREGUE` e `PENDENTE/ENVIADA -> FALHA`.
- [ ] Testar que mensagem já enviada não é reenviada por task repetida.
- [ ] Testar retentativas exponenciais em timeout, 429 e 5xx; não repetir 400/401 sem alteração de configuração.
- [ ] Testar máximo de cinco tentativas e erro final sanitizado.
- [ ] Testar atualização idempotente de recibo de entrega recebido por webhook.
- [ ] Confirmar falhas antes da implementação.
- [ ] Implementar task Celery com `autoretry_for` somente para exceções transitórias e jitter.
- [ ] Auditar falha/reenvio manual e emitir logs/métricas por empresa sem conteúdo sensível.
- [ ] Testar que o endpoint de reenvio apenas autoriza, converte o UUID e chama o service; elegibilidade, auditoria e enfileiramento ficam no service.
- [ ] Executar testes e regressão.

## Critérios de aceite

- Painel pode distinguir pendente, enviada, entregue e falha.
- Retentativa nunca cria nova entidade `Mensagem`.
- Reenvio manual exige permissão e mantém histórico das tentativas.

**Commit sugerido:** `feat: envia mensagens com retentativas seguras`
