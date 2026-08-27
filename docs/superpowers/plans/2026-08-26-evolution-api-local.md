# Evolution API Local Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Subir uma Evolution API junto com o SaaS e permitir que o provider Django acesse com segurança o host Docker interno `http://evolution:8080`.

**Architecture:** O Compose adicionará `evolution` com PostgreSQL exclusivo e reutilizará o Redis atual no database `/6`. O Django aceitará HTTP e DNS privado somente para nomes explicitamente listados em `WHATSAPP_HOSTS_INTERNOS_PERMITIDOS`; todos os demais destinos manterão HTTPS, DNS global e redirects bloqueados.

**Tech Stack:** Docker Compose, Evolution API v2.3.7, PostgreSQL 15, Redis 7.4, Django 5.2, requests, pytest e Ruff.

**Spec:** `docs/superpowers/specs/2026-08-26-evolution-api-local-design.md`

## Global Constraints

- Fixar a imagem em `evoapicloud/evolution-api:v2.3.7`.
- Usar PostgreSQL exclusivo no serviço `evolution-postgres` e volume `evolution_postgres_data`.
- Compartilhar o Redis existente somente por `redis://redis:6379/6`, com prefixo `evolution`.
- Publicar a Evolution apenas em `127.0.0.1:8080:8080`.
- Aceitar HTTP e IP privado somente para hostname exato presente em `WHATSAPP_HOSTS_INTERNOS_PERMITIDOS`.
- Continuar bloqueando `localhost`, IP privado literal, metadata, redirects e DNS privado de hosts não permitidos.
- Nunca renderizar `EVOLUTION_API_KEY` no HTML, JavaScript, resposta HTTP ou auditoria.
- Preservar as alterações não relacionadas já existentes no worktree.

---

### Task 1: Allowlist segura e URL interna padrão

**Files:**
- Modify: `config/settings/base.py:116`
- Modify: `tests/test_configuracao_producao.py:1-52`
- Modify: `apps/whatsapp/services/configurar_instancia.py:99-137,221-226`
- Modify: `apps/whatsapp/integrations/evolution.py:54-110`
- Modify: `apps/whatsapp/tests/test_services_configuracao.py:115-153`
- Modify: `apps/whatsapp/tests/test_provider_evolution.py:204-224`

**Interfaces:**
- Consumes: `EVOLUTION_INTERNAL_URL` e `WHATSAPP_HOSTS_INTERNOS_PERMITIDOS` do ambiente.
- Produces: `settings.EVOLUTION_INTERNAL_URL: str`, `settings.WHATSAPP_HOSTS_INTERNOS_PERMITIDOS: frozenset[str]` e `ProviderEvolution(..., hosts_internos_permitidos: frozenset[str] | None = None)`.

- [ ] **Step 1: Escrever teste RED da normalização da allowlist**

Adicionar a `tests/test_configuracao_producao.py`:

```python
def test_settings_normalizam_hosts_internos_permitidos() -> None:
    """Normaliza caixa, espaços, ponto final e entradas vazias da allowlist."""
    ambiente = os.environ.copy()
    ambiente["WHATSAPP_HOSTS_INTERNOS_PERMITIDOS"] = (
        " Evolution. , OUTRO.INTERNO ,, "
    )
    resultado = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from config.settings.base import "
                "WHATSAPP_HOSTS_INTERNOS_PERMITIDOS as hosts; "
                "print(','.join(sorted(hosts)))"
            ),
        ],
        check=False,
        capture_output=True,
        env=ambiente,
        text=True,
    )

    assert resultado.returncode == 0
    assert resultado.stdout.strip() == "evolution,outro.interno"
```

Executar:

```bash
pytest tests/test_configuracao_producao.py::test_settings_normalizam_hosts_internos_permitidos -v
```

Expected: FAIL porque `WHATSAPP_HOSTS_INTERNOS_PERMITIDOS` ainda não existe.

- [ ] **Step 2: Escrever testes RED para URL interna e HTTP restrito**

Adicionar a `apps/whatsapp/tests/test_services_configuracao.py`:

