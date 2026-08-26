# Conexao do WhatsApp

Esta pagina conecta uma unica instancia do WhatsApp por empresa usando a Evolution API.

## Configurar

Informe a URL publica da Evolution API, o nome da instancia e a chave API. Em producao, a URL deve usar HTTPS e nao pode apontar para enderecos locais, privados ou de metadata. A chave e criptografada antes de ser armazenada e nunca volta pela API.

## Conectar e consultar

Use **Conectar** para iniciar a instancia e depois **Exibir QR Code**. Leia o codigo no aplicativo WhatsApp antes que ele desapareca da tela em 60 segundos. O sistema consulta o estado periodicamente e mostra se a instancia esta desconectada, aguardando QR Code, conectada ou com erro.

Use **Desconectar** para encerrar a sessao atual. As acoes de configurar, conectar e desconectar pedem confirmacao quando necessario e ficam registradas na auditoria, sem chave API ou QR Code.
