# Tarefa 004 — Layout administrativo, claro/escuro e cinco temas

**Objetivo:** construir o design system e a estrutura visual inspirada no layout anexado.

**Dependências:** tarefas 002 e 003.

**Arquivos:**

- Criar: `templates/base.html`, `templates/componentes/{sidebar,barra_superior,cartao,seletor_tema,alertas}.html`.
- Criar: `static/src/css/{aplicacao,temas,componentes}.css`, `static/src/js/{tema,sidebar}.js`.
- Criar: `apps/contas/models/preferencia_visual.py`, `apps/contas/services/preferencia_visual.py`, `apps/contas/api/endpoints/preferencia_visual.py`, `apps/contas/api/schemas/preferencia_visual.py`.
- Criar: `docs/funcionalidades/personalizacao-visual.md` e testes de página, API, service e templates.

**Produz:** shell visual reutilizável, cinco paletas e modo claro/escuro persistente.

## Contrato visual

- Paletas: `azul`, `esmeralda`, `violeta`, `rubi`, `ambar`.
- CSS usa tokens `--cor-primaria`, `--cor-fundo`, `--cor-superficie`, `--cor-texto`, `--cor-borda`, `--cor-sucesso`, `--cor-alerta`.
- `data-tema` define a paleta e a classe `dark` define luminosidade.
- Sidebar recolhível no desktop e drawer no celular; barra superior contém busca, tema, notificações e perfil.

## Ciclo TDD

- [x] Testar que usuário autenticado recebe sidebar, topo, link Ajuda e seletor com exatamente cinco paletas.
- [x] Testar endpoint `PUT /api/v1/preferencias/visual` aceitando apenas os cinco temas e modos `CLARO`, `ESCURO`, `SISTEMA`.
- [x] Testar que preferência de outra empresa/usuário não pode ser alterada.
- [x] Confirmar falhas antes do modelo, view e templates.
- [x] Implementar tokens CSS sem duplicar classes por tema e script que aplica preferência antes da pintura da página para evitar flash.
- [x] Salvar preferência no `localStorage` para visitante; para autenticado, sincronizar com o endpoint Ninja, que delega persistência e auditoria ao service.
- [x] Validar teclado, foco visível, landmarks, `aria-expanded`, contraste AA e responsividade em 360, 768, 1280 e 1920 px.
- [x] Atualizar ajuda contextual e executar build CSS, testes e regressão.

## Critérios de aceite

- Todas as paletas funcionam em claro e escuro.
- Troca de tema não recarrega a página e persiste após novo login.
- Sidebar e topo mantêm navegação utilizável em celular e desktop.
- Componentes não possuem cores de negócio fixas fora dos tokens.

**Commit sugerido:** `feat: adiciona layout responsivo e temas`

## Registro de execução

- Data: 2026-08-24.
- TDD: falhas observadas antes da implementação para modelo/migração, páginas e componentes, endpoint, paletas escuras e comportamento JavaScript de tema/sidebar.
- Implementação: shell administrativo responsivo, cinco paletas em claro/escuro, persistência local e sincronização autenticada com auditoria e isolamento por empresa.
- Acessibilidade: landmarks, foco visível, estados `aria-expanded`/`inert`, navegação por teclado e contraste AA cobertos por testes automatizados; breakpoints cobrem 360, 768, 1280 e 1920 px.
- Verificações: `npm run css:build`; `npm run test:js` (4 testes); `ruff check .`; `ruff format --check .`; `manage.py check`; `manage.py makemigrations --check --dry-run`; `pytest` (91 testes); `git diff --check`.
- Observação: a inspeção visual interativa no navegador interno não pôde ser executada porque o processo do navegador foi bloqueado pelo sandbox; as verificações estruturais, responsivas e de acessibilidade foram executadas por testes.
- Commit: `feat: adiciona layout responsivo e temas`.

## Reformulação visual vibrante — 2026-08-24

- TDD: os novos testes falharam primeiro pela ausência dos tokens de superfície/brilho, da grade de login e dos contratos de largura limitada/estado ativo da sidebar.
- Implementação: paletas azul, esmeralda, violeta, rubi e âmbar renovadas com contraste AA; login responsivo em duas colunas a partir de 768 px; shell autenticado com sidebar preservada, item ativo acessível, cartões internos e destaques derivados dos tokens.
- Compatibilidade: modos **Claro**, **Escuro** e **Sistema**, persistência local/autenticada, endpoints, IDs e atributos JavaScript foram preservados.
- Verificações: `.venv/bin/pytest -q` com a venv no `PATH` (105 testes); `ruff check .`; `ruff format --check .`; `manage.py check`; `manage.py makemigrations --check --dry-run`; `npm run test:js` (4 testes); `npm run css:build`; `git diff --check`.
- Docker: `docker compose build web` compilou o Tailwind e coletou 133 arquivos estáticos; o serviço ficou saudável e `/static/dist/css/aplicacao.css` respondeu HTTP 200 com `Content-Type: text/css`.
- Inspeção visual: o navegador interno não pôde ser inicializado por falha do executor local (`setup refresh had errors`). A estrutura responsiva de 360, 768, 1280 e 1920 px, foco visível e movimento reduzido foram mantidos no CSS e nos testes automatizados, mas a conferência visual interativa permanece pendente.
