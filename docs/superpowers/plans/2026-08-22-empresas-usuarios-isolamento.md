# Empresas, usuarios e isolamento — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar usuarios por e-mail, empresas, associacoes, empresa ativa, isolamento e autenticacao HTTP segura.

**Architecture:** Models UUID persistem o tenant e seus membros; services concentram autenticacao, selecao validada da empresa e consultas isoladas. Middleware apenas anexa o contexto resolvido, e endpoints Ninja com sessao/CSRF delegam aos services.

**Tech Stack:** Python 3.13, Django 5.2, Django Ninja 1.x, pytest-django, SQLite em testes.

**Spec:** `docs/superpowers/specs/2026-08-22-empresas-usuarios-isolamento-design.md`

## Global Constraints

- Identificadores Python e colunas proprias do banco usam portugues sem acentos.
- Toda funcao, classe, modulo, metodo e teste possui docstring.
- Views e endpoints nao importam models; services nao importam API nem views.
- Nenhuma fonte de autorizacao confia em `empresa_id` enviado pelo cliente.
- Usuario sem associacao ativa recebe `403`; UUID de outro tenant recebe `404`.
- Login usa sessao Django, CSRF, throttling por cache e redirecionamento local seguro.
- Aplicar vermelho, verde e refatoracao em cada tarefa.
- O usuario dispensou commits porque o workspace nao possui `.git`.

---

### Task 1: Modelos de usuario, empresa e associacao

**Files:**
- Create: `apps/contas/apps.py`, `apps/contas/models/usuario.py`, `apps/contas/migrations/0001_initial.py`
- Create: `apps/empresas/apps.py`, `apps/empresas/models/empresa.py`, `apps/empresas/models/membro_empresa.py`, `apps/empresas/migrations/0001_initial.py`
- Modify: `config/settings/base.py`
- Test: `apps/contas/tests/test_usuario.py`, `apps/empresas/tests/test_modelos.py`

**Interfaces:**
- Produces: `Usuario.objects.create_user(email: str, password: str | None = None)`
- Produces: `Empresa(id: UUID, nome: str)`
- Produces: `MembroEmpresa.Papel.ADMINISTRADOR|ATENDENTE` e campos `usuario`, `empresa`, `papel`, `ativo`

- [ ] **Step 1: Write failing model tests**

```python
@pytest.mark.django_db
def test_usuario_autentica_por_email_e_exige_email_unico():
    usuario = Usuario.objects.create_user(email="Pessoa@Example.com", password="senha")
    assert usuario.email == "Pessoa@example.com"
    assert usuario.USERNAME_FIELD == "email"
    with pytest.raises(IntegrityError):
        Usuario.objects.create_user(email="Pessoa@example.com")

@pytest.mark.django_db
@pytest.mark.parametrize("papel", [MembroEmpresa.Papel.ADMINISTRADOR, MembroEmpresa.Papel.ATENDENTE])
def test_associacao_aceita_os_papeis_previstos(papel):
    membro = MembroEmpresa.objects.create(usuario=usuario, empresa=empresa, papel=papel)
    assert membro.papel == papel
```

- [ ] **Step 2: Run tests and observe missing modules**

Run: `PATH="$PWD/.venv/bin:$PATH" pytest apps/contas/tests/test_usuario.py apps/empresas/tests/test_modelos.py -q`
Expected: collection fails because the apps/models do not exist.

- [ ] **Step 3: Implement minimal models and settings**

```python
class Usuario(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    username = None
    email = models.EmailField(unique=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []
    objects = UsuarioManager()

class Empresa(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    nome = models.CharField(max_length=160)
    criado_em = models.DateTimeField(auto_now_add=True)

class MembroEmpresa(models.Model):
    class Papel(models.TextChoices):
        ADMINISTRADOR = "ADMINISTRADOR", "Administrador"
        ATENDENTE = "ATENDENTE", "Atendente"
```

Add `apps.contas`, `apps.empresas`, `AUTH_USER_MODEL = "contas.Usuario"`, exports in package `__init__.py` files, uniqueness for `(usuario, empresa)`, UUID migrations and timestamps.

- [ ] **Step 4: Run model tests and migration checks**

Run: `PATH="$PWD/.venv/bin:$PATH" pytest apps/contas/tests/test_usuario.py apps/empresas/tests/test_modelos.py -q`
Run: `PATH="$PWD/.venv/bin:$PATH" python manage.py makemigrations --check --dry-run`
Expected: tests pass and no pending migrations.

### Task 2: Empresa ativa, papeis e consultas isoladas

