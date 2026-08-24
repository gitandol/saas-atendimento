"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const {
  criarFilaSincronizacao,
  criarGuardaHidratacao,
} = require("../../static/src/js/tema.js");

test("serializa mudancas rapidas e persiste a ultima por ultimo", async () => {
  const eventos = [];
  let liberarPrimeira;
  const primeiraPendente = new Promise((resolver) => {
    liberarPrimeira = resolver;
  });
  const enviar = async (preferencia) => {
    eventos.push(`inicio:${preferencia.tema}`);
    if (preferencia.tema === "azul") await primeiraPendente;
    eventos.push(`fim:${preferencia.tema}`);
  };
  const agendar = criarFilaSincronizacao(enviar);

  const primeira = agendar({tema: "azul", modo: "CLARO"});
  const ultima = agendar({tema: "rubi", modo: "ESCURO"});
  await new Promise((resolver) => setImmediate(resolver));

  assert.deepEqual(eventos, ["inicio:azul"]);
  liberarPrimeira();
  await Promise.all([primeira, ultima]);
  assert.deepEqual(eventos, [
    "inicio:azul",
    "fim:azul",
    "inicio:rubi",
    "fim:rubi",
  ]);
});

test("ignora GET antigo depois de uma alteracao local", async () => {
  let liberarResposta;
  const respostaPendente = new Promise((resolver) => {
    liberarResposta = resolver;
  });
  const aplicadas = [];
  const guarda = criarGuardaHidratacao({
    buscar: () => respostaPendente,
    aplicar: (preferencia) => aplicadas.push(preferencia),
  });

  const carregamento = guarda.carregar();
  guarda.marcarAlteracaoLocal();
  liberarResposta({tema: "azul", modo: "CLARO"});
  await carregamento;

  assert.deepEqual(aplicadas, []);
});
