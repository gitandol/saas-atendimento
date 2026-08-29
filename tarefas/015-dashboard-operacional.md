# Tarefa 015 — Dashboard operacional básico

**Objetivo:** apresentar situação atual do atendimento sem criar analytics avançado.

**Dependências:** tarefas 004, 009 e 014.

**Arquivos:**

- Criar: `apps/painel/services/metricas_atendimento.py`.
- Criar: `apps/painel/views/paginas/dashboard.py`, `apps/painel/urls/paginas.py`.
- Criar: `apps/painel/api/router.py`, `apps/painel/api/endpoints/dashboard.py`, `apps/painel/api/schemas/dashboard.py`.
- Criar: `templates/painel/dashboard.html` e componentes de cartões/estado.
- Criar: `docs/funcionalidades/dashboard.md` e testes espelhados.

**Produz:** `obter_metricas_do_dia(empresa, agora) -> MetricasAtendimento` e endpoint `GET /api/v1/painel/metricas`.

## Métricas do MVP

- conversas abertas;
- conversas em modo IA;
- conversas em modo humano;
- mensagens recebidas hoje;
- mensagens enviadas hoje;
- mensagens com falha;
- estado da OpenAI e da Evolution API.

## Ciclo TDD

- [x] Criar fixtures com horários próximos à virada do dia e testar timezone da empresa.
- [x] Testar service de métricas sem dados, com dados mistos e sem vazamento entre empresas.
- [x] Testar que dashboard executa quantidade limitada de queries e usa cache de 30 segundos por empresa.
- [x] Testar visibilidade de alertas de IA/WhatsApp desconectados e links para configuração.
- [x] Confirmar falhas antes da implementação.
- [x] Implementar dataclass imutável de métricas e consultas agregadas.
- [x] Implementar endpoint fino que converte a dataclass em schema de saída e página-shell que o consulta por HTMX.
- [x] Criar cartões inspirados na referência visual, sem gráficos decorativos ou metas inexistentes.
- [x] Adicionar atualização HTMX dos cartões, ajuda e estados de carregamento/erro.
- [x] Executar testes, inspeção responsiva e regressão.

## Critérios de aceite

- Métricas refletem somente a empresa ativa e o fuso configurado.
- Falhas de integração são acionáveis e levam à configuração correta.
- Dashboard permanece útil com zero conversas.

**Commit sugerido:** `feat: adiciona dashboard operacional`

## Registro de execução

- Data: 2026-08-29
- Vermelho observado: campo `Empresa.fuso_horario` ausente; service `apps.painel.services` ausente; rotas `/api/v1/painel/metricas` e `/painel/` retornando 404; arquivos de fronteira inexistentes.
- Implementação realizada: fuso IANA por empresa com migração; dataclass imutável; quatro consultas agregadas isoladas por tenant; cache de 30 segundos por empresa e data local; API Django Ninja; página-shell HTMX; oito cartões; alertas acionáveis; ajuda e navegação.
- Refatorações: agregações separadas por domínio, limites do dia convertidos para UTC e contratos do Import Linter ampliados para o módulo `painel`.
- Comandos e resultados: testes focados `17 passed`; suíte completa `374 passed, 1 skipped`; `ruff check .` verde; `ruff format --check .` verde; `python manage.py check` sem problemas; `makemigrations --check --dry-run` sem alterações; `lint-imports` com 2 contratos preservados.
- Inspeção responsiva: estrutura revisada com grades em 3/2/1 colunas, alertas empilhados em telas estreitas e uso exclusivo das variáveis dos temas claro/escuro. A conexão automatizada ao navegador ficou indisponível por erro do sandbox, sem screenshot.
- Commit: `feat: adiciona dashboard operacional`
