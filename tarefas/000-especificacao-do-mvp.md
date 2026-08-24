# Especificação validada do MVP

## Resultado esperado

Uma empresa administradora entra no painel, configura seu perfil, conecta uma instância da Evolution API por QR Code, informa sua credencial OpenAI e recebe mensagens reais. A IA responde automaticamente usando as instruções e FAQs da empresa. Um atendente pode assumir a conversa, responder manualmente e finalizá-la.

## Papéis

- **Administrador:** configura empresa, IA e WhatsApp; acessa auditoria e todo atendimento.
- **Atendente:** consulta contatos e conversas, assume, responde e finaliza atendimentos.
- **Sistema/IA:** registra mensagens, gera respostas e envia pela integração autorizada.

## Escopo funcional

- Login por sessão Django.
- Isolamento lógico por empresa e associação usuário-empresa.
- Perfil da empresa e instruções de atendimento.
- Uma configuração OpenAI e uma conexão Evolution API por empresa.
- Conhecimento textual e FAQ, sem embeddings.
- Contatos criados automaticamente pelo número do remetente.
- Conversas com modos `IA`, `HUMANO` e estado `FINALIZADA`.
- Mensagens de texto recebidas e enviadas com idempotência e status.
- Caixa de entrada responsiva com busca, filtros e atualização por HTMX.
- Dashboard básico e ajuda contextual.
- Auditoria e revisão das mutações de negócio.

## Fora do escopo

- Outros canais, múltiplos números por empresa, mídia e áudio.
- RAG vetorial, upload de arquivos e coleta de sites.
- CRM com pipeline, agenda, catálogo, financeiro, billing e white label completo.
- WebSockets, aplicativo mobile e Kubernetes.

## Decisões de interface

- Estrutura visual inspirada na referência TailAdmin: sidebar recolhível, barra superior, cartões com bordas suaves e conteúdo central amplo.
- Caixa de entrada em três áreas no desktop: filtros/conversas, histórico e dados/ações; no celular, navegação progressiva.
- Cinco paletas: `azul`, `esmeralda`, `violeta`, `rubi` e `ambar`.
- Cada paleta funciona em modo claro e escuro, persistidos no navegador e no perfil quando autenticado.
- Atualizações do chat usam polling HTMX de 3 segundos no MVP.

## Arquitetura HTTP e regras de negócio

- A aplicação é API-first e expõe seus recursos internos em `/api/v1/` com Django Ninja.
- Views Django apenas autenticam o acesso à página e renderizam o shell HTML; não acessam models, não alteram dados e não contêm consultas ou regras de negócio.
- Após carregar uma página, HTMX ou JavaScript consulta e altera dados exclusivamente pela API.
- Cada módulo possui `api/router.py`, `api/endpoints/` e `api/schemas/`, separados por recurso.
- Endpoints limitam-se a autenticação, autorização inicial, validação do schema, chamada de um service e tradução de erros de domínio para HTTP.
- Services são a única camada autorizada a coordenar models, transações, isolamento por empresa, auditoria, providers e enfileiramento assíncrono.
- Models preservam persistência e invariantes locais, sem orquestrar HTTP ou serviços externos.
- Schemas Pydantic não atravessam a fronteira da API: endpoints convertem schemas para argumentos explícitos ou comandos de domínio.
- Autenticação da interface usa sessão Django e proteção CSRF. Webhooks usam credencial própria, limite de requisições e validação de origem configurada.
- A API possui documentação OpenAPI, respostas de erro padronizadas e testes de contrato.

## Cenário de aceite

1. Administrador entra e configura empresa, IA e WhatsApp.
2. Testes de conexão confirmam OpenAI e Evolution API.
3. Cliente envia texto; webhook registra uma única mensagem e abre a conversa.
4. Celery monta o contexto, solicita resposta e registra a saída.
5. Evolution API entrega a resposta; painel mostra o status.
6. Atendente assume; novas mensagens não acionam a IA.
7. Atendente responde e finaliza; todo o histórico e as mudanças ficam auditados.
