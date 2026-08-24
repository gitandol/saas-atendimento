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

- [ ] Criar fixtures com horários próximos à virada do dia e testar timezone da empresa.
- [ ] Testar service de métricas sem dados, com dados mistos e sem vazamento entre empresas.
- [ ] Testar que dashboard executa quantidade limitada de queries e usa cache de 30 segundos por empresa.
- [ ] Testar visibilidade de alertas de IA/WhatsApp desconectados e links para configuração.
- [ ] Confirmar falhas antes da implementação.
- [ ] Implementar dataclass imutável de métricas e consultas agregadas.
- [ ] Implementar endpoint fino que converte a dataclass em schema de saída e página-shell que o consulta por HTMX.
- [ ] Criar cartões inspirados na referência visual, sem gráficos decorativos ou metas inexistentes.
- [ ] Adicionar atualização HTMX dos cartões, ajuda e estados de carregamento/erro.
- [ ] Executar testes, inspeção responsiva e regressão.

## Critérios de aceite

- Métricas refletem somente a empresa ativa e o fuso configurado.
- Falhas de integração são acionáveis e levam à configuração correta.
- Dashboard permanece útil com zero conversas.

**Commit sugerido:** `feat: adiciona dashboard operacional`
