"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  obterFocaveisVisiveis,
  sincronizarAcessibilidadeDrawer,
} = require("../../static/src/js/sidebar.js");

function elementoFalso() {
  const atributos = new Map();
  return {
    inert: false,
    atributos,
    setAttribute(nome, valor) {
      atributos.set(nome, valor);
    },
    removeAttribute(nome) {
      atributos.delete(nome);
    },
  };
}

test("retira sidebar fechada do teclado e bloqueia fundo quando aberta", () => {
  const sidebar = elementoFalso();
  const areaPrincipal = elementoFalso();

  sincronizarAcessibilidadeDrawer({
    movel: true,
    aberto: false,
    sidebar,
    areaPrincipal,
  });
  assert.equal(sidebar.inert, true);
  assert.equal(sidebar.atributos.get("aria-hidden"), "true");
  assert.equal(areaPrincipal.inert, false);

  sincronizarAcessibilidadeDrawer({
    movel: true,
    aberto: true,
    sidebar,
    areaPrincipal,
  });
  assert.equal(sidebar.inert, false);
  assert.equal(sidebar.atributos.has("aria-hidden"), false);
  assert.equal(areaPrincipal.inert, true);
});

test("ignora botao desktop oculto ao conter foco do drawer movel", () => {
  const primeiroLink = {getClientRects: () => [1]};
  const ultimoLink = {getClientRects: () => [1]};
  const botaoDesktopOculto = {getClientRects: () => []};

  const focaveis = obterFocaveisVisiveis([
    primeiroLink,
    ultimoLink,
    botaoDesktopOculto,
  ]);

  assert.deepEqual(focaveis, [primeiroLink, ultimoLink]);
});
