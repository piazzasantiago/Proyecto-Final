/**
 * Mide la altura del panel de detalle (escritorio) y la deja en --alto-detalle, que usa index.css para
 * que un panel más alto que la pantalla se quede fijo recién cuando su parte de abajo ya se vio.
 * El panel se vuelve a crear al elegir otro registro, así que se vigila la página y se mide el nuevo.
 */
export function activarAltoDetalle() {
  const main = document.querySelector(".main");
  if (!main || typeof ResizeObserver === "undefined") return () => {};

  const medidor = new ResizeObserver((entradas) => {
    for (const e of entradas) e.target.style.setProperty("--alto-detalle", `${Math.round(e.target.offsetHeight)}px`);
  });
  let actual = null;
  const buscar = () => {
    const panel = main.querySelector(".page-body-split > .detail-panel");
    if (panel === actual) return;
    if (actual) medidor.unobserve(actual);
    actual = panel;
    if (actual) medidor.observe(actual);
  };
  const vigilante = new MutationObserver(buscar);
  vigilante.observe(main, { childList: true, subtree: true });
  buscar();
  return () => {
    vigilante.disconnect();
    medidor.disconnect();
  };
}
