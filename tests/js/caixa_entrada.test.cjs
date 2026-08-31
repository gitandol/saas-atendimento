"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  acaoDoSubmit,
  prepararAcaoConversa,
  calcularScrollPreservado,
  deveRolarAoFim,
  estadoDosControles,
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


test("habilita resposta somente para o responsavel humano atual", () => {
  assert.deepEqual(
    estadoDosControles({
      modo: "HUMANO",
      estado: "ABERTA",
      atendenteId: "u-1",
      usuarioId: "u-1",
    }),
    {
      acoes: ["devolver-para-ia", "finalizar"],
      podeResponder: true,
      mostraModoReabertura: false,
    },
  );
  assert.equal(
    estadoDosControles({
      modo: "HUMANO",
      estado: "ABERTA",
      atendenteId: "u-2",
      usuarioId: "u-1",
    }).podeResponder,
    false,
  );
});


test("oferece reabertura e bloqueia resposta quando finalizada", () => {
  assert.deepEqual(
    estadoDosControles({
      modo: "IA",
      estado: "FINALIZADA",
      atendenteId: "",
      usuarioId: "u-1",
    }),
    {
      acoes: ["reabrir"],
      podeResponder: false,
      mostraModoReabertura: true,
    },
  );
});


test("submit sem botao nao escolhe uma transicao implicitamente", () => {
  assert.equal(acaoDoSubmit(null), null);
  assert.equal(
    acaoDoSubmit({dataset: {acaoConversa: "finalizar"}}),
    "finalizar",
  );
});


test("acao informa sua rota no botao antes da submissao do HTMX", () => {
  const atributos = new Map();
  const botao = {
    dataset: {acaoConversa: "assumir"},
    setAttribute(nome, valor) {
      atributos.set(nome, valor);
    },
  };

  assert.equal(prepararAcaoConversa(botao, "conversa-1"), true);
  assert.equal(
    atributos.get("formaction"),
    "/api/v1/atendimento/conversas/conversa-1/assumir",
  );
});
