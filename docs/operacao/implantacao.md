# Implantacao

Configure `DJANGO_SETTINGS_MODULE=config.settings.producao`, `SECRET_KEY`, `IA_CHAVE_CRIPTOGRAFIA`, banco, Redis, hosts, origens CSRF e Evolution conforme `.env.example`. Nunca reutilize os defaults locais.

O proxy deve terminar TLS, enviar `X-Forwarded-Proto: https` e preservar `X-Correlation-ID`. Execute antes de cada release:

```bash
docker compose build
docker compose run --rm web python manage.py check --deploy --settings=config.settings.producao
docker compose run --rm web python manage.py migrate --noinput
docker compose run --rm web python manage.py collectstatic --noinput
docker compose up -d
docker compose ps
```

A rotacao de `SECRET_KEY` invalida sessoes e tokens de webhook. A rotacao de `IA_CHAVE_CRIPTOGRAFIA` exige recriptografar credenciais e snapshots restauraveis antes de remover a chave anterior; sem isso, revisoes historicas cifradas deixam de ser restauraveis. Rotacione chaves OpenAI/Evolution no fornecedor, atualize pela interface e revogue as antigas.
