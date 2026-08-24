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

- [ ] Testar CRUD de textos com `titulo`, `conteudo`, `ativo` e ordem; FAQ com `pergunta`, `resposta`, `ativo` e ordem.
- [ ] Testar isolamento, permissão de administrador, exclusão lógica, auditoria, revisão e restauração.
- [ ] Testar montagem determinística que inclui apenas registros ativos, com limite total de 20.000 caracteres e indicação explícita de truncamento.
- [ ] Testar que conteúdo é tratado como dados e não substitui instruções de sistema.
- [ ] Confirmar falhas antes de criar modelos e serviços.
- [ ] Implementar services transacionais e endpoints finos para listar, criar, editar, ordenar, ativar e excluir logicamente.
- [ ] Implementar páginas-shell que usam HTMX para consumir a API e componentes do design system para os estados de carregamento, vazio e erro.
- [ ] Testar contratos paginados, schemas inválidos, IDs de outra empresa e ausência de importação de models pelos endpoints.
- [ ] Criar ajuda com exemplos de conteúdo seguro e explicar que PDFs/URLs ainda não são suportados.
- [ ] Executar migrations, testes e regressão.

## Critérios de aceite

- Administrador consegue ativar/desativar e ordenar conhecimento.
- Atendente pode consultar, mas não editar.
- Prompt final diferencia claramente instruções da plataforma, perfil da empresa e conteúdo informativo.

**Commit sugerido:** `feat: adiciona conhecimento textual e faq`
