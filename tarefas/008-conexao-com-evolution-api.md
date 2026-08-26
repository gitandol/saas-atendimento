# Tarefa 008 — Conexão de um WhatsApp pela Evolution API

**Objetivo:** configurar uma instância, exibir QR Code, consultar estado e validar conexão.

**Dependências:** tarefas 003, 004 e 005.

**Arquivos:**

- Criar: `apps/whatsapp/models/configuracao_whatsapp.py`, `apps/whatsapp/api/schemas/configuracao_whatsapp.py`.
- Criar: `apps/whatsapp/integrations/{protocolos,evolution}.py`.
- Criar: `apps/whatsapp/services/{criptografia,configurar_instancia,consultar_conexao}.py`.
- Criar: `apps/whatsapp/api/router.py`, `apps/whatsapp/api/endpoints/{configuracao,qrcode,estado_conexao}.py`, `apps/whatsapp/views/paginas/configuracao.py` e rotas/templates.
- Criar: `docs/funcionalidades/conexao-do-whatsapp.md` e testes espelhados.

**Produz:** `ProviderWhatsApp`, `ProviderEvolution`, configuração única por empresa e endpoints `/api/v1/whatsapp/configuracao`, `/qrcode`, `/estado`, `/conectar` e `/desconectar`.

## Contratos

```python
class EstadoConexao(StrEnum):
    """Normaliza estados externos exibidos ao operador."""
    DESCONECTADO = "DESCONECTADO"
    AGUARDANDO_QR = "AGUARDANDO_QR"
    CONECTADO = "CONECTADO"
    ERRO = "ERRO"


class ProviderWhatsApp(Protocol):
    """Isola as operações de mensageria requeridas pelo MVP."""
    def obter_qrcode(self) -> str: ...
    def consultar_estado(self) -> EstadoConexao: ...
    def enviar_texto(self, numero: str, texto: str, chave_idempotencia: str) -> str: ...
```

## Ciclo TDD

- [x] Testar uma configuração por empresa: `url_base`, `nome_instancia`, `chave_api_criptografada`, `ativo` e `estado`.
- [x] Testar cliente Evolution mockado para QR Code, conexão, timeout, 401, 404, 429 e JSON inválido.
- [x] Testar validação de URL HTTPS em produção e bloqueio de host local/metadata para reduzir SSRF.
- [x] Testar que API key é protegida com as mesmas garantias da chave da IA.
- [x] Confirmar falhas antes da implementação.
- [x] Implementar provider com timeout, limites de resposta e mapeamento para exceções de domínio.
- [x] Implementar services separados para consultar, atualizar, conectar, desconectar e obter QR Code; somente eles acessam model e provider.
- [x] Criar página-shell com status, QR Code temporário e ações HTMX contra endpoints Ninja, incluindo confirmação para conectar/desconectar.
- [x] Testar que endpoints não acessam models/providers diretamente e mapeiam erros de credencial, indisponibilidade e limite para o contrato HTTP comum.
- [x] Auditar mudanças, documentar ajuda e executar regressão.

## Critérios de aceite

- Empresa conecta exatamente uma instância e vê seu estado atual.
- QR Code não é persistido em histórico/auditoria e expira visualmente.
- Nenhum teste automatizado acessa uma Evolution API real.

**Commit sugerido:** `feat: adiciona conexao evolution api`

## Registro de execução

- Data: 2026-08-26
- Vermelho observado: 15 falhas iniciais pela ausencia de model, criptografia e provider; 23 falhas pela ausencia de services, API e pagina; regressões de segurança falharam antes das correções de DNS/redirect, streaming limitado, cache do QR e timeout durante streaming.
- Implementação realizada: app `whatsapp`, configuração única e segredo cifrado, provider Evolution, proteção SSRF, services autorizados e auditados, endpoints Ninja, pagina HTMX, QR temporário, migração e ajuda contextual.
- Refatorações: resposta externa passou a streaming limitado com fechamento garantido; DNS e redirects foram endurecidos; migração ficou independente do enum em runtime; imports e formatação foram normalizados.
- Comandos e resultados: testes do módulo e suíte completa verdes; `ruff check .`, `ruff format --check .`, `python manage.py check` e `makemigrations --check --dry-run` verdes; `whatsapp.0001` aplicada com `config.settings.teste`.
- Commit: `feat: adiciona conexao evolution api`
