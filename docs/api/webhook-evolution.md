# Webhook Evolution

O endpoint externo recebe somente mensagens de texto da Evolution API:

```text
POST /api/v1/webhooks/evolution/<uuid_empresa>/<token>/
Content-Type: application/json
```

O corpo tem limite de 256 KiB. O identificador da empresa vem exclusivamente da
URL; qualquer empresa informada no JSON e ignorada. O token e um HMAC-SHA256
derivado de `SECRET_KEY` e do UUID:

```python
from apps.whatsapp.services.validar_webhook import gerar_token_webhook

token = gerar_token_webhook(empresa_id=empresa.id)
```

O token deve ser tratado como segredo e configurado na URL de callback da
instancia Evolution. Trocar `SECRET_KEY` invalida os tokens existentes.

## Evento textual aceito

```json
{
  "event": "messages.upsert",
  "data": {
    "key": {
      "id": "identificador-unico",
      "remoteJid": "5568999999999@s.whatsapp.net",
      "fromMe": false
    },
    "pushName": "Cliente",
    "message": {
      "conversation": "Preciso de ajuda"
    },
    "messageTimestamp": 1725192000
  }
}
```

`MESSAGES_UPSERT` e `extendedTextMessage.text` tambem sao aceitos. Eventos
desconhecidos e mensagens de midia recebem HTTP 200 com status `ignorado`, sem
criar conversa ou resposta automatica.

## Respostas

- `200 recebido`: mensagem criada e processamento publicado.
- `200 duplicado`: identificador ja processado; nenhuma nova task foi criada.
- `200 ignorado`: evento fora do MVP.
- `400 evento_invalido`: JSON ou mensagem textual incompletos.
- `401 webhook_nao_autorizado`: empresa ou token invalidos.
- `409 whatsapp_inativo`: integracao desativada.
- `413 payload_muito_grande`: corpo acima de 256 KiB.
- `415 tipo_nao_suportado`: corpo sem `application/json`.
- `503 processamento_indisponivel`: mensagem persistida, mas o broker recusou
  a publicacao; a Evolution deve repetir exatamente o mesmo webhook.

Uma publicacao em andamento usa lease de dois minutos. Se o processo encerrar
antes de alcançar o broker, repeticoes recebem 503 enquanto o lease estiver
ativo e podem reivindicar a mensagem novamente depois da expiracao. O consumidor
e idempotente porque a entrega do broker segue semantica de pelo menos uma vez.

As respostas incluem `X-Correlation-ID`. Logs registram somente correlacao,
empresa, identificadores tecnicos e tipo do evento; texto e token nao sao
copiados.