**Files:**
- Create: `apps/empresas/services/empresa_ativa.py`, `apps/empresas/services/consultas.py`
- Create: `apps/empresas/middleware/empresa_ativa.py`
- Modify: `config/settings/base.py`
- Test: `apps/empresas/tests/test_empresa_ativa.py`, `apps/empresas/tests/test_consultas.py`, `apps/empresas/tests/test_middleware.py`

**Interfaces:**
- Consumes: `Usuario`, `Empresa`, `MembroEmpresa`
- Produces: `obter_membro_ativo(request) -> MembroEmpresa | None`
- Produces: `obter_empresa_ativa(request) -> Empresa | None`
- Produces: `exigir_empresa_ativa(request) -> Empresa`, raising `EmpresaAtivaAusente`
- Produces: `exigir_administrador(request) -> MembroEmpresa`, raising `PermissaoEmpresaNegada`
- Produces: `listar_empresas_permitidas(usuario) -> QuerySet[Empresa]`
- Produces: `obter_empresa_permitida(usuario, empresa_id: UUID) -> Empresa`, raising `Empresa.DoesNotExist`

- [ ] **Step 1: Write the failing isolation test first**

```python
@pytest.mark.django_db
def test_consulta_nao_retorna_registros_de_outra_empresa(empresa_a, empresa_b):
    Empresa.objects.filter(pk=empresa_b.pk).update(nome="Empresa B")
    resultado = listar_empresas_permitidas(empresa_a.usuario_administrador)
    assert list(resultado) == [empresa_a]
```

Add focused tests for inactive membership, invalid session UUID, deterministic fallback, middleware attachment, administrator acceptance and attendant rejection.

- [ ] **Step 2: Run tests and observe missing services**

Run: `PATH="$PWD/.venv/bin:$PATH" pytest apps/empresas/tests/test_consultas.py apps/empresas/tests/test_empresa_ativa.py apps/empresas/tests/test_middleware.py -q`
Expected: collection fails because services and middleware do not exist.

- [ ] **Step 3: Implement validated tenant resolution**

Use session key `empresa_ativa_id`; every request revalidates it against `MembroEmpresa.objects.select_related("empresa").filter(usuario=request.user, ativo=True)`. Invalid selections are removed, fallback orders by `criado_em` and `pk`, and all lookup services filter through an active membership before returning a company.

- [ ] **Step 4: Run tenant tests**

Run: `PATH="$PWD/.venv/bin:$PATH" pytest apps/empresas/tests -q`
Expected: all tenant tests pass.

### Task 3: Authentication and profile services

**Files:**
- Create: `apps/contas/services/autenticar_usuario.py`, `apps/contas/services/encerrar_sessao.py`, `apps/contas/services/obter_perfil.py`
- Test: `apps/contas/tests/test_autenticar_usuario.py`, `apps/contas/tests/test_encerrar_sessao.py`, `apps/contas/tests/test_obter_perfil.py`

**Interfaces:**
- Produces: `autenticar_usuario(request, email: str, senha: str) -> Usuario`
- Raises: `CredenciaisInvalidas`, `MuitasTentativasAutenticacao`
- Produces: `encerrar_sessao(request) -> None`
- Produces: `PerfilUsuario(email: str, nome: str, empresa_id: UUID, empresa_nome: str, papel: str, pode_administrar: bool)`
- Produces: `obter_perfil(request, empresa_id: UUID | None = None) -> PerfilUsuario`

- [ ] **Step 1: Write failing service tests**

Cover successful login, invalid credentials, inactive member, five failed attempts followed by throttling, counter reset after success, logout, administrator/attendant profile distinction and foreign UUID raising `Empresa.DoesNotExist`.

- [ ] **Step 2: Run tests and observe missing services**

Run: `PATH="$PWD/.venv/bin:$PATH" pytest apps/contas/tests/test_autenticar_usuario.py apps/contas/tests/test_encerrar_sessao.py apps/contas/tests/test_obter_perfil.py -q`
Expected: collection fails because service modules do not exist.

- [ ] **Step 3: Implement minimal services**

Build a SHA-256 cache key from normalized e-mail plus client address, retain attempts for 300 seconds, block after five failures, call Django `authenticate`/`login`/`logout`, require an active membership before completing login, and use `url_has_allowed_host_and_scheme` only at the HTTP boundary for redirects.

- [ ] **Step 4: Run account service tests**

Run: `PATH="$PWD/.venv/bin:$PATH" pytest apps/contas/tests -q`
Expected: all service and model tests pass.

### Task 4: API, page shells and security contracts

