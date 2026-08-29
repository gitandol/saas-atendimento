# Dashboard operacional

O dashboard apresenta um retrato atual da empresa ativa, sem metas ou graficos analiticos.

## Informacoes exibidas

- conversas abertas, separadas entre IA e atendimento humano;
- mensagens recebidas e enviadas no dia civil do fuso da empresa;
- mensagens atualmente marcadas com falha;
- estado da OpenAI e da conexao com a Evolution API.

Os dados sao atualizados automaticamente a cada 30 segundos. Para reduzir consultas repetidas, o mesmo retrato pode permanecer em cache por ate 30 segundos.

## Alertas

Quando a OpenAI nao esta ativa, use **Configurar IA** para revisar a credencial e as respostas automaticas. Quando o WhatsApp nao esta conectado, use **Configurar WhatsApp** para revisar ou reconectar a instancia.

Todas as contagens pertencem somente a empresa ativa. Um dashboard sem conversas continua valido e exibe zero em cada metrica.
