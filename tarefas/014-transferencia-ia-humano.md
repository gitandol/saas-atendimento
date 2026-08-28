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

- [x] Testar cada transição válida e todas as transições recusadas.
- [x] Testar concorrência: dois atendentes tentam assumir; apenas um vence e o outro recebe conflito `409`.
- [x] Testar que task de IA iniciada antes da transferência revalida o lock e não persiste resposta depois dela.
- [x] Testar permissões, isolamento, auditoria, revisão e restauração compatível com regras atuais.
- [x] Confirmar falhas antes da implementação.
- [x] Implementar serviços com `select_for_update()`, versão otimista e mensagens operacionais em português.
- [x] Implementar endpoints que apenas autorizam, convertem schemas e chamam o service de cada transição; conflitos de versão retornam `409`.
- [x] Implementar ações HTMX contra a API com confirmação para devolver/finalizar e atualização dos badges.
- [x] Atualizar ajuda e executar testes, inclusive cenário concorrente em PostgreSQL.

## Critérios de aceite

- Nunca há dois atendentes responsáveis simultaneamente.
- IA não responde enquanto modo humano está ativo.
- Toda mudança informa ator, origem, justificativa opcional e correlação no histórico.

**Commit sugerido:** `feat: controla transferencia entre ia e humano`

## Registro de execução

- Data: 2026-08-28
- Vermelho observado: 12 falhas iniciais por services, rotas, autorização e controles ausentes; restauração regredia a versão e não restaurava FK; PostgreSQL revelou FOR UPDATE inválido com OUTER JOIN; controles e submit sem botão falharam nos testes JavaScript antes da implementação.
- Implementação realizada: versão otimista e locks por conversa; quatro transições autorizadas e auditadas; justificativa no histórico; restauração monotônica; bloqueio central de respostas indevidas; endpoints POST; parcial HTMX, confirmações, badges e política de reabertura; ajuda contextual.
- Refatorações: removido finalizador legado sem autorização; invariável do condutor centralizada em registrar_mensagem; lock limitado à linha de conversa; decisões de UI extraídas para funções puras testáveis.
- Comandos e resultados: pytest -q — 360 passaram e 1 cenário PostgreSQL foi reservado; cenário concorrente isolado em PostgreSQL — 1 passou; testes JavaScript — 6 passaram; ruff check ., ruff format --check ., makemigrations --check --dry-run e manage.py check — sem erros.
- Commit: `feat: controla transferencia entre ia e humano`
