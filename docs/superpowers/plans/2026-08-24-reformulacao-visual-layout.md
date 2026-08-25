# Reformulacao Visual do Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aplicar uma linguagem visual escura, vibrante e concentrada ao login e ao shell autenticado, preservando sidebar, cinco paletas, modos de luminosidade, APIs e acessibilidade.

**Architecture:** Evoluir os tokens existentes em `temas.css` e os componentes em `componentes.css`, mantendo JavaScript e contratos HTTP intactos. Templates recebem somente agrupamentos semanticos necessarios para o login em duas colunas e para limitar/organizar o conteudo autenticado.

**Tech Stack:** Django 5.2, Django Templates, Tailwind CSS 4, CSS custom properties, JavaScript sem framework, pytest e Node test runner.

**Spec:** `docs/superpowers/specs/2026-08-24-reformulacao-visual-layout-design.md`

## Global Constraints

- Preservar as cinco paletas: azul, esmeralda, violeta, rubi e ambar.
- Manter modos CLARO, ESCURO e SISTEMA com persistencia local e autenticada.
- Nao alterar autenticacao, endpoints, models, services ou auditoria.
- Nao remover a sidebar nem substituir a navegacao principal por menu de topo.
- Componentes nao recebem cores de negocio fixas; efeitos derivam dos tokens.
- Contraste minimo WCAG AA, foco visivel e `prefers-reduced-motion` obrigatorios.
- Validar em 360, 768, 1280 e 1920 px.

---

### Task 1: Tokens vibrantes e contraste das cinco paletas

**Files:**
- Modify: `apps/contas/tests/test_contraste_temas.py`
- Modify: `static/src/css/temas.css`

**Interfaces:**
- Consumes: seletores `:root`, `:root.dark` e `:root[...data-tema]` usados por `tema.js`.
- Produces: tokens `--cor-primaria`, `--cor-em-primaria`, `--cor-fundo`, `--cor-superficie`, `--cor-superficie-interna`, `--cor-texto`, `--cor-texto-suave`, `--cor-borda`, `--cor-brilho`, `--sombra`.

- [ ] **Step 1: Escrever testes falhando para contraste claro e escuro**

Estender o teste para extrair a superficie e validar cada paleta nos dois modos:

```python
@pytest.mark.parametrize("seletor", [":root", ":root.dark"])
def test_tema_define_superficie_interna_e_brilho(seletor: str) -> None:
    """Exige os tokens consumidos por cartoes internos e decoracoes."""
    css = Path("static/src/css/temas.css").read_text(encoding="utf-8")
    bloco = _bloco(css, seletor)

    assert re.search(r"--cor-superficie-interna:\s*#[0-9a-fA-F]{6}", bloco)
    assert "--cor-brilho:" in bloco


@pytest.mark.parametrize(
    ("prefixo", "superficie"),
    [("", "#ffffff"), (".dark", "#151a17")],
)
@pytest.mark.parametrize("tema", ["azul", "esmeralda", "violeta", "rubi", "ambar"])
def test_paleta_vibrante_atende_contraste_wcag_aa(
    prefixo: str,
    superficie: str,
    tema: str,
) -> None:
    """Mantem primaria legivel na superficie e no proprio botao."""
    css = Path("static/src/css/temas.css").read_text(encoding="utf-8")
    seletor = f':root{prefixo}[data-tema="{tema}"]'
    bloco = _bloco(css, seletor)
    primaria = _token(bloco, "cor-primaria")
    sobre_primaria = _token(bloco, "cor-em-primaria")

    assert _contraste(primaria, superficie) >= 4.5
    assert _contraste(primaria, sobre_primaria) >= 4.5
```

- [ ] **Step 2: Executar o teste e confirmar o vermelho**

Run: `.venv/bin/pytest apps/contas/tests/test_contraste_temas.py -q`

Expected: FAIL no teste de superficie interna e brilho porque os dois novos tokens ainda nao existem.