```python
@pytest.mark.django_db
def test_configuracao_aceita_http_apenas_para_host_interno_permitido(settings) -> None:
    """Libera o DNS privado gerenciado sem abrir HTTP para outros destinos."""
    from apps.whatsapp.services.configurar_instancia import (
        ConfiguracaoWhatsAppInvalida,
        DadosConfiguracaoWhatsApp,
        atualizar_configuracao,
    )

    settings.DEBUG = True
    settings.IA_CHAVE_CRIPTOGRAFIA = "mestre-interna"
    settings.WHATSAPP_HOSTS_INTERNOS_PERMITIDOS = frozenset({"evolution"})
    empresa = Empresa.objects.create(nome="Empresa Evolution interna")
    ator = _membro(
        empresa,
        MembroEmpresa.Papel.ADMINISTRADOR,
        "evolution-interna@example.com",
    )
    interna = DadosConfiguracaoWhatsApp(
        url_base="http://EVOLUTION.:8080/",
        nome_instancia="empresa-interna",
        chave_api="chave",
    )
    externa_http = DadosConfiguracaoWhatsApp(
        url_base="http://evolution.example.com:8080",
        nome_instancia="empresa-externa",
        chave_api="chave",
    )

    resultado = atualizar_configuracao(
        empresa=empresa,
        ator=ator,
        dados=interna,
        correlacao="interna",
    )
    assert resultado.url_base == "http://EVOLUTION.:8080"
    with pytest.raises(ConfiguracaoWhatsAppInvalida):
        atualizar_configuracao(
            empresa=empresa,
            ator=ator,
            dados=externa_http,
            correlacao="externa-http",
        )
```

Adicionar ainda:

```python
@pytest.mark.django_db
def test_configuracao_vazia_publica_url_interna_padrao(settings) -> None:
    """Preenche a tela inicial sem expor qualquer credencial."""
    from apps.whatsapp.services.configurar_instancia import obter_configuracao

    settings.EVOLUTION_INTERNAL_URL = "http://evolution:8080"
    empresa = Empresa.objects.create(nome="Empresa sem configuracao")
    ator = _membro(
        empresa,
        MembroEmpresa.Papel.ADMINISTRADOR,
        "sem-configuracao@example.com",
    )

    resultado = obter_configuracao(empresa=empresa, ator=ator)

    assert resultado.url_base == "http://evolution:8080"
    assert resultado.chave_configurada is False
```

- [ ] **Step 3: Executar os testes de service e confirmar o RED**

Run:

```bash
pytest apps/whatsapp/tests/test_services_configuracao.py \
  -k "host_interno_permitido or url_interna_padrao" -v
```

Expected: FAIL porque HTTP externo ainda é aceito em `DEBUG=True` e a configuração vazia ainda publica `url_base=""`.

- [ ] **Step 4: Escrever teste RED do provider com DNS privado permitido**

Adicionar a `apps/whatsapp/tests/test_provider_evolution.py`:

```python
def test_provider_aceita_dns_privado_somente_para_host_interno_permitido() -> None:
    """Permite a rede Docker explicitamente confiada e preserva o bloqueio geral."""
    from apps.whatsapp.integrations.evolution import ProviderEvolution
    from apps.whatsapp.integrations.protocolos import EstadoConexao

    resposta = RespostaHTTPFalsa(
        200,
        {"instance": {"state": "open"}},
        content=b'{"instance":{"state":"open"}}',
    )
    provider = ProviderEvolution(
        url_base="http://evolution:8080",
        nome_instancia="empresa-1",
        chave_api="chave",
        cliente=ClienteHTTPFalso([resposta]),
        resolvedor=lambda _host, _porta: {"172.20.0.5"},
        hosts_internos_permitidos=frozenset({"evolution"}),
    )

    assert provider.consultar_estado() == EstadoConexao.CONECTADO
```

- [ ] **Step 5: Executar o teste do provider e confirmar o RED**

Run:

```bash
pytest apps/whatsapp/tests/test_provider_evolution.py::test_provider_aceita_dns_privado_somente_para_host_interno_permitido -v
```

Expected: FAIL com `TypeError` porque `hosts_internos_permitidos` ainda não existe.

- [ ] **Step 6: Implementar settings normalizados**

Adicionar ao final de `config/settings/base.py`:

```python
EVOLUTION_INTERNAL_URL = os.getenv(
    "EVOLUTION_INTERNAL_URL", "http://evolution:8080"
).rstrip("/")
WHATSAPP_HOSTS_INTERNOS_PERMITIDOS = frozenset(
    host.strip().rstrip(".").lower()
    for host in os.getenv(
        "WHATSAPP_HOSTS_INTERNOS_PERMITIDOS", "evolution"
    ).split(",")
    if host.strip()
)
```

- [ ] **Step 7: Implementar a regra de URL no service**

Em `apps/whatsapp/services/configurar_instancia.py`, criar:

```python
def _host_interno_permitido(host: str) -> bool:
    """Compara hostname normalizado com a allowlist gerenciada."""
    normalizado = host.rstrip(".").lower()
    return normalizado in settings.WHATSAPP_HOSTS_INTERNOS_PERMITIDOS
```

