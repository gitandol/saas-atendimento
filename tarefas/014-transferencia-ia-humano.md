# Tarefa 014 — Transferência entre IA e atendimento humano

**Objetivo:** controlar de maneira atômica quem pode responder uma conversa.

**Dependências:** tarefas 011 e 013.

**Arquivos:**

- Criar: `apps/atendimento/services/{assumir_conversa,devolver_para_ia,finalizar_conversa,reabrir_conversa}.py`.
- Criar: `apps/atendimento/api/endpoints/acoes_conversa.py`, `apps/atendimento/api/schemas/acoes_conversa.py` e parciais HTMX.
- Modificar: `templates/atendimento/caixa_entrada.html` e ajuda contextual.
- Criar: testes espelhados.

**Produz:** transições explícitas e auditadas e endpoints `POST /api/v1/atendimento/conversas/{id}/{assumir|devolver-para-ia|finalizar|reabrir}`.

## Regras de transição

- `IA/ABERTA -> HUMANO/ABERTA`: atendente autorizado assume.
- `HUMANO/ABERTA -> IA/ABERTA`: atendente atual ou administrador devolve; não gera resposta retroativa.
- `*/ABERTA -> */FINALIZADA`: finaliza e impede envio manual/automático.
- `*/FINALIZADA -> IA/ABERTA` ou `HUMANO/ABERTA`: reabertura explícita; mensagem nova usa política definida no serviço.

## Ciclo TDD

- [ ] Testar cada transição válida e todas as transições recusadas.
- [ ] Testar concorrência: dois atendentes tentam assumir; apenas um vence e o outro recebe conflito `409`.
- [ ] Testar que task de IA iniciada antes da transferência revalida o lock e não persiste resposta depois dela.
- [ ] Testar permissões, isolamento, auditoria, revisão e restauração compatível com regras atuais.
- [ ] Confirmar falhas antes da implementação.
- [ ] Implementar serviços com `select_for_update()`, versão otimista e mensagens operacionais em português.
- [ ] Implementar endpoints que apenas autorizam, convertem schemas e chamam o service de cada transição; conflitos de versão retornam `409`.
- [ ] Implementar ações HTMX contra a API com confirmação para devolver/finalizar e atualização dos badges.
- [ ] Atualizar ajuda e executar testes, inclusive cenário concorrente em PostgreSQL.

## Critérios de aceite

- Nunca há dois atendentes responsáveis simultaneamente.
- IA não responde enquanto modo humano está ativo.
- Toda mudança informa ator, origem, justificativa opcional e correlação no histórico.

**Commit sugerido:** `feat: controla transferencia entre ia e humano`
