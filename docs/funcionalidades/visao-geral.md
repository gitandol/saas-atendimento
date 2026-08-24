# Visao geral

O historico de auditoria permite que administradores acompanhem alteracoes feitas nos objetos da empresa ativa.

Cada evento informa a acao, o tipo do objeto, os campos alterados, o ator, a origem, a correlacao e o numero sequencial da revisao. **Snapshots e segredos nao sao exibidos pela API de historico.**

A restauracao reaplica uma revisao compativel com as regras atuais e cria um novo evento de restauracao. Nenhuma revisao anterior e apagada.