Na função `_validar_url`, substituir a escolha baseada em `DEBUG` por:

```python
host_interno = _host_interno_permitido(hostname)
if partes.scheme.lower() != "https" and not (
    partes.scheme.lower() == "http" and host_interno
):
    raise ConfiguracaoWhatsAppInvalida(
        "A URL da Evolution deve usar HTTPS ou um host interno permitido."
    )
```

Na publicação vazia, usar `settings.EVOLUTION_INTERNAL_URL` como `url_base`. Em `_obter_provider`, passar:

```python
hosts_internos_permitidos=settings.WHATSAPP_HOSTS_INTERNOS_PERMITIDOS,
```

- [ ] **Step 8: Implementar a exceção explícita no provider**

Estender `ProviderEvolution.__init__`:

```python
hosts_internos_permitidos: frozenset[str] | None = None,
```

Armazenar a forma normalizada:

```python
self.hosts_internos_permitidos = frozenset(
    host.rstrip(".").lower() for host in (hosts_internos_permitidos or ())
)
```

Em `_validar_destino_resolvido`, aceitar endereços privados somente quando o hostname normalizado estiver nesse conjunto:

```python
host_interno = host.rstrip(".").lower() in self.hosts_internos_permitidos
if not host_interno and any(not destino.is_global for destino in destinos):
    raise WhatsAppIndisponivel("O destino da Evolution API nao e permitido.")
```

Não alterar `allow_redirects=False`, streaming limitado ou tradução de timeouts.

- [ ] **Step 9: Executar todos os testes do módulo e de settings**

Run:

```bash
pytest apps/whatsapp/tests -q
pytest tests/test_configuracao_producao.py -q
```

Expected: PASS, incluindo os testes novos e todos os bloqueios SSRF existentes.

- [ ] **Step 10: Commit da allowlist**

```bash
git add config/settings/base.py \
  tests/test_configuracao_producao.py \
  apps/whatsapp/services/configurar_instancia.py \
  apps/whatsapp/integrations/evolution.py \
  apps/whatsapp/tests/test_services_configuracao.py \
  apps/whatsapp/tests/test_provider_evolution.py
git commit -m "feat: permite evolution interna gerenciada"
```

---

### Task 2: Serviços Docker da Evolution API

**Files:**
- Modify: `compose.yaml:1-80`
- Modify: `.env.example:1-11`
- Modify: `docs/funcionalidades/conexao-do-whatsapp.md:1-13`

**Interfaces:**
- Consumes: `EVOLUTION_API_KEY`, `EVOLUTION_POSTGRES_DB`, `EVOLUTION_POSTGRES_USER`, `EVOLUTION_POSTGRES_PASSWORD`, `EVOLUTION_INTERNAL_URL` e `WHATSAPP_HOSTS_INTERNOS_PERMITIDOS`.
- Produces: serviços Compose `evolution` e `evolution-postgres`, volumes `evolution_instances` e `evolution_postgres_data`, Evolution na porta local `8080` e URL interna `http://evolution:8080`.

- [ ] **Step 1: Executar validação RED do Compose ainda sem serviços**

Run:

```bash
docker compose config --format json | python -c '
import json, sys
dados = json.load(sys.stdin)
assert dados["services"]["evolution"]["image"] == "evoapicloud/evolution-api:v2.3.7"
assert dados["services"]["evolution-postgres"]["image"] == "postgres:15-alpine"
assert dados["services"]["evolution"]["environment"]["CACHE_REDIS_URI"] == "redis://redis:6379/6"
'
```

Expected: FAIL com `KeyError: 'evolution'`.

- [ ] **Step 2: Documentar variáveis no `.env.example`**

Acrescentar:

```dotenv
# Evolution API local gerenciada pelo Docker Compose.
EVOLUTION_API_KEY=troque-por-uma-chave-longa-e-aleatoria
EVOLUTION_POSTGRES_DB=evolution
EVOLUTION_POSTGRES_USER=evolution
EVOLUTION_POSTGRES_PASSWORD=troque-esta-senha
EVOLUTION_INTERNAL_URL=http://evolution:8080
WHATSAPP_HOSTS_INTERNOS_PERMITIDOS=evolution
```

- [ ] **Step 3: Adicionar PostgreSQL exclusivo ao Compose**

Adicionar a `compose.yaml`:

```yaml
  evolution-postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ${EVOLUTION_POSTGRES_DB:-evolution}
      POSTGRES_USER: ${EVOLUTION_POSTGRES_USER:-evolution}
      POSTGRES_PASSWORD: ${EVOLUTION_POSTGRES_PASSWORD:-evolution-local}
    volumes:
      - evolution_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 10
```

