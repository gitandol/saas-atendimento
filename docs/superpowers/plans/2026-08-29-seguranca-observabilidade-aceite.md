# Seguranca, Observabilidade e Aceite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Endurecer o MVP, propagar correlacao, publicar verificacoes de saude e provar o cenario de aceite com isolamento multitenant.

**Architecture:** Middleware e `contextvars` mantem a correlacao por requisicao; sinais do Celery e providers propagam o mesmo identificador. Seguranca permanece nos settings e nas fronteiras HTTP, enquanto verificacoes de dependencias ficam em services independentes da API. Testes de contrato, arquitetura e integracao exercitam comportamento real com somente OpenAI, Evolution e broker mockados.

**Tech Stack:** Python 3.13, Django 5.2, Django Ninja, Celery 5.6, pytest, coverage, import-linter e Docker Compose.

**Spec:** `tarefas/016-seguranca-observabilidade-e-aceite.md`

## Global Constraints

- Identificadores proprios em portugues sem acentos; nomes de protocolos externos preservados.
- Views e endpoints nao importam models; services nao importam `api` ou `views`.
- Nenhum log, fixture, auditoria ou documentacao versionada contem telefone, texto de mensagem, prompt ou segredo real.
- Testes nao acessam OpenAI, Evolution API, Redis ou broker reais.
- Cada comportamento de producao nasce de um teste observado em vermelho.
- A suite externa permanece marcada e condicionada a credenciais fora do Git.

---

### Task 1: Correlacao e logs JSON sanitizados

**Files:** `config/logging.py`, `apps/nucleo/middleware/correlacao.py`, settings, Celery, providers e `tests/test_observabilidade.py`.

**Interfaces:** Produz `obter_correlacao() -> str`, contexto por requisicao/tarefa, `FormatadorJsonSeguro` e cabecalho `X-Correlation-ID`.

- [ ] Escrever testes falhando para correlacao segura, resposta HTTP, propagacao aos providers e JSON sem campos sensiveis.
- [ ] Executar `pytest tests/test_observabilidade.py -q` e registrar o vermelho esperado.
- [ ] Implementar contexto, middleware, sinais Celery, headers dos providers e formatter/filtro minimos.
- [ ] Executar o arquivo e testes de providers/tasks ate verde; refatorar duplicacao mantendo verde.

### Task 2: Endurecimento HTTP e verificacoes de saude

**Files:** `apps/nucleo/services/verificacoes.py`, health endpoint/schema/service, settings e testes de seguranca/saude.

**Interfaces:** Produz `verificar_dependencias() -> EstadoDependencias`, `/api/v1/saude`, `/api/v1/saude/dependencias` e settings seguros.

- [ ] Escrever testes falhando para headers, cookies, hosts, CSRF, limite de corpo e autenticacao interna.
- [ ] Implementar somente settings e enforcement identificados pelo vermelho.
- [ ] Escrever testes falhando em que banco, Redis ou worker degradam independentemente sem derrubar `/saude`.
- [ ] Implementar service/schema/endpoint e executar os testes de seguranca e saude ate verde.

### Task 3: Contratos OpenAPI e fronteiras arquiteturais

**Files:** `tests/api/test_openapi.py`, teste de camadas, `pyproject.toml` e schemas/endpoints apenas se o contrato falhar.

**Interfaces:** Produz OpenAPI sem caminhos ou operation IDs duplicados, sem campos sensiveis e com erros documentados; import-linter cobre todos os apps.

- [ ] Escrever testes OpenAPI com campos proibidos e operacoes sem resposta de erro.
- [ ] Executar o vermelho e registrar as operacoes exatas.
- [ ] Corrigir apenas os contratos identificados e executar testes de API/arquitetura e `lint-imports` ate verde.

### Task 4: Isolamento multitenant e cenario ponta a ponta

**Files:** dois testes em `tests/integracao/` e services/tasks somente se o teste revelar defeito.

**Interfaces:** Consome login/CSRF, configuracoes, webhook, IA, Evolution, assumir, resposta manual e finalizar; produz evidencia de isolamento e auditoria.

- [ ] Escrever teste com duas empresas compartilhando identificadores externos e afirmar isolamento em persistencia, services e tasks.
- [ ] Executar o teste; se ja protegido, fazer mutation check em cada fronteira sem inventar producao.
- [ ] Escrever teste ponta a ponta pelas paginas/endpoints reais, mockando somente providers e broker.
- [ ] Observar o vermelho, corrigir lacunas minimas e executar os dois testes e suites afetadas ate verde.

### Task 5: Operacao, bootstrap e verificacao final

**Files:** `README.md`, ambiente, Compose, docs de API/operacao/funcionalidades e tarefa 016.

**Interfaces:** Produz instrucoes reproduziveis de implantacao, backup/restauracao, rotacao, webhook e monitoramento.

- [ ] Adicionar assercoes executaveis de Compose/configuracao antes de alterar bootstrap e observar o vermelho.
- [ ] Atualizar Compose e ambiente minimamente; escrever documentacao operacional com comandos literais e placeholders seguros.
- [ ] Executar deploy check, Ruff, cobertura >= 90%, import-linter, testes JS e build CSS.
- [ ] Registrar vermelho/verde, comandos, limitacoes e suite externa; inspecionar segredos, revisar, reverificar e criar o commit sugerido.