- [ ] **Step 3: Implementar os tokens e paletas**

Usar bases neutras claras e grafite no escuro. Definir cores primarias explicitas, com texto de alto contraste:

```css
:root {
  --cor-fundo: #f4f6f3;
  --cor-superficie: #ffffff;
  --cor-superficie-interna: #eef1ed;
  --cor-texto: #161a17;
  --cor-texto-suave: #59615b;
  --cor-borda: #c8cec9;
  --cor-brilho: color-mix(in srgb, var(--cor-primaria) 18%, transparent);
}

:root.dark {
  --cor-fundo: #080b09;
  --cor-superficie: #151a17;
  --cor-superficie-interna: #0e120f;
  --cor-texto: #f4f7f3;
  --cor-texto-suave: #a7b0a9;
  --cor-borda: #303732;
}
```

Paletas escuras: azul `#38bdf8`, esmeralda `#a3e635`, violeta `#a78bfa`, rubi `#fb7185`, ambar `#fbbf24`, todas com `--cor-em-primaria: #080b09`. Paletas claras: azul `#0369a1`, esmeralda `#3f6212`, violeta `#6d28d9`, rubi `#be123c`, ambar `#92400e`, todas com `--cor-em-primaria: #ffffff`.

- [ ] **Step 4: Executar teste e build CSS**

Run: `.venv/bin/pytest apps/contas/tests/test_contraste_temas.py -q`

Expected: PASS para as dez combinacoes.

Run: `npm run css:build`

Expected: Tailwind conclui sem erro.

- [ ] **Step 5: Commit**

```bash
git add apps/contas/tests/test_contraste_temas.py static/src/css/temas.css
git commit -m "style: renova paletas visuais vibrantes"
```

### Task 2: Login em duas colunas

**Files:**
- Modify: `apps/contas/tests/test_paginas.py`
- Modify: `templates/base_publica.html`
- Modify: `templates/contas/autenticacao/login.html`
- Modify: `static/src/css/componentes.css`

**Interfaces:**
- Consumes: `tema.js`, `componentes/seletor_tema.html` e endpoints `/api/v1/autenticacao/csrf` e `/api/v1/autenticacao/login`.
- Produces: classes `pagina-publica`, `cabecalho-publico`, `grade-login`, `apresentacao-login`, `cartao-login` e `formulario-autenticacao`.

- [ ] **Step 1: Escrever teste falhando da composicao publica**

Atualizar o teste do login para validar estrutura e controles, sem mudar os endpoints:

```python
@pytest.mark.django_db
def test_pagina_de_login_expoe_composicao_em_duas_colunas() -> None:
    """Entrega hero, acesso e seletor completo no shell publico."""
    resposta = Client().get("/entrar/")
    conteudo = resposta.content.decode()

    assert resposta.status_code == 200
    assert 'class="grade-login"' in conteudo
    assert 'class="apresentacao-login"' in conteudo
    assert 'class="cartao cartao-login"' in conteudo
    assert 'class="formulario-autenticacao"' in conteudo
    assert "Atendimento inteligente" in conteudo
    assert conteudo.count("data-tema-opcao=") == 5
```

- [ ] **Step 2: Executar o teste e confirmar o vermelho**

Run: `.venv/bin/pytest apps/contas/tests/test_paginas.py::test_pagina_de_login_expoe_composicao_em_duas_colunas -q`

Expected: FAIL porque hero, grade e seletor publico ainda nao existem.

- [ ] **Step 3: Implementar estrutura semantica do login**

No `base_publica.html`, substituir utilitarios soltos por `pagina-publica` e `cabecalho-publico`, mantendo marca, Ajuda e adicionando o seletor de tema. No login, usar:

```html
<div class="grade-login">
  <section class="apresentacao-login" aria-labelledby="titulo-boas-vindas">
    <p class="rotulo-pagina">Atendimento inteligente</p>
    <h1 id="titulo-boas-vindas">Conecte. Atenda. Cresca.</h1>
    <p>Centralize conversas e ofereca respostas mais rapidas sem perder o toque humano.</p>
    <ul class="beneficios-login">
      <li>Respostas organizadas</li>
      <li>Equipe e IA no mesmo fluxo</li>
    </ul>
  </section>
  <section class="cartao cartao-login" aria-labelledby="titulo-login">
    <p class="rotulo-pagina">Acesso seguro</p>
    <h2 id="titulo-login">Acesse sua conta</h2>
    <p class="texto-apoio">Use os dados cadastrados para continuar.</p>
    <form id="form-login" class="formulario-autenticacao">
      <label for="email">E-mail</label>
      <input id="email" name="email" type="email" autocomplete="email" required>
      <label for="senha">Senha</label>
      <input id="senha" name="senha" type="password" autocomplete="current-password" required>
      <button type="submit">Entrar <span aria-hidden="true">&rarr;</span></button>
      <p id="erro-login" role="alert"></p>
    </form>
  </section>
</div>
```

- [ ] **Step 4: Implementar CSS do login e responsividade**

Criar grade de duas colunas a partir de 768 px, largura maxima de 70rem, fundo com pontos e halos derivados de `--cor-brilho`, cartao de 28rem, inputs em `--cor-superficie-interna` e botao primario em largura total. Em ate 767 px, ocultar beneficios secundarios, manter hero compacto e formulario em coluna unica.

Adicionar:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
  }
}
```

- [ ] **Step 5: Executar testes e build**

Run: `.venv/bin/pytest apps/contas/tests/test_paginas.py -q`

Expected: PASS.

Run: `npm run css:build`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/contas/tests/test_paginas.py templates/base_publica.html templates/contas/autenticacao/login.html static/src/css/componentes.css
git commit -m "style: cria login vibrante em duas colunas"
```

### Task 3: Shell autenticado com sidebar preservada

**Files:**
- Modify: `apps/contas/tests/test_paginas.py`
- Modify: `templates/base.html`
- Modify: `templates/componentes/sidebar.html`
- Modify: `templates/componentes/barra_superior.html`
- Modify: `templates/contas/perfil.html`
- Modify: `templates/auditoria/historico.html`
- Modify: `static/src/css/componentes.css`

**Interfaces:**
- Consumes: atributos `data-abrir-sidebar`, `data-fechar-sidebar`, `data-recolher-sidebar`, IDs `sidebar` e `conteudo-principal` usados por `sidebar.js`.
- Produces: classes `conteudo-limitado`, `item-navegacao-ativo`, `marca-descricao`, `cartao-destaque` e hierarquia visual compartilhada.

- [ ] **Step 1: Escrever teste falhando do shell refinado**

No teste autenticado, exigir os novos contratos sem remover landmarks:

```python
assert 'class="conteudo-principal conteudo-limitado"' in conteudo
assert 'class="marca-descricao sidebar-rotulo"' in conteudo
assert 'item-navegacao-ativo' in conteudo
assert 'aria-current="page"' in conteudo
```

- [ ] **Step 2: Executar o teste e confirmar o vermelho**

Run: `.venv/bin/pytest apps/contas/tests/test_paginas.py::test_usuario_autenticado_recebe_layout_e_cinco_paletas -q`

Expected: FAIL porque o shell ainda nao possui largura limitada nem estado ativo.

- [ ] **Step 3: Implementar markup minimo sem quebrar JavaScript**

Adicionar as classes conteudo-limitado ao main e item-navegacao-ativo ao link correspondente a request.path. Na sidebar, manter todos os IDs e atributos de controle e acrescentar a descricao curta da marca. Na barra superior, preservar a estrutura atual de busca, tema, notificacoes, ajuda e perfil, alterando somente classes e estilos. O link ativo recebe `aria-current="page"`.

- [ ] **Step 4: Refinar shell e cartoes**

Atualizar CSS para:

- sidebar grafite integrada ao fundo, borda sutil e item ativo derivado da primaria;
- barra superior translucida compacta;
- conteudo com `max-width: 78rem` e margem automatica;
- titulos maiores, rotulos em caixa alta e espacos verticais consistentes;
- cartoes com superficie elevada e regioes internas em `--cor-superficie-interna`;
- controles preservando dimensoes minimas de toque e foco visivel;
- breakpoints existentes de 767 px e comportamento recolhido no desktop.

Aplicar a classe cartao-destaque aos cartoes principais de perfil e historico, sem mudar IDs ou endpoints. Implementar os contratos centrais:

```css
.conteudo-limitado { width: min(100%, 78rem); margin-inline: auto; }
.item-navegacao-ativo {
  background: color-mix(in srgb, var(--cor-primaria) 14%, var(--cor-superficie));
  color: var(--cor-primaria);
}
.cartao-destaque { background: var(--cor-superficie); }
.cartao-destaque > :not(h2) {
  border-radius: 0.8rem;
  background: var(--cor-superficie-interna);
}
```

- [ ] **Step 5: Executar testes de pagina e JavaScript**

Run: `.venv/bin/pytest apps/contas/tests/test_paginas.py apps/auditoria/tests/test_pagina_historico.py -q`

Expected: PASS.

Run: `npm run test:js`

Expected: 4 testes passam, comprovando que sidebar e tema mantiveram o comportamento.

- [ ] **Step 6: Commit**

```bash
git add apps/contas/tests/test_paginas.py templates/base.html templates/componentes/sidebar.html templates/componentes/barra_superior.html templates/contas/perfil.html templates/auditoria/historico.html static/src/css/componentes.css
git commit -m "style: refina shell autenticado e sidebar"
```

### Task 4: Validacao integrada, ajuda e registro

**Files:**
- Modify: `docs/funcionalidades/personalizacao-visual.md`
- Modify: `tarefas/004-layout-e-temas.md`

**Interfaces:**
- Consumes: design system completo produzido nas Tasks 1 a 3.
- Produces: documentacao contextual e registro verificavel da reformulacao.

- [ ] **Step 1: Atualizar ajuda contextual**

Documentar que as cinco paletas compartilham a linguagem vibrante, que claro/escuro/sistema continuam disponiveis e que a sidebar permanece recolhivel/drawer.

- [ ] **Step 2: Executar verificacao completa**

Run: `.venv/bin/pytest`

Expected: todos os testes passam.

Run: `.venv/bin/ruff check . && .venv/bin/ruff format --check .`

Expected: nenhum erro e todos os arquivos formatados.

Run: `DJANGO_SETTINGS_MODULE=config.settings.teste .venv/bin/python manage.py check && DJANGO_SETTINGS_MODULE=config.settings.teste .venv/bin/python manage.py makemigrations --check --dry-run`

Expected: zero issues e nenhuma migracao nova.

Run: `npm run test:js && npm run css:build`

Expected: 4 testes JavaScript e build Tailwind verdes.

- [ ] **Step 3: Validar imagem Docker e assets**

Run: `docker compose build web && docker compose up -d web`

Expected: build Node e `collectstatic` concluem; servico web fica healthy.

Run: `curl -fsSI http://localhost:8000/static/dist/css/aplicacao.css`

Expected: HTTP 200 e `Content-Type: text/css`.

- [ ] **Step 4: Validar interface manualmente**

Em `/entrar/`, `/perfil/` e `/auditoria/`, conferir 360, 768, 1280 e 1920 px; testar as cinco paletas em claro e escuro; percorrer controles com Tab; abrir/fechar drawer com teclado; verificar que `Esc` devolve o foco e que nao ha scroll horizontal.

- [ ] **Step 5: Registrar resultados e commit final**

Acrescentar ao registro da tarefa os vermelhos observados, implementacao, refatoracoes, comandos e resultados.

```bash
git add docs/funcionalidades/personalizacao-visual.md tarefas/004-layout-e-temas.md
git commit -m "docs: registra reformulacao visual do layout"
```