- [ ] **Step 4: Adicionar Evolution API ao Compose**

Adicionar:

```yaml
  evolution:
    image: evoapicloud/evolution-api:v2.3.7
    environment:
      SERVER_NAME: evolution
      SERVER_TYPE: http
      SERVER_PORT: 8080
      SERVER_URL: ${EVOLUTION_INTERNAL_URL:-http://evolution:8080}
      AUTHENTICATION_API_KEY: ${EVOLUTION_API_KEY:-evolution-local-api-key}
      DATABASE_PROVIDER: postgresql
      DATABASE_CONNECTION_URI: postgresql://${EVOLUTION_POSTGRES_USER:-evolution}:${EVOLUTION_POSTGRES_PASSWORD:-evolution-local}@evolution-postgres:5432/${EVOLUTION_POSTGRES_DB:-evolution}?schema=evolution_api
      DATABASE_CONNECTION_CLIENT_NAME: saas_atendimento
      CACHE_REDIS_ENABLED: "true"
      CACHE_REDIS_URI: redis://redis:6379/6
      CACHE_REDIS_PREFIX_KEY: evolution
      CACHE_REDIS_SAVE_INSTANCES: "false"
      DEL_INSTANCE: "false"
      CONFIG_SESSION_PHONE_CLIENT: Atendimento SaaS
      CONFIG_SESSION_PHONE_NAME: Chrome
    ports:
      - "127.0.0.1:8080:8080"
    volumes:
      - evolution_instances:/evolution/instances
    depends_on:
      evolution-postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
```

Adicionar ao serviço `web`:

```yaml
      EVOLUTION_INTERNAL_URL: ${EVOLUTION_INTERNAL_URL:-http://evolution:8080}
      WHATSAPP_HOSTS_INTERNOS_PERMITIDOS: ${WHATSAPP_HOSTS_INTERNOS_PERMITIDOS:-evolution}
```

Adicionar aos volumes raiz:

```yaml
  evolution_instances:
  evolution_postgres_data:
```

- [ ] **Step 5: Atualizar ajuda do operador**

Acrescentar a `docs/funcionalidades/conexao-do-whatsapp.md`:

```markdown
## Evolution local

No ambiente Docker do projeto, use `http://evolution:8080` como URL base. A chave API é o valor de `EVOLUTION_API_KEY` do arquivo `.env`. A porta `http://localhost:8080` serve somente para diagnóstico no computador que executa os containers.
```

- [ ] **Step 6: Executar a validação GREEN do Compose**

Repetir o comando JSON do Step 1.

Expected: PASS. Executar também:

```bash
docker compose config --quiet
```

Expected: exit 0, sem erro de interpolação ou dependência.

- [ ] **Step 7: Baixar e subir os serviços reais**

```bash
docker compose pull evolution evolution-postgres
docker compose up -d --build evolution-postgres evolution web
docker compose exec web python manage.py migrate
```

Expected: imagens baixadas, containers `evolution-postgres`, `evolution` e `web` em execução e migrações Django aplicadas.

- [ ] **Step 8: Verificar saúde e conectividade**

```bash
docker compose ps
docker compose logs --tail=100 evolution
curl --fail --silent --show-error http://localhost:8080/
docker compose exec web python -c '
import socket
print(socket.gethostbyname("evolution"))
'
```

Expected: PostgreSQL exclusivo saudável, Evolution sem reinícios, HTTP 2xx na porta 8080 e hostname `evolution` resolvido para IP da rede Docker.

- [ ] **Step 9: Executar regressão e verificações do projeto**

```bash
ruff check .
ruff format --check .
python manage.py check
pytest
```

Expected: todos os comandos com exit 0. O teste do import-linter exige a venv ativada antes de `pytest`.

- [ ] **Step 10: Verificar a tela no ambiente reconstruído**

Abrir `http://localhost:8000/whatsapp/configuracao/`, autenticar um administrador e confirmar:

- URL inicial `http://evolution:8080`;
- chave nunca reaparece depois de salvar;
- **Conectar** cria a instância;
- **Exibir QR Code** retorna imagem com `Cache-Control: no-store, private`;
- estado muda de `AGUARDANDO_QR` para `CONECTADO` após leitura do QR.

- [ ] **Step 11: Commit da infraestrutura**

```bash
git add compose.yaml .env.example docs/funcionalidades/conexao-do-whatsapp.md
git commit -m "feat: adiciona evolution api ao ambiente local"
```
