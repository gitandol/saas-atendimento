# Tarefa 002 — Empresas, usuários e isolamento lógico

**Objetivo:** garantir que usuários acessem somente dados de sua empresa.

**Dependências:** tarefa 001.

**Arquivos:**

- Criar: `apps/contas/models/usuario.py`, `apps/empresas/models/{empresa,membro_empresa}.py`.
- Criar: `apps/empresas/services/{empresa_ativa,consultas}.py`, `apps/empresas/middleware/empresa_ativa.py`.
- Criar: `apps/contas/services/{autenticar_usuario,encerrar_sessao,obter_perfil}.py`.
- Criar: `apps/contas/views/paginas/{autenticacao,perfil}.py`, `apps/contas/api/router.py`, `apps/contas/api/endpoints/{autenticacao,perfil}.py`, `apps/contas/api/schemas/{autenticacao,perfil}.py`.
- Testar: caminhos espelhados em `apps/*/tests/`.

**Produz:** `Usuario`, `Empresa`, `MembroEmpresa`, `obter_empresa_ativa(request)`, services de autenticação/consulta e endpoints `/api/v1/autenticacao/*`.

## Ciclo TDD

- [x] Escrever testes para criação de empresa, e-mail único, associação com papel `ADMINISTRADOR` ou `ATENDENTE`, login/logout e bloqueio de membro inativo.
- [x] Escrever primeiro o teste de isolamento:

```python
def test_consulta_nao_retorna_registros_de_outra_empresa(empresa_a, empresa_b):
    """Impede vazamento de dados entre empresas no queryset público."""
    Empresa.objects.filter(pk=empresa_b.pk).update(nome="Empresa B")
    resultado = listar_empresas_permitidas(empresa_a.usuario_administrador)
    assert list(resultado) == [empresa_a]
```

- [x] Confirmar falhas por modelos e serviços ausentes.
- [x] Implementar usuário baseado em `AbstractUser` com autenticação por e-mail e modelos usando UUID.
- [x] Implementar middleware que resolve a empresa ativa pela associação do usuário; nunca aceitar `empresa_id` arbitrário de formulário como fonte de autorização.
- [x] Criar mixin/service para filtros por empresa e testes contra IDOR em views.
- [x] Criar páginas de login e perfil como shells sem consultas de negócio; submissões e carregamento de dados usam endpoints Ninja com sessão Django e CSRF.
- [x] Testar endpoints separadamente dos services: schemas inválidos retornam `422`, credenciais inválidas `401`, ausência de empresa ativa `403` e UUID externo `404`.
- [x] Testar que módulos de páginas e endpoints não importam models e que cada endpoint delega ao service correspondente.
- [x] Executar testes isolados e regressão.

## Critérios de aceite

- Usuário sem associação ativa recebe `403` nas áreas privadas.
- Administrador e atendente têm permissões distintas.
- Tentativa de acessar UUID de outra empresa retorna `404`, não detalhes do objeto.
- Login possui proteção CSRF, throttling básico por cache e redirecionamento seguro.

**Commit sugerido:** `feat: adiciona empresas usuarios e isolamento`

## Registro de execução

**Data:** 2026-08-22

### REDs reais

- Task 1: `ModuleNotFoundError: apps.contas.models` e `AttributeError` para `Empresa.criado_em`, antes de `5 passed in 0.11s`.
- Task 2: ausência de `apps.empresas.services` e `apps.empresas.middleware`, antes de `11 passed in 0.13s`.
- Task 3: ausência de `apps.contas.services` e depois `ImportError` para `reservar_tentativa_autenticacao`, antes dos GREENs focais de 10, 12 e 13 testes.
- Task 4: `19 failed, 3 passed in 0.56s` por rotas e pacotes ausentes, antes de `22 passed in 0.33s`.
- Task 5: `pytest -q` coletava apenas 8 testes por `testpaths = tests`; após corrigir a coleta, passou a coletar 53.
- Task 5: Ruff começou com 20 violações nas migrations, depois 4 E501 e conflito entre formatter/lint num `help_text`; a exceção final ficou limitada a `apps/*/migrations/*.py`.
- Task 5: `ruff format --check .` apontou 14 arquivos, dos quais 11 fontes Python com CRLF/refluxo e 3 artefatos de processo alcançados pelo formatter.

