"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  calcularScrollPreservado,
  deveRolarAoFim,
  filtrarMensagensNovas,
} = require("../../static/src/js/caixa_entrada.js");


test("filtra mensagens repetidas pelo identificador persistido", () => {
  const mensagens = [
    {dataset: {mensagemId: "m-1"}},
    {dataset: {mensagemId: "m-2"}},
    {dataset: {mensagemId: "m-2"}},
  ];

  assert.deepEqual(
    filtrarMensagensNovas(new Set(["m-1"]), mensagens),
    [mensagens[1]],
  );
});


test("rola automaticamente somente quando usuario esta no fim", () => {
  assert.equal(
    deveRolarAoFim({scrollTop: 500, clientHeight: 300, scrollHeight: 820}),
    true,
  );
  assert.equal(
    deveRolarAoFim({scrollTop: 100, clientHeight: 300, scrollHeight: 820}),
    false,
  );
});


test("preserva a mensagem visivel ao adicionar historico antigo", () => {
  assert.equal(
    calcularScrollPreservado({
      scrollTop: 120,
      alturaAntes: 900,
      alturaDepois: 1250,
    }),
    470,
  );
});
