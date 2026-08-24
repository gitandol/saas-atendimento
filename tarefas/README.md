# Plano de Implementação do MVP de Atendimento por WhatsApp com IA

> **Para agentes executores:** use `superpowers:test-driven-development` em cada tarefa e `superpowers:verification-before-completion` antes de marcá-la como concluída. Execute um arquivo por vez, na ordem numérica.

**Objetivo:** entregar um SaaS Django no qual uma empresa conecta um WhatsApp pela Evolution API, configura a OpenAI e atende clientes por IA ou intervenção humana.

**Arquitetura:** monólito modular Django, API-first e com isolamento lógico por empresa. Templates Django renderizam somente a estrutura visual; Tailwind CSS, HTMX e Alpine.js consomem a API versionada construída com Django Ninja. Endpoints validam o contrato HTTP e delegam todo comportamento aos services; PostgreSQL persiste os dados; Redis e Celery processam mensagens; integrações externas ficam atrás de providers.

**Stack:** Python 3.13, Django 5.2 LTS, Django Ninja 1.x, PostgreSQL 17+, Redis 7.2+, Celery 5.6, pytest, Tailwind CSS 4, HTMX 2 e Alpine.js 3, Docker Compose.

## Restrições globais

- Usar português sem acentos nos identificadores Python e nas colunas próprias do banco: `Empresa`, `Conversa`, `criado_em`, `numero_telefone`.
- Preservar nomes exigidos por protocolos externos, como `webhook`, `payload`, cabeçalhos HTTP e campos da Evolution API/OpenAI.
- Organizar `models`, `views`, `forms`, `services`, `tasks`, `integrations`, `urls` e `tests` como pacotes por responsabilidade; não criar arquivos genéricos crescentes.
- Views Django renderizam somente páginas-base e não consultam models nem executam regras de negócio.
- Toda leitura e mutação dinâmica da interface usa endpoints versionados em `/api/v1/`, consumidos por HTMX ou JavaScript.
- Endpoints Django Ninja autenticam, autorizam, validam schemas, chamam um service e convertem resultados ou exceções de domínio em respostas HTTP; não acessam models diretamente.
- Services concentram consultas, regras de negócio, transações, isolamento por empresa e auditoria; não importam módulos de `api` ou `views`.
- Schemas Django Ninja pertencem à fronteira HTTP; services recebem tipos de domínio, dataclasses ou argumentos explícitos e não dependem de schemas Pydantic.
- Integrações encapsulam APIs externas; tasks Celery apenas coordenam services reutilizáveis.
- Autenticação web usa sessão Django com CSRF; endpoints operacionais não aceitam autenticação anônima.
- A API publica OpenAPI em rota autenticada para endpoints internos e documentação separada para webhooks externos.
- Todo módulo, classe, função, método e teste deve possuir docstring de intenção e contrato.
- Aplicar TDD: teste falhando, implementação mínima, refatoração e regressão.
- Testes automatizados não acessam OpenAI, Evolution API ou Redis reais; usar mocks apenas nas fronteiras externas.
- Toda consulta e mutação de negócio deve respeitar a empresa ativa.
- Toda alteração relevante gera `EventoAuditoria` e `RevisaoObjeto`; segredos nunca entram em snapshots ou logs.
- Toda tela funcional possui link visível `Ajuda` e Markdown correspondente em `docs/funcionalidades/`.
- Cada tema visual deve funcionar nos modos claro e escuro e respeitar contraste WCAG AA.
- O produto inicial aceita somente mensagens de texto e uma instância de WhatsApp por empresa.
- Cada tarefa termina com atualização de seu registro de execução e um commit pequeno.

## Estrutura alvo

```text
config/
apps/
  <modulo>/
    api/
      endpoints/
      schemas/
      router.py
    views/paginas/
    services/
    models/
    integrations/
    tasks/
    tests/
templates/
static/src/css/
static/src/js/
docs/funcionalidades/
tests/integracao/
infra/
tarefas/
```

## Ordem de execução

Antes de iniciar, leia a [especificação validada do MVP](000-especificacao-do-mvp.md).

1. [001 — Base Django e ambiente](001-base-django-e-ambiente.md)
2. [002 — Empresas, usuários e isolamento](002-empresas-usuarios-e-isolamento.md)
3. [003 — Auditoria, revisões e ajuda](003-auditoria-revisoes-e-ajuda.md)
4. [004 — Layout, claro/escuro e cinco temas](004-layout-e-temas.md)
5. [005 — Configuração da empresa](005-configuracao-da-empresa.md)
6. [006 — Configuração e provider de IA](006-configuracao-e-provider-de-ia.md)
7. [007 — Conhecimento textual e FAQ](007-conhecimento-textual-e-faq.md)
8. [008 — Conexão com Evolution API](008-conexao-com-evolution-api.md)
9. [009 — Contatos, conversas e mensagens](009-dominio-de-atendimento.md)
10. [010 — Recebimento idempotente de mensagens](010-recebimento-de-mensagens.md)
11. [011 — Orquestração das respostas da IA](011-respostas-automaticas-da-ia.md)
12. [012 — Envio e retentativas no WhatsApp](012-envio-e-retentativas.md)
13. [013 — Caixa de entrada funcional](013-caixa-de-entrada.md)
14. [014 — Transferência entre IA e humano](014-transferencia-ia-humano.md)
15. [015 — Dashboard operacional](015-dashboard-operacional.md)
16. [016 — Segurança, observabilidade e aceite](016-seguranca-observabilidade-e-aceite.md)

## Definição de pronto de cada tarefa

- Ciclo vermelho/verde/refatorar registrado no final do arquivo da tarefa.
- Testes do módulo e suíte completa verdes.
- Migrações criadas, revisadas e aplicadas quando houver modelos.
- Docstrings e tipagem revisadas.
- Auditoria, autorização, isolamento e dados sensíveis testados quando aplicáveis.
- Contratos Django Ninja e fronteiras de importação entre `views`, `api`, `services` e `models` testados.
- Ajuda contextual e teste do link atualizados quando houver tela.
- `ruff check .`, `ruff format --check .`, `python manage.py check` e `pytest` executados.
- Commit sugerido criado somente depois da verificação.

## Registro de execução

Ao executar uma tarefa, acrescente ao final do próprio arquivo:

```markdown
## Registro de execução

- Data:
- Vermelho observado:
- Implementação realizada:
- Refatorações:
- Comandos e resultados:
- Commit:
```