### Implementação comprovada

- `Usuario` deriva de `AbstractUser`, autentica por e-mail único e usa UUID; `Empresa` e `MembroEmpresa` modelam a associação e os papéis `ADMINISTRADOR`/`ATENDENTE`.
- Services e middleware resolvem a empresa ativa pela associação autenticada, bloqueiam membro inativo e filtram consultas por empresa, inclusive contra IDOR.
- Services de autenticação/perfil cobrem login, logout, sessão, throttle básico e redirecionamento seguro.
- Páginas permanecem shells; endpoints Ninja concentram submissões e dados, com sessão Django, CSRF e respostas `422`, `401`, `403` e `404` testadas.
- Testes de arquitetura e import-linter comprovam que as fronteiras HTTP não importam models e que services não importam fronteiras HTTP.

### Refatorações e revisões

- Revisões anteriores limitaram-se a docstrings, ordenação de imports e forma canônica do Ruff nas migrations, sem alterar suas operações.
- `pytest.ini` passou a coletar os três caminhos da suíte; a exceção E501 permaneceu exclusiva de migrations geradas.
- `[tool.ruff].extend-exclude` preserva `tarefas` e exclui somente `.superpowers` e `docs/superpowers`, artefatos de processo.
- `ruff format .` normalizou os 11 fontes Python reais; nenhum ajuste manual de comportamento foi feito.
- Três backups transitórios `.orig` foram removidos por caminho explícito; a busca repetida fora de `.venv` não retornou arquivos.

### Comandos e resultados

```text
PATH="$PWD/.venv/bin:$PATH" ruff format .
11 files reformatted, 65 files left unchanged

PATH="$PWD/.venv/bin:$PATH" ruff check .
All checks passed!

PATH="$PWD/.venv/bin:$PATH" ruff format --check .
76 files already formatted

PATH="$PWD/.venv/bin:$PATH" pytest apps/contas/tests apps/empresas/tests tests/arquitetura -q
.....................................................                    [100%]
53 passed in 0.38s

PATH="$PWD/.venv/bin:$PATH" pytest -q
........................................................                 [100%]
56 passed in 0.57s

PATH="$PWD/.venv/bin:$PATH" python manage.py makemigrations --check --dry-run --settings=config.settings.teste
No changes detected

PATH="$PWD/.venv/bin:$PATH" python manage.py migrate --noinput --settings=config.settings.teste
Operations to perform:
  Apply all migrations: admin, auth, contas, contenttypes, empresas, sessions
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying contenttypes.0002_remove_content_type_name... OK
  Applying auth.0001_initial... OK
  Applying auth.0002_alter_permission_name_max_length... OK
  Applying auth.0003_alter_user_email_max_length... OK
  Applying auth.0004_alter_user_username_opts... OK
  Applying auth.0005_alter_user_last_login_null... OK
  Applying auth.0006_require_contenttypes_0002... OK
  Applying auth.0007_alter_validators_add_error_messages... OK
  Applying auth.0008_alter_user_username_max_length... OK
  Applying auth.0009_alter_user_last_name_max_length... OK
  Applying auth.0010_alter_group_name_max_length... OK
  Applying auth.0011_update_proxy_permissions... OK
  Applying auth.0012_alter_user_first_name_max_length... OK
  Applying contas.0001_initial... OK
  Applying admin.0001_initial... OK
  Applying admin.0002_logentry_remove_auto_add... OK
  Applying admin.0003_logentry_add_action_flag_choices... OK
  Applying empresas.0001_initial... OK
  Applying sessions.0001_initial... OK

PATH="$PWD/.venv/bin:$PATH" python manage.py check
System check identified no issues (0 silenced).

PATH="$PWD/.venv/bin:$PATH" lint-imports --config pyproject.toml
Analyzed 47 files, 28 dependencies.
Camadas HTTP nao importam models KEPT
Services nao importam fronteiras HTTP KEPT
Contracts: 2 kept, 0 broken.

find . -path ./.venv -prune -o -name '*.orig' -print
(sem saída; exit 0)
```

Commit: dispensado pelo usuario; workspace sem .git
