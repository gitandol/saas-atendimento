# Monitoramento

Use `GET /api/v1/saude` para liveness do processo. Use `GET /api/v1/saude/dependencias` para banco, Redis e worker; estado `degradado` não derruba a liveness. OpenAI e Evolution são observadas nas operações e podem degradar sem tornar o processo indisponivel.

Logs são uma linha JSON com timestamp, nivel, logger, evento e correlacao. Campos opcionais permitidos: empresa, conversa, mensagem, tarefa, duracao e resultado. Conteudo, telefone, prompt, token e segredo são descartados.

Alerte para: liveness indisponivel, dependencia degradada, repeticao de `429`, falhas finais de envio, indisponibilidade da IA e crescimento da fila. Correlacione HTTP, Celery e providers pelo `X-Correlation-ID`; não use payloads como chave de busca.
