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

- [ ] Testar contrato do endpoint de lista por última atividade com nome, número, prévia, não lidas, modo, estado e atendente.
- [ ] Testar busca por nome/número e filtros `ABERTAS`, `IA`, `HUMANO`, `FINALIZADAS`.
- [ ] Testar paginação por cursor do histórico e polling HTMX a cada 3 segundos sem duplicar mensagens.
- [ ] Testar marcação de lidas apenas ao abrir conversa autorizada.
- [ ] Testar schema de envio vazio, limite de 4.096 caracteres, conversa finalizada e ID de outra empresa.
- [ ] Confirmar falhas antes da implementação.
- [ ] Implementar página Django sem consultas de negócio e layout de três áreas no desktop, com navegação progressiva no celular.
- [ ] Fazer HTMX consumir somente os endpoints Ninja; endpoints chamam `listar_conversas`, `obter_historico`, `marcar_como_lida` e `enviar_resposta_manual`, sem importar models.
- [ ] Implementar bolhas por autor, data, status de entrega, falha e ação autorizada de reenvio.
- [ ] Garantir scroll preservado durante polling e rolagem automática apenas quando usuário está no fim.
- [ ] Criar ajuda contextual e executar testes, build CSS e regressão.

## Critérios de aceite

- Atendente encontra e acompanha conversa sem recarregar toda a página.
- Envio manual pela API chama o service, que cria mensagem pendente e aciona o mesmo pipeline da tarefa 012.
- Interface é navegável por teclado, tem estados vazios/carregando/erro e funciona a partir de 360 px.

**Commit sugerido:** `feat: adiciona caixa de entrada de atendimentos`
