# Recuperacao

O ensaio deve usar banco descartavel e nunca sobrescrever producao.

```bash
docker compose exec -T postgres createdb -U atendimento atendimento_restore
docker compose exec -T postgres pg_restore -U atendimento -d atendimento_restore --clean --if-exists < var/backups/atendimento.dump
docker compose exec -T postgres psql -U atendimento -d atendimento_restore -c "select count(*) from django_migrations"
docker compose exec -T postgres dropdb -U atendimento atendimento_restore
```

Depois de validar migrations e contagens esperadas, restaure no ambiente alvo durante janela aprovada, inicie web/worker e verifique `/api/v1/saude` e `/api/v1/saude/dependencias`. Documente tempo de restauração, RPO/RTO observado e qualquer divergencia.
