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

- [ ] Testar que usuário autenticado recebe sidebar, topo, link Ajuda e seletor com exatamente cinco paletas.
- [ ] Testar endpoint `PUT /api/v1/preferencias/visual` aceitando apenas os cinco temas e modos `CLARO`, `ESCURO`, `SISTEMA`.
- [ ] Testar que preferência de outra empresa/usuário não pode ser alterada.
- [ ] Confirmar falhas antes do modelo, view e templates.
- [ ] Implementar tokens CSS sem duplicar classes por tema e script que aplica preferência antes da pintura da página para evitar flash.
- [ ] Salvar preferência no `localStorage` para visitante; para autenticado, sincronizar com o endpoint Ninja, que delega persistência e auditoria ao service.
- [ ] Validar teclado, foco visível, landmarks, `aria-expanded`, contraste AA e responsividade em 360, 768, 1280 e 1920 px.
- [ ] Atualizar ajuda contextual e executar build CSS, testes e regressão.

## Critérios de aceite

- Todas as paletas funcionam em claro e escuro.
- Troca de tema não recarrega a página e persiste após novo login.
- Sidebar e topo mantêm navegação utilizável em celular e desktop.
- Componentes não possuem cores de negócio fixas fora dos tokens.

**Commit sugerido:** `feat: adiciona layout responsivo e temas`
