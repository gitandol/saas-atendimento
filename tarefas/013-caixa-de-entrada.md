# Tarefa 013 — Caixa de entrada funcional

**Objetivo:** permitir acompanhamento e envio manual de conversas em uma interface responsiva.

**Dependências:** tarefas 004, 009 e 012.

**Arquivos:**

- Criar: `apps/atendimento/views/paginas/caixa_entrada.py`, `apps/atendimento/urls/paginas.py`.
- Criar: `apps/atendimento/api/router.py`, `apps/atendimento/api/endpoints/{conversas,mensagens}.py`, `apps/atendimento/api/schemas/{conversas,mensagens}.py`.
- Criar: `templates/atendimento/caixa_entrada.html` e parciais em `templates/atendimento/parciais/`.
- Criar: `static/src/js/caixa_entrada.js`, `docs/funcionalidades/caixa-de-entrada.md`.
- Criar: testes espelhados de views, forms e templates.

**Produz:** página-shell e endpoints `GET /api/v1/atendimento/conversas`, `GET /api/v1/atendimento/conversas/{id}/mensagens`, `POST /api/v1/atendimento/conversas/{id}/mensagens` e `POST /api/v1/atendimento/conversas/{id}/marcar-lida`.

## Ciclo TDD

- [x] Testar contrato do endpoint de lista por última atividade com nome, número, prévia, não lidas, modo, estado e atendente.
- [x] Testar busca por nome/número e filtros `ABERTAS`, `IA`, `HUMANO`, `FINALIZADAS`.
- [x] Testar paginação por cursor do histórico e polling HTMX a cada 3 segundos sem duplicar mensagens.
- [x] Testar marcação de lidas apenas ao abrir conversa autorizada.
- [x] Testar schema de envio vazio, limite de 4.096 caracteres, conversa finalizada e ID de outra empresa.
- [x] Confirmar falhas antes da implementação.
- [x] Implementar página Django sem consultas de negócio e layout de três áreas no desktop, com navegação progressiva no celular.
- [x] Fazer HTMX consumir somente os endpoints Ninja; endpoints chamam `listar_conversas`, `obter_historico`, `marcar_como_lida` e `enviar_resposta_manual`, sem importar models.
- [x] Implementar bolhas por autor, data, status de entrega, falha e ação autorizada de reenvio.
- [x] Garantir scroll preservado durante polling e rolagem automática apenas quando usuário está no fim.
- [x] Criar ajuda contextual e executar testes, build CSS e regressão.

## Critérios de aceite

- Atendente encontra e acompanha conversa sem recarregar toda a página.
- Envio manual pela API chama o service, que cria mensagem pendente e aciona o mesmo pipeline da tarefa 012.
- Interface é navegável por teclado, tem estados vazios/carregando/erro e funciona a partir de 360 px.

**Commit sugerido:** `feat: adiciona caixa de entrada de atendimentos`

## Registro de execução

- Data: 2026-08-28
- Vermelho observado: rotas 404, services e módulos ausentes, filtros e cursores não aceitos, parciais HTMX retornando JSON, JavaScript ausente, busca formatada sem resultado e mutação do status 202 detectada.
- Implementação realizada: services isolados por empresa, quatro endpoints Ninja, schemas, página-shell responsiva em três áreas, parciais HTMX, polling incremental, envio manual pelo pipeline existente, reenvio autorizado, navegação móvel e ajuda contextual.
- Refatorações: cursor sem perda de mensagens, deduplicação defensiva, preservação de scroll, busca numérica normalizada, validação de limites e contratos arquiteturais do módulo.
- Comandos e resultados: `ruff check .` e `ruff format --check .` verdes; `python manage.py check` sem problemas; `pytest -q` com 343 testes; 7 testes JavaScript; `docker compose build web` com build Tailwind e collectstatic concluídos.
- Commit: `feat: adiciona caixa de entrada de atendimentos`
