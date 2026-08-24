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

- [ ] Testar uma única configuração por empresa, campos `modelo`, `nome_assistente`, `personalidade`, `mensagem_saudacao`, `mensagem_falha` e `respostas_automaticas_ativas`.
- [ ] Testar criptografia em repouso: valor persistido difere da chave e a chave nunca aparece em `repr`, respostas, auditoria ou logs.
- [ ] Testar provider com cliente HTTP mockado: sucesso, timeout, 401, 429, resposta vazia e payload inválido.
- [ ] Testar endpoints de consulta, atualização e conexão sem salvar credencial vazia ou devolver segredo existente ao navegador.
- [ ] Confirmar falhas antes da implementação.
- [ ] Implementar `ProviderIA` e `ProviderOpenAI` usando timeout explícito e exceções de domínio `CredencialIAInvalida`, `LimiteIAExcedido`, `IAIndisponivel`.
- [ ] Implementar services de consulta, edição e teste em que campo de chave vazio preserva a chave atual e ação separada permite removê-la.
- [ ] Criar página-shell que carrega e envia configurações pela API; o endpoint não instancia models ou provider diretamente.
- [ ] Testar schemas `422`, autenticação `401/403`, indisponibilidade `503` e limite externo `429` com corpo de erro padronizado.
- [ ] Auditar alterações com segredo sanitizado, criar ajuda e executar regressão.

## Critérios de aceite

- Teste de conexão informa sucesso ou erro acionável sem expor detalhes sensíveis.
- Somente OpenAI está habilitada, mas o serviço de atendimento depende do protocolo.
- Nenhum teste automatizado chama a OpenAI real.

**Commit sugerido:** `feat: adiciona configuracao e provider openai`
