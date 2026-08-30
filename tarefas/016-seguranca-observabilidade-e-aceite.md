# Tarefa 016 — Segurança, observabilidade e aceite ponta a ponta

**Objetivo:** endurecer e validar o fluxo completo do MVP antes de disponibilizá-lo.

**Dependências:** tarefas 001 a 015.

**Arquivos:**

- Criar: `config/logging.py`, `apps/nucleo/middleware/correlacao.py`, `apps/nucleo/services/verificacoes.py`.
- Criar: `tests/integracao/test_fluxo_completo_atendimento.py`, `tests/integracao/test_isolamento_multitenant.py`.
- Criar: `tests/arquitetura/test_dependencias_de_camadas.py`, `tests/api/test_openapi.py`, `docs/api/contratos-e-erros.md`.
- Criar: `docs/operacao/{implantacao,backup,recuperacao,webhooks,monitoramento}.md`.
- Modificar: `.env.example`, `compose.yaml`, `README.md` e documentos funcionais afetados.

**Produz:** aplicação verificável, logs correlacionados, documentação operacional e evidência do cenário de aceite.

## Ciclo TDD e verificação

- [x] Escrever teste ponta a ponta pelas páginas e endpoints Ninja, com OpenAI/Evolution mockadas: login, configuração, webhook, resposta automática, envio, intervenção humana, resposta manual e finalização.
- [x] Escrever teste com duas empresas repetindo UUIDs externos e confirmar isolamento em modelos, views, serviços, cache e tasks.
- [x] Testar cabeçalhos seguros, CSRF, cookies `Secure/HttpOnly/SameSite`, hosts permitidos, limite de corpo, rate limit e redaction de logs.
- [x] Testar que toda operação interna exige sessão válida, empresa ativa e CSRF nas mutações; webhooks usam autenticação própria e não herdam sessão.
- [x] Testar o OpenAPI para rotas duplicadas, operation IDs instáveis, endpoints sem schema de erro e respostas que exponham campos sensíveis.
- [x] Executar import-linter e teste AST garantindo que `views` e `api` não importem models e que services não dependam da camada HTTP.
- [x] Testar healthchecks separados de web, banco, Redis e worker; dependências externas devem aparecer como degradadas sem derrubar `/saude/`.
- [x] Confirmar falhas antes dos ajustes finais.
- [x] Implementar ID de correlação propagado de HTTP para Celery e integrações.
- [x] Configurar logs JSON com empresa, conversa, mensagem, tarefa, duração e resultado, sem conteúdo de mensagens ou segredos.
- [x] Documentar variáveis de ambiente, migrations, coleta de estáticos, backup, restauração e rotação de chaves.
- [x] Executar `python manage.py check --deploy` com settings de produção e corrigir todos os alertas aplicáveis.
- [x] Executar `ruff check .`, `ruff format --check .`, `pytest --cov=apps --cov-fail-under=90` e `npm run css:build`.
- [ ] Executar teste manual com sandbox Evolution/OpenAI somente em suíte marcada `externa`, após configurar credenciais fora do Git.
- [x] Registrar comandos, resultados, limitações conhecidas e evidência do cenário de aceite.

## Critérios de aceite final

- O cenário da especificação `000` passa integralmente.
- Cobertura é de pelo menos 90% nos módulos próprios.
- Não há segredo, telefone, texto de mensagem ou prompt completo em logs, auditoria ou fixtures versionadas.
- Todas as telas possuem ajuda contextual, estados de erro e autorização testada; dados e ações trafegam pela Django Ninja API.
- Views apenas renderizam páginas, endpoints apenas tratam HTTP e services concentram todo comportamento de negócio.
- Backup/restauração foram ensaiados em ambiente não produtivo.
- O MVP pode ser iniciado do zero usando somente README, `.env` e Docker Compose.

**Commit sugerido:** `chore: valida seguranca operacao e aceite do mvp`

## Registro de execução — 2026-08-30

- TDD: falhas observadas antes das implementações de correlação, redaction, limites HTTP, healthchecks, OpenAPI, isolamento, fluxo integral e proteção cifrada de auditoria.
- `python manage.py check --deploy --settings=config.settings.producao`: sem alertas, com variáveis sintéticas.
- `ruff check .` e `ruff format --check .`: aprovados.
- `pytest --cov=apps --cov-fail-under=90 -q`: 401 aprovados, 1 ignorado, cobertura total 96,60%.
- `lint-imports --config pyproject.toml` e testes AST/OpenAPI: 2 contratos mantidos, 0 quebrados; 9 testes aprovados.
- `npm run test:js` e `npm run css:build`: 10 testes aprovados e CSS compilado em Node Linux.
- `docker compose config -q`: aprovado; probes separados para web, worker, PostgreSQL e Redis.
- Backup/restauração: dump de 74.933 bytes restaurado em `atendimento_restore_tarefa016`; 29 migrations e 19 tabelas verificadas; banco temporário removido e dump preservado em `/tmp/tarefa016-atendimento-20260830.dump`.
- Limitação conhecida: `pytest -m externa -q` selecionou 0 casos (402 desmarcados) e não há credenciais Evolution/OpenAI externas configuradas; nenhuma chamada real foi executada.
