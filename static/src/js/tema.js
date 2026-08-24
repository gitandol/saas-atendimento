(() => {
  "use strict";

  /** Cria uma fila que preserva a ordem das preferencias enviadas. */
  function criarFilaSincronizacao(enviar) {
    let fila = Promise.resolve();
    return (preferencia) => {
      fila = fila
        .catch(() => undefined)
        .then(() => enviar(preferencia));
      return fila;
    };
  }

  /** Impede uma resposta remota antiga de apagar uma escolha local recente. */
  function criarGuardaHidratacao({buscar, aplicar}) {
    let houveAlteracaoLocal = false;
    return {
      marcarAlteracaoLocal() {
        houveAlteracaoLocal = true;
      },
      async carregar() {
        const preferencia = await buscar();
        if (!houveAlteracaoLocal && preferencia) aplicar(preferencia);
      },
    };
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = {
      criarFilaSincronizacao,
      criarGuardaHidratacao,
    };
  }
  if (typeof window === "undefined" || typeof document === "undefined") return;

  const CHAVE = "preferencia-visual";
  const TEMAS = ["azul", "esmeralda", "violeta", "rubi", "ambar"];
  const MODOS = ["CLARO", "ESCURO", "SISTEMA"];
  const consultaEscuro = window.matchMedia("(prefers-color-scheme: dark)");

  /** Retorna somente valores locais pertencentes ao contrato visual. */
  function lerPreferencia() {
    try {
      const salva = JSON.parse(window.localStorage.getItem(CHAVE) || "{}");
      return {
        tema: TEMAS.includes(salva.tema) ? salva.tema : "azul",
        modo: MODOS.includes(salva.modo) ? salva.modo : "SISTEMA",
      };
    } catch (_erro) {
      return {tema: "azul", modo: "SISTEMA"};
    }
  }

  /** Guarda a preferencia no navegador sem impedir o uso quando indisponivel. */
  function salvarPreferencia(preferencia) {
    try {
      window.localStorage.setItem(CHAVE, JSON.stringify(preferencia));
    } catch (_erro) {
      document.querySelector("[data-estado-tema]")?.replaceChildren(
        "O navegador nao permitiu salvar o tema.",
      );
    }
  }

  /** Resolve SISTEMA e aplica tokens antes de atualizar os controles. */
  function aplicarPreferencia(preferencia) {
    const escuro = preferencia.modo === "ESCURO" ||
      (preferencia.modo === "SISTEMA" && consultaEscuro.matches);
    document.documentElement.dataset.tema = preferencia.tema;
    document.documentElement.classList.toggle("dark", escuro);
    document.querySelectorAll("[data-tema-opcao]").forEach((botao) => {
      botao.setAttribute(
        "aria-pressed",
        String(botao.dataset.temaOpcao === preferencia.tema),
      );
    });
    const seletorModo = document.querySelector("[data-modo-tema]");
    if (seletorModo) seletorModo.value = preferencia.modo;
  }

  /** Obtem um token CSRF pelo contrato ja exposto pela API. */
  async function obterCsrf() {
    const cookie = document.cookie
      .split("; ")
      .find((item) => item.startsWith("csrftoken="));
    if (cookie) return decodeURIComponent(cookie.split("=")[1]);
    const resposta = await fetch("/api/v1/autenticacao/csrf", {
      credentials: "same-origin",
    });
    if (!resposta.ok) throw new Error("CSRF indisponivel");
    return (await resposta.json()).csrf_token;
  }

  /** Sincroniza a mudanca autenticada sem recarregar a pagina. */
  async function sincronizar(preferencia) {
    if (document.body.dataset.autenticado !== "true") return;
    const estado = document.querySelector("[data-estado-tema]");
    try {
      const csrf = await obterCsrf();
      const resposta = await fetch("/api/v1/preferencias/visual", {
        method: "PUT",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf,
        },
        body: JSON.stringify(preferencia),
      });
      if (!resposta.ok) throw new Error("Falha ao sincronizar");
      if (estado) estado.textContent = "Preferencia salva.";
    } catch (_erro) {
      if (estado) estado.textContent = "Tema salvo somente neste navegador.";
    }
  }

  const agendarSincronizacao = criarFilaSincronizacao(sincronizar);

  /** Aplica e persiste uma alteracao iniciada pelo usuario. */
  function alterar(parcial) {
    guardaHidratacao.marcarAlteracaoLocal();
    const preferencia = {...lerPreferencia(), ...parcial};
    aplicarPreferencia(preferencia);
    salvarPreferencia(preferencia);
    agendarSincronizacao(preferencia);
  }

  /** Busca a preferencia persistida depois que o shell ja esta utilizavel. */
  async function buscarNoServidor() {
    if (document.body.dataset.autenticado !== "true") return null;
    try {
      const resposta = await fetch("/api/v1/preferencias/visual", {
        credentials: "same-origin",
      });
      if (!resposta.ok) return null;
      const preferencia = await resposta.json();
      if (!TEMAS.includes(preferencia.tema) || !MODOS.includes(preferencia.modo)) {
        return null;
      }
      return preferencia;
    } catch (_erro) {
      // A preferencia local ja aplicada continua funcional sem rede.
      return null;
    }
  }

  const guardaHidratacao = criarGuardaHidratacao({
    buscar: buscarNoServidor,
    aplicar(preferencia) {
      salvarPreferencia(preferencia);
      aplicarPreferencia(preferencia);
    },
  });

  document.querySelectorAll("[data-tema-opcao]").forEach((botao) => {
    botao.addEventListener("click", () => alterar({tema: botao.dataset.temaOpcao}));
  });
  document.querySelector("[data-modo-tema]")?.addEventListener("change", (evento) => {
    alterar({modo: evento.currentTarget.value});
  });
  consultaEscuro.addEventListener("change", () => {
    const preferencia = lerPreferencia();
    if (preferencia.modo === "SISTEMA") aplicarPreferencia(preferencia);
  });

  aplicarPreferencia(lerPreferencia());
  guardaHidratacao.carregar();
})();
