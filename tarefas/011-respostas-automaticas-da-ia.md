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

- [ ] Testar prompt com blocos claramente delimitados e ordem determinística.
- [ ] Testar que modo `HUMANO`, conversa finalizada, IA desativada ou configuração inválida não chama o provider.
- [ ] Testar lock/idempotência: duas tasks para a mesma mensagem criam no máximo uma resposta.
- [ ] Testar sucesso, timeout, limite, resposta vazia e conteúdo acima de 4.096 caracteres.
- [ ] Testar que falha gera mensagem de sistema/estado operacional, não mensagem falsa enviada ao cliente.
- [ ] Confirmar falhas antes da implementação.
- [ ] Implementar serviço transacional com rechecagem do modo imediatamente antes de persistir a saída.
- [ ] Manter o service independente de HTTP e schemas: task Celery passa UUIDs e correlação, enquanto futuras APIs chamam a mesma função de domínio.
- [ ] Registrar modelo e tokens para métricas, sem registrar prompt completo em log.
- [ ] Enfileirar o envio da tarefa 012 somente após commit da mensagem pendente.
- [ ] Executar testes e regressão.

## Critérios de aceite

- IA nunca responde após intervenção humana, inclusive sob concorrência.
- Uma entrada gera no máximo uma saída automática.
- Exceção externa é convertida para estado recuperável e log correlacionado.

**Commit sugerido:** `feat: gera respostas automaticas contextualizadas`
