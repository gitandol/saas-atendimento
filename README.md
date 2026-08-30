# SaaS de Atendimento por WhatsApp com IA

Monolito Django API-first para atendimento automatico e humano, integrado a OpenAI e Evolution API.

## Inicio rapido

Requisitos: Docker Engine com Compose v2 e portas 8000 e 8080 livres.

1. Copie `.env.example` para `.env`.
2. Troque todos os valores iniciados por `troque-` e mantenha `DJANGO_SETTINGS_MODULE=config.settings.desenvolvimento` no ambiente local.
3. Execute `docker compose up --build -d`.
4. Acompanhe `docker compose ps` ate `web`, `worker`, `postgres` e `redis` ficarem saudaveis.
5. Crie o administrador com `docker compose exec web python manage.py createsuperuser`.
6. Acesse `http://localhost:8000/entrar/`.

O container web aplica migrations e coleta estaticos antes do Gunicorn. A Evolution API local fica restrita a `127.0.0.1:8080`.

## Producao

Use `DJANGO_SETTINGS_MODULE=config.settings.producao`, HTTPS no proxy, segredos aleatorios e `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` com os dominios reais. Antes de publicar:

```bash
docker compose run --rm web python manage.py check --deploy --settings=config.settings.producao
docker compose run --rm web python manage.py migrate --noinput
docker compose run --rm web python manage.py collectstatic --noinput
```

Procedimentos completos: [implantacao](docs/operacao/implantacao.md), [backup](docs/operacao/backup.md), [recuperacao](docs/operacao/recuperacao.md), [webhooks](docs/operacao/webhooks.md) e [monitoramento](docs/operacao/monitoramento.md).

## Desenvolvimento e verificacao

```bash
source .venv/bin/activate
ruff check .
ruff format --check .
python manage.py check
pytest --cov=apps --cov-fail-under=90
lint-imports --config pyproject.toml
npm run test:js
npm run css:build
```

A suite `externa` usa credenciais configuradas fora do Git: `pytest -m externa`. Contratos HTTP e erros estão em [docs/api/contratos-e-erros.md](docs/api/contratos-e-erros.md).
