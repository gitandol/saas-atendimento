# Backup

Execute em ambiente nao produtivo primeiro e armazene o arquivo cifrado fora do host. O backup principal cobre PostgreSQL; preserve também o `.env` em cofre separado, nunca dentro do arquivo versionado.

```bash
mkdir -p var/backups
docker compose exec -T postgres pg_dump -U atendimento -d atendimento -Fc > var/backups/atendimento.dump
test -s var/backups/atendimento.dump
docker compose exec -T postgres pg_restore --list < var/backups/atendimento.dump
```

Registre data, tamanho, checksum, versão do PostgreSQL e responsável. Defina retenção e teste restauração periodicamente conforme [recuperacao](recuperacao.md).
