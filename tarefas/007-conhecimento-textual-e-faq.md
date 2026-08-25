# Tarefa 007 — Conhecimento textual e perguntas frequentes

**Objetivo:** fornecer contexto controlado para a IA sem introduzir RAG vetorial no MVP.

**Dependências:** tarefa 006.

**Arquivos:**

- Criar: `apps/ia/models/{documento_textual,pergunta_frequente}.py`.
- Criar: `apps/ia/api/schemas/{documento_textual,pergunta_frequente}.py`.
- Criar: `apps/ia/services/{gerenciar_conhecimento,montar_contexto}.py`.
- Criar: `apps/ia/api/endpoints/{conhecimento,perguntas_frequentes}.py`, `apps/ia/views/paginas/{conhecimento,perguntas_frequentes}.py` e rotas/templates correspondentes.
- Criar: `docs/funcionalidades/base-de-conhecimento.md` e testes espelhados.

**Produz:** `montar_contexto_empresa(empresa) -> str` e endpoints CRUD `/api/v1/ia/conhecimentos` e `/api/v1/ia/perguntas-frequentes`.

## Ciclo TDD

- [x] Testar CRUD de textos com `titulo`, `conteudo`, `ativo` e ordem; FAQ com `pergunta`, `resposta`, `ativo` e ordem.
- [x] Testar isolamento, permissão de administrador, exclusão lógica, auditoria, revisão e restauração.
- [x] Testar montagem determinística que inclui apenas registros ativos, com limite total de 20.000 caracteres e indicação explícita de truncamento.
- [x] Testar que conteúdo é tratado como dados e não substitui instruções de sistema.
- [x] Confirmar falhas antes de criar modelos e serviços.
- [x] Implementar services transacionais e endpoints finos para listar, criar, editar, ordenar, ativar e excluir logicamente.
- [x] Implementar páginas-shell que usam HTMX para consumir a API e componentes do design system para os estados de carregamento, vazio e erro.
- [x] Testar contratos paginados, schemas inválidos, IDs de outra empresa e ausência de importação de models pelos endpoints.
- [x] Criar ajuda com exemplos de conteúdo seguro e explicar que PDFs/URLs ainda não são suportados.
- [x] Executar migrations, testes e regressão.

## Critérios de aceite

- Administrador consegue ativar/desativar e ordenar conhecimento.
- Atendente pode consultar, mas não editar.
- Prompt final diferencia claramente instruções da plataforma, perfil da empresa e conteúdo informativo.

**Commit sugerido:** `feat: adiciona conhecimento textual e faq`
## Registro de execução

- Data: 2026-08-25
- Vermelho observado: 7 falhas por modelos/services ausentes; 3 falhas por rotas API inexistentes; 5 falhas por páginas/ajuda ausentes; 2 falhas pelos controles HTMX de edição e exclusão ausentes.
- Implementação realizada: modelos `DocumentoTextual` e `PerguntaFrequente`, exclusão lógica, services transacionais e auditáveis, restauração por snapshots, contexto determinístico e truncado, CRUD paginado, páginas HTMX e ajuda contextual.
- Refatorações: publicação por dataclasses, paginação compartilhada, snapshots JSON seguros e endpoints sem importação de models.
- Comandos e resultados: `ruff check .` (limpo); `ruff format --check .` (212 arquivos formatados); `makemigrations --check --dry-run` (sem mudanças); `migrate --noinput` (migrações aplicadas); `python manage.py check` (0 issues); `pytest apps/ia/tests -q` (50 passed); `pytest -q` (183 passed).
- Commit: `feat: adiciona conhecimento textual e faq`
