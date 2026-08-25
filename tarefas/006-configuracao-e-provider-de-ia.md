# Tarefa 006 — Configuração segura e provider de IA

**Objetivo:** configurar e testar uma integração OpenAI sem acoplar o domínio ao fornecedor.

**Dependências:** tarefa 005.

**Arquivos:**

- Criar: `apps/ia/models/configuracao_ia.py`, `apps/ia/api/schemas/configuracao_ia.py`.
- Criar: `apps/ia/integrations/protocolos.py`, `apps/ia/integrations/openai.py`.
- Criar: `apps/ia/services/{criptografia,testar_configuracao,obter_provider}.py`.
- Criar: `apps/ia/api/router.py`, `apps/ia/api/endpoints/configuracao_ia.py`, `apps/ia/views/paginas/configuracao_ia.py`.
- Criar: `templates/ia/configuracao.html`, `docs/funcionalidades/configuracao-de-ia.md` e testes espelhados.

**Produz:** protocolo `ProviderIA.gerar_resposta(mensagens, modelo) -> RespostaIA`, `obter_provider(empresa)` e endpoints `GET/PUT /api/v1/ia/configuracao` e `POST /api/v1/ia/teste`.

## Contratos

```python
@dataclass(frozen=True)
class RespostaIA:
    """Representa texto e métricas retornados por um provider de linguagem."""
    texto: str
    modelo: str
    tokens_entrada: int
    tokens_saida: int


class ProviderIA(Protocol):
    """Define a operação de linguagem usada pelo domínio de atendimento."""
    def gerar_resposta(self, mensagens: list[dict[str, str]], modelo: str) -> RespostaIA: ...
```

## Ciclo TDD

- [x] Testar uma única configuração por empresa, campos `modelo`, `nome_assistente`, `personalidade`, `mensagem_saudacao`, `mensagem_falha` e `respostas_automaticas_ativas`.
- [x] Testar criptografia em repouso: valor persistido difere da chave e a chave nunca aparece em `repr`, respostas, auditoria ou logs.
- [x] Testar provider com cliente HTTP mockado: sucesso, timeout, 401, 429, resposta vazia e payload inválido.
- [x] Testar endpoints de consulta, atualização e conexão sem salvar credencial vazia ou devolver segredo existente ao navegador.
- [x] Confirmar falhas antes da implementação.
- [x] Implementar `ProviderIA` e `ProviderOpenAI` usando timeout explícito e exceções de domínio `CredencialIAInvalida`, `LimiteIAExcedido`, `IAIndisponivel`.
- [x] Implementar services de consulta, edição e teste em que campo de chave vazio preserva a chave atual e ação separada permite removê-la.
- [x] Criar página-shell que carrega e envia configurações pela API; o endpoint não instancia models ou provider diretamente.
- [x] Testar schemas `422`, autenticação `401/403`, indisponibilidade `503` e limite externo `429` com corpo de erro padronizado.
- [x] Auditar alterações com segredo sanitizado, criar ajuda e executar regressão.

## Critérios de aceite

- Teste de conexão informa sucesso ou erro acionável sem expor detalhes sensíveis.
- Somente OpenAI está habilitada, mas o serviço de atendimento depende do protocolo.
- Nenhum teste automatizado chama a OpenAI real.

**Commit sugerido:** `feat: adiciona configuracao e provider openai`

## Registro de execução

- Data: 2026-08-25
- Vermelho observado: 2 falhas de modelo/criptografia, 8 de provider, 12 de services/API e 3 de página antes das respectivas implementações.
- Implementação realizada: configuração única por empresa, criptografia Fernet, protocolo e provider OpenAI, services isolados, API segura, página-shell e ajuda contextual.
- Refatorações: cliente HTTP injetável, contratos públicos sem segredo, handlers comuns de autenticação/validação e inclusão da app no import-linter.
- Comandos e resultados: `ruff check .` aprovado; `ruff format --check .` com 196 arquivos formatados; `manage.py check` sem problemas; migrações consistentes e aplicadas; `uv run pytest -q` com 166 testes aprovados.
- Commit: `feat: adiciona configuracao e provider openai`
