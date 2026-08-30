# Webhooks Evolution

Cada empresa recebe URL com UUID e token HMAC proprio. Trate a URL inteira como segredo, aceite somente HTTPS fora da rede Docker e nunca registre token, telefone ou corpo.

A fronteira aceita JSON, limita o corpo a 262144 bytes e aplica 60 requisicoes por minuto por empresa/origem. Respostas `200` podem indicar `recebido`, `duplicado` ou `ignorado`; `401` autenticação, `409` integração inativa, `413` tamanho, `429` limite e `503` fila indisponivel.

Para rotacionar o token, rotacione `SECRET_KEY` em janela controlada, atualize a URL na Evolution e considere que todas as sessoes Django serão invalidadas. Reenvios são seguros pelo identificador externo dentro de cada empresa.
