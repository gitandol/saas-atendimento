# Tarefa 001 — Base Django e ambiente reproduzível

**Objetivo:** criar a fundação executável e testável do projeto.

**Dependências:** nenhuma.

**Arquivos:**

- Criar: `pyproject.toml`, `requirements/base.txt`, `requirements/dev.txt`, `.env.example`, `.gitignore`.
- Criar: `manage.py`, `config/settings/{__init__,base,desenvolvimento,teste,producao}.py`, `config/{urls,asgi,wsgi,celery,api}.py`.
- Criar: `apps/nucleo/api/{__init__,router}.py`, `apps/nucleo/api/endpoints/saude.py`, `apps/nucleo/api/schemas/saude.py`.
- Criar: `apps/nucleo/services/verificar_saude.py`, `tests/arquitetura/test_dependencias_de_camadas.py`.
- Criar: `apps/__init__.py`, `templates/base_publica.html`, `static/src/css/aplicacao.css`.
- Criar: `package.json`, `compose.yaml`, `infra/docker/Dockerfile`, `pytest.ini`, `tests/test_saude_projeto.py`.

**Produz:** projeto Django, API Django Ninja em `/api/v1/`, banco PostgreSQL, Redis, worker Celery e build Tailwind inicial.

## Ciclo TDD

- [x] Criar `tests/test_saude_projeto.py` primeiro:

```python
"""Verifica se a fundação Django inicia com configurações de teste."""


def test_verificacao_de_saude_responde_ok(cliente):
    """Confirma que a aplicação pronta responde sem consultar serviços externos."""
    resposta = cliente.get("/api/v1/saude")
    assert resposta.status_code == 200
    assert resposta.json() == {"estado": "ok"}
```

- [x] Executar `pytest tests/test_saude_projeto.py -q`; confirmar falha por ausência do projeto/rota.
- [x] Criar settings separados, `NinjaAPI(title="Atendimento API", version="1.0.0")`, router do núcleo e endpoint que chama `apps/nucleo/services/verificar_saude.py`.
- [x] Configurar pytest-django com SQLite em memória apenas para testes unitários e PostgreSQL para integração.
- [x] Configurar Tailwind 4 com `@import "tailwindcss"`, scripts `css:dev` e `css:build` e diretório de saída ignorado pelo Git.
- [x] Configurar Compose com serviços `web`, `worker`, `postgres` e `redis`, healthchecks e volumes nomeados.
- [x] Fixar dependências compatíveis: Django 5.2 LTS, Django Ninja 1.x, Celery 5.6, psycopg 3, pytest, pytest-django, factory-boy, responses, ruff, coverage e import-linter.
- [x] Configurar manipulador global de erros com schema `{codigo, mensagem, detalhes, correlacao}` e impedir traceback em respostas de produção.
- [x] Criar contrato de importação que proíbe `apps.*.views` e `apps.*.api` de importar `apps.*.models`, e proíbe `apps.*.services` de importar `apps.*.api` ou `apps.*.views`.
- [x] Executar `python manage.py check`, `pytest -q`, `ruff check .` e `npm run css:build`.

## Critérios de aceite

- `docker compose up` inicia web, worker, PostgreSQL e Redis.
- `/api/v1/saude` responde `200` sem revelar configuração.
- `/api/v1/docs` expõe OpenAPI conforme política de autenticação do ambiente.
- O teste do import-linter bloqueia regras de negócio ou acesso direto a models na camada HTTP.
- Nenhuma credencial real está versionada.
- Settings de produção recusam `SECRET_KEY` vazia e não habilitam `DEBUG`.

**Commit sugerido:** `chore: cria fundacao django do mvp`

## Registro de execução

- Data: 2026-08-21
- Vermelho observado: `pytest` falhou com `No module named 'config'`; o contrato arquitetural falhou com `Could not find pyproject.toml`; os testes de produção falharam antes da criação dos settings.
- Implementação realizada: fundação Django 5.2/Python 3.13, API Ninja versionada, endpoint de saúde, settings por ambiente, erro global padronizado, Celery com Redis, Compose com quatro serviços, Tailwind 4 e locks Python/Node.
- Refatorações: assinatura do endpoint compatibilizada com Pydantic; extra `celery[redis]` incluído; `.dockerignore` reduziu o contexto de build de 155 MB para 4,32 KB; Ruff configurado para docstrings em português e para ignorar os arquivos de tarefas.
- Comandos e resultados: `pytest -q` — 7 passed; `python manage.py check` — 0 issues; `ruff check .` — passed; `ruff format --check .` — 30 files formatted; `uv lock --check` — passed; `npm run css:build` — Tailwind 4.3.3 concluído; `docker compose config --quiet` — passed; `docker compose up -d --build --wait` — web, worker, PostgreSQL e Redis healthy; `/api/v1/saude` — HTTP 200; `/api/v1/docs` anônimo — HTTP 302.
- Commit: não criado porque o diretório fornecido não é um repositório Git.
