# Reformulacao visual do layout

## Objetivo

Atualizar a linguagem visual do SaaS de atendimento tomando como referencia o acabamento escuro, vibrante e concentrado do Compra Certa, sem copiar sua identidade nem alterar contratos de API, regras de negocio ou fluxos de autenticacao. A sidebar existente permanece como estrutura principal da area autenticada.

## Escopo

- Redesenhar tokens, superficies, tipografia, espacamentos, inputs e botoes.
- Preservar as cinco paletas: azul, esmeralda, violeta, rubi e ambar.
- Manter modos CLARO, ESCURO e SISTEMA com persistencia local e autenticada.
- Reformular o login em duas colunas no desktop e uma coluna no celular.
- Refinar sidebar, barra superior, cartoes, alertas e conteudo administrativo.
- Manter responsividade, acessibilidade e comportamento JavaScript existentes.

## Fora de escopo

- Alterar autenticacao, endpoints, models, services ou auditoria.
- Remover a sidebar ou substituir a navegacao principal por um menu de topo.
- Copiar textos, marca, icones proprietarios ou elementos de negocio da referencia.
- Criar dashboards ou funcionalidades ainda nao previstas nas tarefas do MVP.

## Direcao visual

O modo escuro sera a expressao mais marcante do sistema: fundo quase preto, superficies elevadas em tons grafite, bordas discretas e brilhos decorativos derivados da cor primaria. O modo claro manterá a mesma hierarquia usando fundo neutro claro, superficies brancas e acentos saturados com contraste equivalente.

Cada paleta usara uma versao vibrante de sua identidade:

- azul eletrico;
- verde esmeralda/lima;
- violeta luminoso;
- rosa-rubi vibrante;
- amarelo-ambar intenso.

As cores continuarao centralizadas nos tokens CSS. Componentes nao receberao cores de negocio fixas. Efeitos decorativos usarao misturas ou transparencias derivadas de `--cor-primaria`.

A tipografia sera local, sem dependencia externa. Titulos terao peso forte, escala mais expressiva e entrelinha curta. Rotulos e marcadores poderao usar caixa alta, tamanho reduzido e maior espacamento entre letras. Textos de apoio permanecerao discretos, mas legiveis.

## Login

No desktop, a pagina publica tera cabecalho compacto com marca e controle de tema. O corpo sera centralizado em uma largura maxima e dividido em:

1. apresentacao do produto a esquerda, com marcador, titulo forte, descricao e beneficios curtos voltados ao atendimento inteligente;
2. cartao de acesso a direita, com titulo, texto auxiliar, campos empilhados, mensagem de erro e botao primario em largura total.

O fundo podera usar grade pontilhada e halos suaves sem interferir na leitura. Em telas menores que 768 px, a apresentacao sera simplificada e o formulario assumira uma unica coluna, com prioridade visual e largura total segura.

## Shell autenticado

A sidebar continuara fixa no desktop, recolhivel e convertida em drawer no celular. Seu fundo sera integrado ao restante da aplicacao, com marca compacta, itens de navegacao mais espacados e estado ativo indicado pela cor primaria.

A barra superior sera visualmente leve e compacta. Busca, seletor de tema, notificacoes, ajuda e perfil manterao os comportamentos atuais. A area de conteudo tera largura maxima centralizada dentro do espaco restante, evitando que cartoes se estendam excessivamente em monitores largos.

## Componentes

- Cartoes: superficie elevada, borda sutil, sombra contida e raios moderados.
- Inputs e selects: altura confortavel, fundo contrastante, borda visivel e estado de foco derivado da paleta.
- Botoes primarios: preenchimento vibrante, texto de alto contraste e estados hover/focus sem deslocamento de layout.
- Botoes secundarios: superficie neutra e borda que ganha a cor primaria.
- Alertas: estrutura atual preservada, com hierarquia melhor entre titulo e mensagem.
- Listas e regioes internas: superficies aninhadas mais escuras ou claras que o cartao, sem depender de cores fixas.

## Responsividade

- 360 px: login em coluna unica; sidebar como drawer; acoes secundarias condensadas.
- 768 px: transicao para composicoes amplas sem sobreposicao de controles.
- 1280 px: login em duas colunas e shell com conteudo centralizado.
- 1920 px: largura maxima impede espacos e linhas excessivamente longos.

## Acessibilidade

- Contraste minimo WCAG AA em todas as paletas e luminosidades.
- Foco visivel em links, inputs, selects, botoes e controles da sidebar.
- Ordem de tabulacao coerente e estados `aria-expanded` preservados.
- Landmarks, rotulos e mensagens com `role="alert"` mantidos.
- Animacoes e transicoes reduzidas quando `prefers-reduced-motion: reduce`.
- Decoracoes de fundo nao recebem foco nem transmitem informacao essencial.

## Estrategia de implementacao

A mudanca evoluira o design system existente. Templates receberao apenas as classes e agrupamentos semanticos necessarios; a maior parte da linguagem visual ficara em `temas.css` e `componentes.css`. Scripts de tema e sidebar serao preservados, salvo ajuste comprovadamente necessario para acessibilidade.

## Validacao

O trabalho seguira TDD. A regressao cobrira a composicao do login, o shell autenticado e a presenca das cinco paletas. Tambem serao executados:

- testes Python e JavaScript completos;
- teste automatizado de contraste;
- lint e formatacao;
- build CSS local e no Docker;
- checks Django e de migracoes;
- verificacao HTTP dos assets;
- validacao responsiva e por teclado nas larguras de referencia.

## Criterios de aceite

- O login lembra a composicao e o acabamento da referencia sem copiar sua marca.
- A sidebar permanece funcional no desktop e celular.
- As cinco paletas compartilham a nova linguagem vibrante.
- Modos claro e escuro mantem contraste e legibilidade.
- Inputs, botoes e cartoes possuem hierarquia visual clara.
- Persistencia de tema e contratos HTTP nao sofrem regressao.
