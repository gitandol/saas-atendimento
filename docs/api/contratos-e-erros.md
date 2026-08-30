# Contratos e erros da API

A API interna usa `/api/v1/`, sessao Django e CSRF em mutacoes. A documentacao OpenAPI interna fica em `/api/v1/docs` e exige usuario staff. Webhooks possuem contrato separado e autenticacao propria.

Toda resposta inclui `X-Correlation-ID`. O cliente pode enviar um identificador com ate 80 caracteres seguros; valores invalidos são substituidos por UUID.

Erros de negocio usam:

```json
{"codigo": "codigo_estavel", "mensagem": "Mensagem segura."}
```

Principais status: `400` payload invalido, `401` autenticacao ausente, `403` permissao/CSRF, `404` recurso do tenant nao encontrado, `409` conflito, `413` corpo excessivo, `422` schema invalido, `429` limite e `503` dependencia indisponivel. Respostas nunca devolvem chaves, tokens, prompts completos ou detalhes de excecoes externas.

O webhook Evolution usa `POST /api/v1/webhooks/evolution/{empresa_id}/{token}/`, aceita apenas JSON textual de ate 262144 bytes e não usa sessao Django. Consulte [webhooks](../operacao/webhooks.md).
