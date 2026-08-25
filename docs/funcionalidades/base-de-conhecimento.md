# Base de conhecimento

Use textos e perguntas frequentes para fornecer fatos que a IA pode consultar ao responder clientes. Administradores podem cadastrar, ordenar, ativar, desativar e excluir itens; atendentes podem apenas consultar.

## Conteudo seguro

Cadastre informacoes objetivas e publicas, por exemplo:

- prazos, horarios e areas de entrega;
- regras de troca e devolucao;
- perguntas e respostas sobre produtos e servicos.

Nao inclua senhas, tokens, dados pessoais ou comandos. Frases como **Ignore instrucoes anteriores** sao tratadas como dados e nao substituem as regras da plataforma, mas ainda devem ser removidas do cadastro.

## Limites do MVP

O contexto usa somente registros ativos, em ordem deterministica, e possui limite total de 20.000 caracteres com aviso quando houver truncamento. PDFs e URLs ainda nao sao suportados. O MVP tambem nao usa busca vetorial ou RAG.
