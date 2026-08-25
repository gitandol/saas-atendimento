# Tarefa 005 — Configuração da empresa

**Objetivo:** permitir que o administrador mantenha o perfil usado no atendimento e no prompt da IA.

**Dependências:** tarefas 003 e 004.

**Arquivos:**

- Modificar: `apps/empresas/models/empresa.py`.
- Criar: `apps/empresas/services/{obter_empresa,atualizar_empresa}.py`.
- Criar: `apps/empresas/api/router.py`, `apps/empresas/api/endpoints/configuracao_empresa.py`, `apps/empresas/api/schemas/configuracao_empresa.py`.
- Criar: `apps/empresas/views/paginas/configuracao_empresa.py`, `apps/empresas/urls/paginas.py`.
- Criar: `templates/empresas/configuracao.html`, `docs/funcionalidades/configuracao-da-empresa.md`.
- Testar: arquivos espelhados em `apps/empresas/tests/`.

**Produz:** `obter_empresa(*, empresa, ator)`, `atualizar_empresa(*, empresa, dados, ator, correlacao)` e endpoints `GET/PUT /api/v1/empresa`.

## Ciclo TDD

- [x] Testar schemas de entrada/saída com `nome`, `segmento`, `descricao`, `horario_atendimento`, `endereco`, `telefone`, `site`, `instrucoes_atendimento` e `atualizado_em`.
- [x] Testar validação de URL, limites de tamanho e normalização do telefone.
- [x] Testar que somente administrador da empresa ativa pode editar.
- [x] Testar que atualização cria evento e revisão sem registrar campos sensíveis.
- [x] Confirmar falhas antes de alterar modelo, schemas, services e endpoint.
- [x] Implementar atualização dentro de `transaction.atomic()`, com diff explícito para auditoria.
- [x] Criar página-shell sem consulta de negócio; carregar e salvar o formulário em seções pelos endpoints Ninja usando HTMX, com feedback e link Ajuda.
- [x] Testar que o endpoint apenas converte o schema em dados de domínio e chama o service; validação de concorrência e regras permanecem no service.
- [x] Executar migrations, testes do módulo e regressão.

## Critérios de aceite

- Dados persistidos reaparecem pelo endpoint e ficam disponíveis por service, não por acesso direto de view, endpoint ou integração.
- Atualização concorrente usa campo `atualizado_em` e rejeita versão obsoleta com mensagem compreensível.
- Histórico mostra valores anteriores/posteriores e permite restauração autorizada.

**Commit sugerido:** `feat: adiciona configuracao da empresa`


## Registro de execução

- Data: 2026-08-25
- Vermelho observado: 12 falhas para modelo/schemas ausentes; 6 para services ausentes; 7 para rotas/página ausentes; conflito 409 no fluxo GET→PUT por precisão do timestamp; assets HTMX/CSS inicialmente inexistentes.
- Implementação realizada: perfil completo de `Empresa`, migration, services isolados por tenant, autorização administrativa, concorrência otimista, auditoria atômica, GET/PUT Ninja, página-shell HTMX, ajuda contextual, navegação e assets locais.
- Refatorações: comparação de versão alinhada aos milissegundos publicados pela API; snapshots restauráveis com diff explícito; contratos de importação ampliados para a nova fronteira HTTP.
- Comandos e resultados: migration `empresas.0002_configuracao_empresa` aplicada no PostgreSQL via Compose; `pytest -q` com 132 testes aprovados; 4 testes JavaScript aprovados; Ruff, formatação e checks Django executados.
- Commit: `feat: adiciona configuracao da empresa`
