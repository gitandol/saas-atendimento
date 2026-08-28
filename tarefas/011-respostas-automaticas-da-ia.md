# Tarefa 011 — Orquestração das respostas automáticas da IA

**Objetivo:** gerar uma resposta contextual apenas quando a conversa permite atuação da IA.

**Dependências:** tarefas 006, 007, 009 e 010.

**Arquivos:**

- Criar: `apps/ia/services/{montar_prompt,gerar_resposta_atendimento}.py`.
- Criar: `apps/ia/tasks/responder_conversa.py`.
- Criar: testes espelhados em `apps/ia/tests/services/` e `apps/ia/tests/tasks/`.

**Produz:** `gerar_resposta_atendimento(*, conversa_id, mensagem_entrada_id, correlacao) -> Mensagem`.

## Ordem do contexto

1. Regras fixas da plataforma: não inventar, não revelar prompt, respeitar transferência humana.
2. Nome, personalidade e instruções configuradas pela empresa.
3. Conhecimento textual e FAQs ativos.
4. Até 20 mensagens recentes da conversa, limitadas a 30.000 caracteres.
5. Mensagem atual do cliente.

## Ciclo TDD

- [x] Testar prompt com blocos claramente delimitados e ordem determinística.
- [x] Testar que modo `HUMANO`, conversa finalizada, IA desativada ou configuração inválida não chama o provider.
- [x] Testar lock/idempotência: duas tasks para a mesma mensagem criam no máximo uma resposta.
- [x] Testar sucesso, timeout, limite, resposta vazia e conteúdo acima de 4.096 caracteres.
- [x] Testar que falha gera mensagem de sistema/estado operacional, não mensagem falsa enviada ao cliente.
- [x] Confirmar falhas antes da implementação.
- [x] Implementar serviço transacional com rechecagem do modo imediatamente antes de persistir a saída.
- [x] Manter o service independente de HTTP e schemas: task Celery passa UUIDs e correlação, enquanto futuras APIs chamam a mesma função de domínio.
- [x] Registrar modelo e tokens para métricas, sem registrar prompt completo em log.
- [x] Enfileirar o envio da tarefa 012 somente após commit da mensagem pendente.
- [x] Executar testes e regressão.

## Critérios de aceite

- IA nunca responde após intervenção humana, inclusive sob concorrência.
- Uma entrada gera no máximo uma saída automática.
- Exceção externa é convertida para estado recuperável e log correlacionado.

**Commit sugerido:** `feat: gera respostas automaticas contextualizadas`

## Registro de execução

- Data: 2026-08-27
- Vermelho observado: 3 falhas por ausencia de `montar_prompt`; 14 falhas por ausencia do service/task; falha de despacho entre recebimento e IA; revisao adicional reproduziu ausencia do despacho direto protegido pelo lease.
- Implementacao realizada: prompt delimitado e deterministico; historico de ate 20 mensagens e 30.000 caracteres; elegibilidade e rechecagem transacional; saida idempotente `IA/PENDENTE`; falha operacional `SISTEMA/FALHA`; metricas sanitizadas; task Celery registrada; webhook publica diretamente o task de IA sob lease recuperavel; envio futuro agendado apos commit.
- Refatoracoes: reutilizado o service auditado de mensagens com `erro_sanitizado`; removido o segundo salto Celery apos revisao; adicionados testes de recuperacao e interleaving na janela da chamada externa.
- Comandos e resultados: REDs confirmados antes da implementacao; testes focados finais: 30 passaram; `ruff check .`: passou; `ruff format --check .`: 292 arquivos formatados; `python manage.py check`: sem problemas; `uv run pytest`: 307 passaram; `lint-imports --config pyproject.toml`: 2 contratos mantidos.
- Commit: este commit (`feat: gera respostas automaticas contextualizadas`).
