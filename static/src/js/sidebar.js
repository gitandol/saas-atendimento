(() => {
  "use strict";

  /** Mantem apenas a regiao visivel no percurso de teclado do drawer. */
  function sincronizarAcessibilidadeDrawer({
    movel,
    aberto,
    sidebar,
    areaPrincipal,
  }) {
    const sidebarInerte = movel && !aberto;
    sidebar.inert = sidebarInerte;
    if (sidebarInerte) sidebar.setAttribute("aria-hidden", "true");
    else sidebar.removeAttribute("aria-hidden");
    areaPrincipal.inert = movel && aberto;
  }

  /** Remove controles sem caixa visual do ciclo de foco atual. */
  function obterFocaveisVisiveis(elementos) {
    return [...elementos].filter((elemento) => elemento.getClientRects().length > 0);
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = {
      obterFocaveisVisiveis,
      sincronizarAcessibilidadeDrawer,
    };
  }
  if (typeof window === "undefined" || typeof document === "undefined") return;

  const corpo = document.body;
  const sidebar = document.querySelector("#sidebar");
  const abrir = document.querySelector("[data-abrir-sidebar]");
  const recolher = document.querySelector("[data-recolher-sidebar]");
  const sobreposicao = document.querySelector("[data-fechar-sidebar]");
  const areaPrincipal = document.querySelector(".area-principal");
  const consultaMovel = window.matchMedia("(max-width: 767px)");
  let focoAnterior = null;

  if (!sidebar || !abrir || !areaPrincipal) return;

  /** Sincroniza inercia com o breakpoint e o estado visual atuais. */
  function sincronizarDrawer() {
    sincronizarAcessibilidadeDrawer({
      movel: consultaMovel.matches,
      aberto: corpo.classList.contains("sidebar-aberta"),
      sidebar,
      areaPrincipal,
    });
  }

  /** Informa a tecnologia assistiva sobre o estado do drawer. */
  function definirExpandido(expandido) {
    abrir.setAttribute("aria-expanded", String(expandido));
  }

  /** Abre o drawer movel e posiciona o foco na primeira navegacao. */
  function abrirDrawer() {
    focoAnterior = document.activeElement;
    corpo.classList.add("sidebar-aberta");
    sobreposicao.hidden = false;
    definirExpandido(true);
    sincronizarDrawer();
    sidebar.querySelector("a, button")?.focus();
  }

  /** Fecha o drawer e devolve o foco ao controle que o abriu. */
  function fecharDrawer() {
    corpo.classList.remove("sidebar-aberta");
    sobreposicao.hidden = true;
    definirExpandido(false);
    sincronizarDrawer();
    focoAnterior?.focus();
  }

  /** Alterna somente a largura do menu desktop e guarda o estado local. */
  function alternarDesktop() {
    const recolhida = corpo.classList.toggle("sidebar-recolhida");
    recolher.setAttribute("aria-expanded", String(!recolhida));
    try {
      window.localStorage.setItem("sidebar-recolhida", String(recolhida));
    } catch (_erro) {
      // O menu continua funcional mesmo quando o armazenamento e bloqueado.
    }
  }

  try {
    const recolhida = window.localStorage.getItem("sidebar-recolhida") === "true";
    corpo.classList.toggle("sidebar-recolhida", recolhida);
    recolher?.setAttribute("aria-expanded", String(!recolhida));
  } catch (_erro) {
    corpo.classList.remove("sidebar-recolhida");
  }

  abrir.addEventListener("click", abrirDrawer);
  sobreposicao?.addEventListener("click", fecharDrawer);
  recolher?.addEventListener("click", alternarDesktop);
  document.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape" && corpo.classList.contains("sidebar-aberta")) {
      fecharDrawer();
      return;
    }
    if (evento.key !== "Tab" || !corpo.classList.contains("sidebar-aberta")) {
      return;
    }
    const focaveis = obterFocaveisVisiveis(
      sidebar.querySelectorAll("a[href], button:not([disabled])"),
    );
    const primeiro = focaveis[0];
    const ultimo = focaveis.at(-1);
    if (evento.shiftKey && document.activeElement === primeiro) {
      evento.preventDefault();
      ultimo?.focus();
    } else if (!evento.shiftKey && document.activeElement === ultimo) {
      evento.preventDefault();
      primeiro?.focus();
    }
  });
  consultaMovel.addEventListener("change", (evento) => {
    if (!evento.matches) fecharDrawer();
    else sincronizarDrawer();
  });
  sincronizarDrawer();
})();