**Files:**
- Create: `apps/contas/api/router.py`, `apps/contas/api/endpoints/autenticacao.py`, `apps/contas/api/endpoints/perfil.py`
- Create: `apps/contas/api/schemas/autenticacao.py`, `apps/contas/api/schemas/perfil.py`
- Create: `apps/contas/views/paginas/autenticacao.py`, `apps/contas/views/paginas/perfil.py`
- Create: `templates/contas/autenticacao/login.html`, `templates/contas/perfil.html`
- Modify: `config/api.py`, `config/urls.py`, `pyproject.toml`
- Test: `apps/contas/tests/test_api_autenticacao.py`, `apps/contas/tests/test_api_perfil.py`, `apps/contas/tests/test_paginas.py`, `tests/arquitetura/test_dependencias_de_camadas.py`

**Interfaces:**
- Produces: GET `/api/v1/autenticacao/csrf`
- Produces: POST `/api/v1/autenticacao/login`, POST `/api/v1/autenticacao/logout`
- Produces: GET `/api/v1/perfil`, GET `/api/v1/perfil/{empresa_id}`
- Produces: GET `/entrar/`, GET `/perfil/`

- [ ] **Step 1: Write failing HTTP and architecture tests**

```python
cliente_csrf = Client(enforce_csrf_checks=True)
token = cliente_csrf.get("/api/v1/autenticacao/csrf").json()["csrf_token"]
resposta = cliente_csrf.post(
    "/api/v1/autenticacao/login",
    {"email": "admin@example.com", "senha": "senha"},
    content_type="application/json",
    HTTP_X_CSRFTOKEN=token,
)
assert resposta.status_code == 200
```

Add literal assertions for malformed schema `422`, invalid credentials `401`,
no active company `403`, foreign UUID `404`, missing CSRF `403`, unsafe
redirect falling back to `/perfil/`, authenticated logout and page shells.
Architecture tests inspect imports, while delegation tests patch the service
symbol imported by each endpoint and assert the HTTP result.

- [ ] **Step 2: Run tests and observe missing routes**

Run: `PATH="$PWD/.venv/bin:$PATH" pytest apps/contas/tests/test_api_autenticacao.py apps/contas/tests/test_api_perfil.py apps/contas/tests/test_paginas.py tests/arquitetura/test_dependencias_de_camadas.py -q`
Expected: tests fail with route/module errors.

- [ ] **Step 3: Implement schemas, endpoints, routers and shells**

```python
@router.get("/csrf", response=TokenCsrfSaidaSchema)
def obter_token_csrf(request: HttpRequest) -> dict[str, str]:
    return {"csrf_token": get_token(request)}

falha_csrf = check_csrf(request)
if falha_csrf:
    return Status(403, erro("csrf_invalido", "Token CSRF invalido."))
```

Use `SessionAuth()` (CSRF enabled by default) for private operations and
`Status(codigo, valor)` for declared response schemas. Views call only
`render`; templates load dynamic data through the versioned API.

- [ ] **Step 4: Run HTTP and architecture tests**

Run: `PATH="$PWD/.venv/bin:$PATH" pytest apps/contas/tests tests/arquitetura/test_dependencias_de_camadas.py -q`
Expected: all account, tenant and architecture tests pass.

### Task 5: Regression, task record and final verification

**Files:**
- Modify: `tarefas/002-empresas-usuarios-e-isolamento.md`

**Interfaces:**
- Consumes: all prior deliverables
- Produces: execution record with red/green/refactor evidence and command results

- [ ] **Step 1: Run isolated and full verification**

Run:
```bash
PATH="$PWD/.venv/bin:$PATH" pytest apps/contas/tests apps/empresas/tests tests/arquitetura -q
PATH="$PWD/.venv/bin:$PATH" pytest -q
PATH="$PWD/.venv/bin:$PATH" python manage.py makemigrations --check --dry-run
PATH="$PWD/.venv/bin:$PATH" python manage.py migrate --noinput
PATH="$PWD/.venv/bin:$PATH" python manage.py check
PATH="$PWD/.venv/bin:$PATH" ruff check .
PATH="$PWD/.venv/bin:$PATH" ruff format --check .
```
Expected: every command exits zero.

- [ ] **Step 2: Append execution record**

Record the observed red failures, implemented contracts, refactors, exact verification results, date `2026-08-22`, and `Commit: dispensado pelo usuario; workspace sem .git`.

- [ ] **Step 3: Re-run task file checks affected by the record**

Run: `PATH="$PWD/.venv/bin:$PATH" ruff check . && PATH="$PWD/.venv/bin:$PATH" pytest -q`
Expected: both commands exit zero.

