# Tarefa 003 — Auditoria, revisões e ajuda contextual

**Objetivo:** criar infraestrutura comum de rastreabilidade, restauração e documentação funcional.

**Dependências:** tarefa 002.

**Arquivos:**

- Criar: `apps/auditoria/models/{evento_auditoria,revisao_objeto}.py`.
- Criar: `apps/auditoria/services/{registrar_alteracao,restaurar_revisao,sanitizar_snapshot}.py`.
- Criar: `apps/auditoria/views/paginas/historico.py`, `apps/auditoria/api/router.py`, `apps/auditoria/api/endpoints/{historico,restauracao}.py`, `apps/auditoria/api/schemas/{historico,restauracao}.py` e testes espelhados.
- Criar: `apps/ajuda/services/renderizar_markdown.py`, `apps/ajuda/views/paginas/topico.py`, `apps/ajuda/api/router.py`, `apps/ajuda/api/endpoints/topico.py`, `apps/ajuda/api/schemas/topico.py`.
- Criar: `templates/ajuda/topico.html`, `docs/funcionalidades/visao-geral.md`.

**Produz:** `registrar_alteracao(...)`, `restaurar_revisao(...)`, endpoints de histórico/restauração e rota de página `ajuda:topico`.

## Ciclo TDD

- [x] Testar que `registrar_alteracao` grava objeto, ação, antes/depois, campos, ator, origem, correlação e revisão sequencial na mesma transação.
- [x] Testar que chaves com nomes `senha`, `token`, `segredo`, `api_key` e `chave_api` viram `"[PROTEGIDO]"` no snapshot.
- [x] Testar imutabilidade dos eventos e restauração que cria novo evento `RESTORE`, sem apagar revisões anteriores.
- [x] Testar autorização por empresa e papel administrador nos endpoints de histórico/restauração.
- [x] Testar contrato JSON, paginação e códigos `403`, `404`, `409` e `422` sem expor snapshots protegidos.
- [x] Testar Markdown sanitizado, ausência de `<script>` e exibição da data de atualização pela página que consome o endpoint.
- [x] Confirmar os testes falhando antes de criar modelos e serviços.
- [x] Implementar serviços explícitos; não usar signals genéricos como única fonte de auditoria.
- [x] Criar componente reutilizável `templates/componentes/link_ajuda.html`.
- [x] Executar testes do módulo, migrations, check e regressão.

## Critérios de aceite

- Operação auditada e revisão são atômicas.
- Eventos não podem ser editados/excluídos pela interface comum.
- Restauração revalida empresa, permissão e invariantes atuais.
- Ajuda exige a mesma autenticação da funcionalidade chamadora.

**Commit sugerido:** `feat: cria auditoria revisoes e ajuda contextual`

## Registro de execução

- Data: 2026-08-24
- Vermelho observado: módulos ausentes produziram ciclos de 1, 4 e 6 falhas; `timezone.utc` produziu 2 falhas; revisão independente originou REDs de 5 falhas de isolamento/imutabilidade/estado/segredos, 3 falhas de append-only/OpenAPI e 1 falha de preservação do ator.
- Implementação realizada: modelos e quatro migrações de eventos/revisões; sanitização recursiva; registro transacional isolado por tenant; restauração validada; histórico paginado e restauração administrativos; páginas-shell; ajuda Markdown autenticada e sanitizada; componente de link e documentação funcional.
- Refatorações: consulta de histórico e resolução de revisão por ID isoladas em services; locks e estado anterior real na restauração; base append-only compartilhada; proteção ORM e triggers PostgreSQL; ator protegido; política ampliada de segredos; `datetime.UTC`; contratos de importação ampliados.
- Comandos e resultados: testes focados em ciclos RED/GREEN; suíte completa `77 passed`; `ruff check .` aprovado; `ruff format --check .` aprovado; migrações `auditoria.0001` a `0004` aplicadas; `makemigrations --check --dry-run` sem mudanças; `manage.py check` sem problemas.
- Commit: não criado porque o workspace fornecido não contém diretório `.git`.
