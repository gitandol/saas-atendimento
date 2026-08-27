# Evolution API Local Design

## Objetivo

Incluir uma Evolution API operacional no mesmo ambiente Docker Compose do SaaS, permitindo que a tela existente de configuração do WhatsApp use `http://evolution:8080` sem depender de uma instalação externa. A Evolution terá banco PostgreSQL exclusivo, compartilhará o Redis existente com isolamento lógico e continuará acessível diretamente no host somente para diagnóstico local.

## Escopo

O trabalho adicionará os serviços `evolution` e `evolution-postgres`, volumes próprios, variáveis documentadas, autorização explícita do host Docker interno e verificações de subida. A tela, os endpoints Ninja, o modelo `ConfiguracaoWhatsApp` e o provider criados na tarefa 008 serão preservados e ajustados apenas onde necessário para aceitar o destino interno gerenciado.

Não serão incluídos Evolution Manager, proxy reverso público, TLS terminando dentro do container, alta disponibilidade, múltiplas réplicas nem provisionamento automático de uma configuração para cada empresa. O operador continuará definindo o nome da instância e confirmando as ações pela tela do SaaS.

## Topologia Docker

O `compose.yaml` ganhará:

- `evolution-postgres`, baseado em `postgres:15-alpine`, seguindo a versão usada pelo Compose oficial da Evolution API. Terá database, usuário, senha, healthcheck e volume exclusivos.
- `evolution`, baseado na tag versionada `evoapicloud/evolution-api:v2.3.7`. Dependerá do PostgreSQL exclusivo e do Redis existente, publicará `127.0.0.1:8080:8080` e persistirá sessões no volume `evolution_instances`.
- O Redis compartilhado será acessado por `redis://redis:6379/6`, com prefixo `evolution`, sem misturar chaves com o Django/Celery, que continuam no database `/0`.
- O serviço `web` receberá o host interno permitido e a URL padrão da Evolution. O Django não dependerá da saúde da Evolution para iniciar; indisponibilidade continuará sendo traduzida pelo provider em erro de domínio.

O banco da Evolution ficará isolado do banco `atendimento`. Remover ou migrar a Evolution não alterará tabelas Django, e uma falha de schema da Evolution não bloqueará migrações do SaaS.

## Configuração e segredos

O `.env.example` documentará:

```dotenv
EVOLUTION_API_KEY=troque-por-uma-chave-longa-e-aleatoria
EVOLUTION_POSTGRES_DB=evolution
EVOLUTION_POSTGRES_USER=evolution
EVOLUTION_POSTGRES_PASSWORD=troque-esta-senha
EVOLUTION_INTERNAL_URL=http://evolution:8080
WHATSAPP_HOSTS_INTERNOS_PERMITIDOS=evolution
```

O Compose passará `AUTHENTICATION_API_KEY`, `DATABASE_PROVIDER=postgresql`, `DATABASE_CONNECTION_URI`, `CACHE_REDIS_ENABLED=true`, `CACHE_REDIS_URI`, `CACHE_REDIS_PREFIX_KEY=evolution`, `SERVER_TYPE=http`, `SERVER_PORT=8080` e `SERVER_URL` para a Evolution.

A chave global da Evolution permanecerá no `.env`. Para manter o contrato existente da tarefa 008, o operador informará essa chave uma vez na tela do WhatsApp; o SaaS a armazenará cifrada. A chave não será renderizada de volta, registrada em auditoria ou colocada no JavaScript.

## Acesso interno e SSRF

Hoje o provider rejeita corretamente qualquer DNS resolvido para endereço privado. O host Docker `evolution` será a única exceção explícita.

As regras serão:

1. Hosts não listados continuam exigindo HTTPS em produção e endereços DNS globais.
2. Somente nomes presentes em `WHATSAPP_HOSTS_INTERNOS_PERMITIDOS` podem resolver para IP privado.
3. HTTP sem TLS será aceito apenas para um host interno explicitamente permitido.
4. `localhost`, IPs literais privados, metadata e redirects continuarão bloqueados.
5. A allowlist será aplicada tanto ao salvar a configuração quanto imediatamente antes de cada chamada do provider.

Assim, a rede Docker funciona sem transformar a exceção em permissão genérica para SSRF.

## Fluxo do operador

1. O ambiente sobe com `docker compose up -d --build`.
2. O operador acessa `/whatsapp/configuracao/`.
3. Informa `http://evolution:8080`, um nome único de instância e a mesma chave definida em `EVOLUTION_API_KEY`.
4. Salva, confirma **Conectar** e solicita o QR Code.
5. Lê o QR Code no WhatsApp e acompanha o estado normalizado pela tela.

A porta `8080` poderá ser usada no host para diagnóstico, mas o navegador do SaaS nunca chamará a Evolution diretamente.

## Testes e verificação

O desenvolvimento seguirá RED-GREEN-REFACTOR:

- teste de settings para normalização da allowlist interna;
- testes de URL garantindo que apenas `evolution` aceita HTTP/IP privado resolvido;
- teste do provider confirmando que outros hosts privados continuam bloqueados;
- regressão completa dos 188 testes existentes;
- `docker compose config` para validar o Compose resolvido;
- `docker compose pull evolution evolution-postgres` e subida real dos serviços;
- migrações Django, `docker compose ps` e chamada de saúde à porta 8080;
- `ruff check .`, `ruff format --check .`, `python manage.py check` e `pytest`.

## Operação e recuperação

Os volumes `evolution_instances` e `evolution_postgres_data` serão persistentes. `docker compose down` preservará dados; a remoção deliberada exigirá `docker compose down -v`. A tag da imagem ficará fixada em `v2.3.7`, evitando atualização implícita. Atualizações futuras exigirão alterar a tag, revisar notas de versão e validar backup/migração do banco exclusivo.
