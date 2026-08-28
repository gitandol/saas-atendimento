(() => {
  "use strict";

  /** Mantem somente a primeira ocorrencia de cada mensagem ainda nao exibida. */
  function filtrarMensagensNovas(idsExistentes, mensagens) {
    const vistos = new Set(idsExistentes);
    return [...mensagens].filter((mensagem) => {
      const id = mensagem.dataset.mensagemId;
      if (!id || vistos.has(id)) return false;
      vistos.add(id);
      return true;
    });
  }

  /** Informa se a pessoa permanece perto do fim do historico. */
  function deveRolarAoFim({
    scrollTop,
    clientHeight,
    scrollHeight,
    margem = 48,
  }) {
    return scrollHeight - scrollTop - clientHeight <= margem;
  }

  /** Compensa a altura adicionada acima da mensagem que estava visivel. */
  function calcularScrollPreservado({scrollTop, alturaAntes, alturaDepois}) {
    return scrollTop + Math.max(0, alturaDepois - alturaAntes);
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = {
      calcularScrollPreservado,
      deveRolarAoFim,
      filtrarMensagensNovas,
    };
  }
  if (typeof window === "undefined" || typeof document === "undefined") return;

  const historico = document.querySelector("#historico-conversa");
  const formulario = document.querySelector("#formulario-resposta-manual");
  const texto = formulario?.querySelector("[name='texto']");
  const enviar = formulario?.querySelector("[type='submit']");
  const feedback = document.querySelector("#feedback-resposta");
  const erroCaixa = document.querySelector("#erro-caixa");
  let conversaAtiva = null;
  let preservarTopo = false;
  let alturaAntes = 0;
  let scrollAntes = 0;
  let rolarDepois = true;

  if (!historico || !formulario || !texto || !enviar) return;

  /** Retorna o token CSRF emitido para a sessao web. */
  function obterCsrf() {
    const item = document.cookie
      .split(";")
      .map((valor) => valor.trim())
      .find((valor) => valor.startsWith("csrftoken="));
    return item ? decodeURIComponent(item.split("=").slice(1).join("=")) : "";
  }

  /** Exibe uma unica area no fluxo progressivo de telas pequenas. */
  function mostrarPainel(nome) {
    document.querySelectorAll("[data-painel]").forEach((painel) => {
      if (painel.dataset.painel === nome) {
        painel.setAttribute("data-painel-ativo", "");
      } else {
        painel.removeAttribute("data-painel-ativo");
      }
    });
  }

  /** Atualiza a consulta incremental a partir da ultima mensagem renderizada. */
  function atualizarPolling() {
    if (!conversaAtiva) return;
    const mensagens = historico.querySelectorAll("[data-mensagem-id]");
    const ultima = mensagens.item(mensagens.length - 1)?.dataset.mensagemId;
    const base = `/api/v1/atendimento/conversas/${conversaAtiva}/mensagens`;
    historico.setAttribute("hx-get", ultima ? `${base}?depois_de=${ultima}` : base);
    historico.setAttribute("hx-trigger", "every 3s");
    historico.setAttribute("hx-swap", "beforeend");
    window.htmx?.process(historico);
  }

  /** Remove repeticoes defensivamente apos qualquer troca parcial. */
  function removerDuplicadas() {
    const mensagens = historico.querySelectorAll("[data-mensagem-id]");
    const unicas = new Set(filtrarMensagensNovas(new Set(), mensagens));
    mensagens.forEach((mensagem) => {
      if (!unicas.has(mensagem)) mensagem.remove();
    });
    historico.querySelectorAll(".carregar-anteriores").forEach((botao, indice) => {
      if (indice > 0) botao.remove();
    });
  }

  document.body.addEventListener("click", (evento) => {
    const seletorPainel = evento.target.closest("[data-mostrar-painel]");
    if (seletorPainel) {
      mostrarPainel(seletorPainel.dataset.mostrarPainel);
      return;
    }
    const item = evento.target.closest("[data-abrir-conversa]");
    if (!item) return;
    conversaAtiva = item.dataset.conversaId;
    document.querySelectorAll("[data-abrir-conversa]").forEach((conversa) => {
      conversa.setAttribute("aria-current", String(conversa === item));
    });
    document.querySelector("#nome-conversa").textContent = item.dataset.nome;
    document.querySelector("#numero-conversa").textContent = item.dataset.numero;
    document.querySelector("#modo-conversa").textContent = item.dataset.modo;
    document.querySelector("#estado-conversa").textContent = item.dataset.estado;
    document.querySelector("#atendente-conversa").textContent =
      item.dataset.atendente || "Sem atendente";
    const aberta = item.dataset.estado === "ABERTA";
    texto.disabled = !aberta;
    enviar.disabled = !aberta;
    formulario.setAttribute(
      "hx-post",
      `/api/v1/atendimento/conversas/${conversaAtiva}/mensagens`,
    );
    window.htmx?.process(formulario);
    mostrarPainel("conversa");
    window.htmx?.ajax(
      "POST",
      `/api/v1/atendimento/conversas/${conversaAtiva}/marcar-lida`,
      {
        swap: "none",
        headers: {"X-CSRFToken": obterCsrf()},
      },
    );
  });

  document.body.addEventListener("htmx:beforeRequest", (evento) => {
    if (erroCaixa) erroCaixa.hidden = true;
    if (evento.detail.target !== historico) return;
    preservarTopo =
      evento.detail.elt?.getAttribute("hx-swap") === "afterbegin";
    alturaAntes = historico.scrollHeight;
    scrollAntes = historico.scrollTop;
    rolarDepois = deveRolarAoFim(historico);
  });

  document.body.addEventListener("htmx:responseError", () => {
    if (erroCaixa) erroCaixa.hidden = false;
  });

  document.body.addEventListener("htmx:afterSwap", (evento) => {
    if (evento.detail.target !== historico) return;
    removerDuplicadas();
    if (preservarTopo) {
      historico.scrollTop = calcularScrollPreservado({
        scrollTop: scrollAntes,
        alturaAntes,
        alturaDepois: historico.scrollHeight,
      });
    } else if (rolarDepois) {
      historico.scrollTop = historico.scrollHeight;
    }
    preservarTopo = false;
    atualizarPolling();
  });

  document.body.addEventListener("htmx:afterRequest", (evento) => {
    if (evento.detail.elt !== formulario) return;
    let mensagem = "Nao foi possivel enviar a resposta.";
    if (evento.detail.successful) {
      texto.value = "";
      mensagem = "Resposta adicionada para envio.";
      window.htmx?.ajax("GET", historico.getAttribute("hx-get"), {
        target: historico,
        swap: "beforeend",
      });
    } else {
      try {
        mensagem = JSON.parse(evento.detail.xhr.responseText).mensagem || mensagem;
      } catch (_erro) {
        // A mensagem generica permanece quando a resposta nao e JSON.
      }
    }
    feedback.textContent = mensagem;
  });
})();
