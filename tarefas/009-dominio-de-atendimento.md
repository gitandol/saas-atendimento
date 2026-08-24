# Tarefa 009 — Domínio de contatos, conversas e mensagens

**Objetivo:** persistir o histórico do atendimento com estados e invariantes claros.

**Dependências:** tarefas 002 e 003.

**Arquivos:**

- Criar: `apps/atendimento/models/{contato,conversa,mensagem}.py`.
- Criar: `apps/atendimento/services/{contatos,conversas,mensagens}.py`.
- Criar: `apps/atendimento/services/consultas/{listar_conversas,obter_historico}.py`.
- Criar: `apps/atendimento/dto/{contato,conversa,mensagem}.py`.
- Criar: factories e testes espelhados em `apps/atendimento/tests/`.

**Produz:** modelos centrais, DTOs imutáveis de leitura e services `obter_ou_criar_contato`, `obter_ou_abrir_conversa` e `registrar_mensagem`, consumíveis por API, Celery e integrações sem duplicar regras.

## Modelo mínimo

- `Contato`: empresa, nome, número normalizado, observações, primeiro/último contato e exclusão lógica.
- `Conversa`: empresa, contato, modo `IA|HUMANO`, estado `ABERTA|FINALIZADA`, atendente, última mensagem e contagem não lida.
- `Mensagem`: empresa, conversa, direção `ENTRADA|SAIDA`, autor `CLIENTE|IA|ATENDENTE|SISTEMA`, texto, identificador externo, status `RECEBIDA|PENDENTE|ENVIADA|ENTREGUE|FALHA`, erro sanitizado e datas.

## Ciclo TDD

- [ ] Testar unicidade de contato por `empresa + numero_normalizado` e de mensagem externa por `empresa + identificador_externo`.
- [ ] Testar abertura/reabertura da conversa e atualização atômica de última mensagem/não lidas.
- [ ] Testar ordenação estável por data e UUID, isolamento e exclusão lógica.
- [ ] Testar que texto vazio ou acima de 4.096 caracteres é rejeitado para envio do MVP.
- [ ] Confirmar falhas antes da implementação.
- [ ] Implementar enums, constraints e índices para lista de conversas e idempotência.
- [ ] Implementar serviços transacionais com ator, origem e correlação para auditoria.
- [ ] Fazer services de consulta retornarem dataclasses/DTOs do domínio, sem retornar QuerySets para endpoints ou depender de schemas Django Ninja.
- [ ] Executar migrations, explicar o plano dos índices e rodar regressão.

## Critérios de aceite

- Histórico mantém ordem e não duplica identificadores externos.
- Finalizar conversa não apaga mensagens; nova entrada pode reabri-la conforme serviço explícito.
- Consultas públicas sempre recebem empresa ativa.

**Commit sugerido:** `feat: cria dominio de atendimento`
