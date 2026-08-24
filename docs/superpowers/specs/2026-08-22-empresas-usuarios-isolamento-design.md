# Empresas, usuarios e isolamento logico

## Objetivo

Garantir que usuarios autenticados acessem somente recursos pertencentes a uma
empresa na qual possuam associacao ativa, sem aceitar identificadores enviados
pelo cliente como fonte de autorizacao.

## Dominio

`Usuario` estende `AbstractUser`, usa UUID como chave primaria e e-mail unico
como identificador de autenticacao. `Empresa` usa UUID e representa o tenant.
`MembroEmpresa` associa usuario e empresa, registra o papel `ADMINISTRADOR` ou
`ATENDENTE`, possui estado ativo e impede associacoes duplicadas.

## Empresa ativa e isolamento

A empresa ativa pode ser lembrada na sessao pelo UUID da empresa, mas cada
resolucao consulta novamente uma associacao ativa do usuario. Um valor ausente
ou invalido nunca concede acesso. Quando a sessao ainda nao possui uma selecao,
a primeira associacao ativa em ordem deterministica e usada e registrada na
sessao. Usuario anonimo ou sem associacao ativa nao possui empresa ativa.

Consultas de negocio recebem explicitamente o usuario ou a empresa ativa e
filtram no banco antes de recuperar objetos. Um UUID pertencente a outro tenant
produz ausencia de objeto e, na fronteira HTTP, resposta `404`, evitando IDOR e
enumeracao de recursos.

## Camadas

- Models definem apenas dados e restricoes persistentes.
- Services executam autenticacao, encerramento de sessao, perfil, resolucao da
  empresa ativa e consultas isoladas.
- Middleware anexa a empresa ativa validada ao request, sem aceitar selecao de
  empresa em formulario como autorizacao.
- Endpoints Ninja autenticam, validam schemas, aplicam CSRF, delegam aos
  services e traduzem resultados para `401`, `403`, `404` ou `422`.
- Views Django renderizam somente os shells de login e perfil.

## Autenticacao e seguranca

O login usa sessao Django e e-mail/senha. Requisicoes de login passam pela
protecao CSRF e por throttling basico no cache, indexado sem armazenar senha.
Credenciais invalidas retornam `401`. Redirecionamentos posteriores ao login
aceitam apenas destinos locais considerados seguros pelo Django. Logout encerra
a sessao por endpoint autenticado e protegido por CSRF.

O perfil retorna somente dados do usuario autenticado, da empresa ativa e do
papel da associacao. Administrador e atendente sao diferenciados pelo papel
resolvido no service; operacoes administrativas recusam atendentes.

## Contratos HTTP

Os endpoints ficam sob `/api/v1/autenticacao/` e incluem login e logout. O
perfil e carregado pela API versionada para alimentar a pagina-shell. Payloads
malformados retornam `422`; credenciais invalidas, `401`; ausencia de empresa
ativa, `403`; e UUID externo ao tenant, `404`.

## Testes e verificacao

O desenvolvimento segue ciclos vermelho, verde e refatoracao. Os testes cobrem
modelos UUID, e-mail unico, papeis, associacao inativa, empresa ativa, isolamento
de querysets, IDOR, login/logout, CSRF, throttling, redirect seguro, contratos
HTTP e fronteiras de importacao/delegacao. Ao final serao executados testes
isolados, suite completa, migracoes, `ruff check .`, `ruff format --check .` e
`python manage.py check`.

## Fora de escopo

Nao serao implementados convites, troca visual de empresa, recuperacao de senha,
auditoria/revisoes da tarefa 003 ou permissoes de modulos posteriores.
