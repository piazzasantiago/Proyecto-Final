/**
 * Comportamiento propio de pantallas chicas (celular y tablet, hasta 1100 px):
 *
 *   1. El detalle de un registro se muestra como una hoja que sube desde abajo (en pantalla ancha
 *      es una columna al costado y no hace falta). Se abre al tocar una tarjeta o fila de la
 *      lista, y se cierra con la X, tocando afuera o con Escape. El estado vive en
 *      `data-detalle="abierto"` del <html>; el aspecto está en index.css.
 *   2. En las tablas, cada celda recibe `data-label` con el título de su columna, para que en el
 *      celular, donde la fila se convierte en tarjeta, se sepa qué es cada dato.
 *
 * Las filas y tarjetas de todas las pantallas ya llevan `data-tutorial-fila`, así que se usa ese
 * mismo atributo para detectar el toque (no hace falta tocar cada pantalla).
 */

const PANTALLA_CHICA = "(max-width:1100px)";

export const esPantallaChica = () => window.matchMedia(PANTALLA_CHICA).matches;

export function abrirDetalleMovil() {
  if (esPantallaChica()) document.documentElement.dataset.detalle = "abierto";
}

export function cerrarDetalleMovil() {
  delete document.documentElement.dataset.detalle;
  // Se limpia cualquier arrastre o altura media que haya quedado en la hoja.
  document.querySelectorAll(".page-body-split > .detail-panel").forEach((p) => {
    p.style.transform = ""; p.style.transition = ""; p.style.maxHeight = ""; delete p.dataset.alto;
  });
}

/** Marca las columnas cuyos valores son todos números (para alinearlas a la derecha en escritorio). */
const ES_NUMERO = /^-?[\d.,]+\s?(%|kg|L|hs|aves|m²|huevos)?$/;
function marcarNumericas(tabla) {
  const filas = [...tabla.querySelectorAll("tbody tr")];
  const ths = [...tabla.querySelectorAll("thead th")];
  ths.forEach((th, i) => {
    const celdas = filas.map((f) => f.children[i]).filter((c) => c && c.textContent.trim() && c.textContent.trim() !== "—");
    // Los códigos con ceros a la izquierda (Nº de comprobante, etc.) son identificadores, no cifras.
    const numerica = celdas.length > 0 && celdas.every((c) => ES_NUMERO.test(c.textContent.trim()) && !/^0\d/.test(c.textContent.trim()));
    const valor = numerica ? "1" : "";
    if ((th.dataset.num || "") !== valor) {
      if (valor) th.dataset.num = valor; else delete th.dataset.num;
    }
    filas.forEach((f) => {
      const c = f.children[i];
      if (c && (c.dataset.num || "") !== valor) { if (valor) c.dataset.num = valor; else delete c.dataset.num; }
    });
  });
}

function etiquetarTablas() {
  document.querySelectorAll("table.data-table").forEach((tabla) => {
    marcarNumericas(tabla);
    const titulos = [...tabla.querySelectorAll("thead th")].map((th) => th.textContent.trim());
    tabla.querySelectorAll("tbody tr").forEach((fila) => {
      [...fila.children].forEach((celda, i) => {
        if (titulos[i] && celda.dataset.label !== titulos[i]) celda.dataset.label = titulos[i];
      });
    });
  });
}

/**
 * Filtros colapsados (celular): cada barra de filtros muestra solo el buscador y un botón «Filtros»
 * con la cantidad de filtros aplicados; al tocarlo se despliegan los demás. El botón se agrega acá
 * (no en cada pantalla); el estado vive en `data-filtros` de la barra.
 */
function prepararFiltros() {
  document.querySelectorAll(".toolbar[data-tutorial='sec-filtros']").forEach((barra) => {
    let boton = barra.querySelector(":scope > .filtros-btn");
    if (!boton) {
      boton = document.createElement("button");
      boton.type = "button";
      boton.className = "filtros-btn";
      boton.setAttribute("aria-expanded", "false");
      boton.innerHTML = '<i class="fa-solid fa-sliders"></i><span>Filtros</span><b class="filtros-n"></b>';
      const buscador = barra.querySelector(":scope > .search-box");
      if (buscador) buscador.after(boton);
      else barra.prepend(boton);
    }
    // El placeholder largo no entra junto al botón: se acorta y el texto completo pasa a la etiqueta accesible.
    const campo = barra.querySelector(".search-box input");
    if (campo && campo.placeholder !== "Buscar…" && esPantallaChica() && window.innerWidth <= 700) {
      campo.setAttribute("aria-label", campo.placeholder);
      campo.placeholder = "Buscar…";
    }
    // Cuántos filtros de lista desplegable están aplicados (distintos de la primera opción, «Todos»).
    const n = [...barra.querySelectorAll("select")].filter((sel) => sel.selectedIndex > 0).length;
    const marca = boton.querySelector(".filtros-n");
    if (marca.textContent !== (n ? String(n) : "")) marca.textContent = n ? String(n) : "";
    boton.dataset.con = n ? "1" : "";
    const abierto = barra.dataset.filtros === "abierto";
    if (boton.getAttribute("aria-expanded") !== String(abierto)) boton.setAttribute("aria-expanded", String(abierto));
  });
}

/**
 * Gestos de la hoja de detalle: se arrastra desde el asa con el dedo pegado (1:1), hacia abajo.
 * Al soltar se proyecta hacia dónde iba (con la velocidad del dedo) y se elige entre tres alturas:
 * completa, media o cerrada. Si se interrumpe, arranca desde donde está en pantalla. Arriba del
 * tope se resiste (efecto elástico). Las animaciones usan el resorte de la hoja (--resorte).
 */
function gestosHoja() {
  let g = null; // estado del arrastre en curso

  const panel = (el) => el.closest(".page-body-split > .detail-panel");
  const resorte = () => getComputedStyle(document.documentElement).getPropertyValue("--resorte").trim() || "ease-out";
  const elastico = (x, dim) => (x * dim * 0.55) / (dim + 0.55 * Math.abs(x));

  function abajo(e) {
    if (!esPantallaChica() || e.button > 0) return;
    const asa = e.target.closest?.(".detalle-cerrar");
    if (!asa || e.target.closest(".detalle-x")) return;
    const p = panel(asa);
    if (!p) return;
    // Altura completa de la hoja (si estaba en altura media, se vuelve a medir sin el tope).
    const estabaMedia = p.dataset.alto === "medio";
    const topAntes = p.getBoundingClientRect().top;
    if (estabaMedia) { p.style.maxHeight = ""; delete p.dataset.alto; }
    const altoCompleto = p.getBoundingClientRect().height;
    // Desde dónde parte: la posición actual en pantalla, también si una animación estaba en curso.
    const off0 = estabaMedia ? altoCompleto - Math.round(altoCompleto * 0.5) : Math.max(topAntes - (window.innerHeight - altoCompleto), 0);
    g = { p, id: e.pointerId, y0: e.clientY, off0, altoCompleto, medio: Math.round(altoCompleto * 0.5), muestras: [[performance.now(), e.clientY]], off: off0 };
    p.style.transition = "none";
    p.style.transform = `translateY(${g.off}px)`;
    asa.setPointerCapture(e.pointerId);
  }

  function mover(e) {
    if (!g || e.pointerId !== g.id) return;
    let off = g.off0 + (e.clientY - g.y0);
    if (off < 0) off = -elastico(-off, 120); // resistencia hacia arriba
    g.off = off;
    g.p.style.transform = `translateY(${off}px)`;
    g.muestras.push([performance.now(), e.clientY]);
    if (g.muestras.length > 6) g.muestras.shift();
    const velo = document.querySelector(".detalle-velo");
    if (velo) velo.style.opacity = String(Math.max(0, 1 - Math.max(off, 0) / g.altoCompleto));
  }

  function soltar(e) {
    if (!g || e.pointerId !== g.id) return;
    const { p, muestras, altoCompleto, medio } = g;
    const primero = muestras[0];
    const ultimo = muestras[muestras.length - 1];
    const v = ultimo[0] > primero[0] ? ((ultimo[1] - primero[1]) / (ultimo[0] - primero[0])) * 1000 : 0; // px/s
    // Proyección tipo desplazamiento: hasta dónde llegaría con esa velocidad.
    const proyectado = g.off + ((v / 1000) * 0.998) / (1 - 0.998) * 0.12;
    const puntos = [0, altoCompleto - medio, altoCompleto];
    const destino = puntos.reduce((a, b) => (Math.abs(b - proyectado) < Math.abs(a - proyectado) ? b : a));
    const velo = document.querySelector(".detalle-velo");
    g = null;
    p.style.transition = `transform .5s ${resorte()}`;
    if (velo) velo.style.opacity = "";
    if (destino === altoCompleto) {
      p.style.transform = `translateY(${altoCompleto}px)`;
      setTimeout(() => { cerrarDetalleMovil(); }, 230);
      return;
    }
    p.style.transform = `translateY(${destino}px)`;
    if (destino > 0) {
      // Altura media: se fija con una altura máxima, para que el contenido siga pudiéndose recorrer.
      setTimeout(() => {
        if (!p.isConnected) return;
        p.style.transition = "none";
        p.style.transform = "";
        p.style.maxHeight = `${medio}px`;
        p.dataset.alto = "medio";
      }, 500);
    } else {
      setTimeout(() => { if (p.isConnected) { p.style.transition = ""; p.style.transform = ""; } }, 520);
    }
  }

  document.addEventListener("pointerdown", abajo, true);
  document.addEventListener("pointermove", mover, true);
  document.addEventListener("pointerup", soltar, true);
  document.addEventListener("pointercancel", soltar, true);
  return () => {
    document.removeEventListener("pointerdown", abajo, true);
    document.removeEventListener("pointermove", mover, true);
    document.removeEventListener("pointerup", soltar, true);
    document.removeEventListener("pointercancel", soltar, true);
  };
}

/** Activa el comportamiento. Devuelve la función que lo desactiva. */
export function activarMovil() {
  const alTocar = (e) => {
    if (!esPantallaChica()) return;
    const bf = e.target.closest?.(".filtros-btn");
    if (bf) {
      const barra = bf.parentElement;
      barra.dataset.filtros = barra.dataset.filtros === "abierto" ? "" : "abierto";
      prepararFiltros();
      return;
    }
    const fila = e.target.closest?.("[data-tutorial-fila]");
    // Los botones y enlaces internos (p. ej. el "ojito" de auditoría) no abren el detalle.
    if (fila && !e.target.closest("button, a, .col-auditoria")) abrirDetalleMovil();
  };
  // Atajos de teclado en escritorio: ↑/↓ recorren la lista, «/» enfoca el buscador, «N» crea uno nuevo.
  const atajos = (e) => {
    if (esPantallaChica() || e.metaKey || e.ctrlKey || e.altKey || e.defaultPrevented) return;
    const t = e.target;
    if (t.closest?.("input, select, textarea, [contenteditable], button, a")) return;
    if (document.querySelector(".modal-overlay.active, .tut-velo")) return;
    if (e.key === "/") {
      const campo = document.querySelector(".search-box input");
      if (campo) { e.preventDefault(); campo.focus(); campo.select(); }
    } else if (e.key === "n" || e.key === "N") {
      const nuevo = document.querySelector(".page-header .btn-green:not([disabled])");
      if (nuevo) { e.preventDefault(); nuevo.click(); }
    } else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      const filas = [...document.querySelectorAll("[data-tutorial-fila]")].filter((f) => f.offsetParent !== null);
      if (filas.length === 0) return;
      const i = filas.findIndex((f) => f.classList.contains("card-selected") || f.classList.contains("row-selected"));
      const sig = e.key === "ArrowDown" ? Math.min(i + 1, filas.length - 1) : Math.max(i - 1, 0);
      if (sig === i) return;
      e.preventDefault();
      filas[sig].click();
      filas[sig].scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  };
  const alTeclear = (e) => {
    if (e.key === "Escape" && document.documentElement.dataset.detalle) cerrarDetalleMovil();
  };

  let pendiente = 0;
  const alCambiar = () => {
    cancelAnimationFrame(pendiente);
    pendiente = requestAnimationFrame(() => {
      etiquetarTablas();
      observarEncabezado();
      actualizarTitulo();
      prepararFiltros();
      // El botón principal pasa a ser un botón flotante (solo ícono): necesita un nombre accesible.
      // Con el encabezado fijo (escritorio) las acciones quedan solo con el ícono: también necesitan nombre y tooltip.
      document.querySelectorAll(".page-header .btn:not([aria-label])").forEach((b) => {
        const texto = b.textContent.trim();
        if (!texto) return;
        b.setAttribute("aria-label", texto);
        if (!b.title) b.title = texto;
      });
      // Si el registro abierto desapareció (se eliminó o se cambió de pantalla), se cierra la hoja.
      if (document.documentElement.dataset.detalle && !document.querySelector(".page-body-split > .detail-panel")) {
        cerrarDetalleMovil();
      }
    });
  };
  // Altura del encabezado fijo (escritorio): la usan el encabezado de la tabla y el panel de detalle para pegarse debajo.
  let encabezadoObservado = null;
  const vidrio = document.createElement("div");
  vidrio.className = "encabezado-vidrio";
  vidrio.setAttribute("aria-hidden", "true");
  document.body.appendChild(vidrio);
  const ubicarVidrio = () => {
    const main = document.querySelector(".main");
    const h = encabezadoObservado ? Math.round(encabezadoObservado.getBoundingClientRect().height) : 0;
    document.documentElement.style.setProperty("--alto-enc", `${h}px`);
    if (!main || !h) return;
    const r = main.getBoundingClientRect();
    vidrio.style.left = `${Math.round(r.left) + 1}px`;
    vidrio.style.width = `${Math.round(r.width) - 2}px`;
    // El desenfoque necesita una capa más alta que la visible: se recorta al alto real del encabezado.
    vidrio.style.height = `${h + 200}px`;
    vidrio.style.clipPath = `inset(0 0 200px 0)`;
  };
  window.addEventListener("resize", ubicarVidrio);
  const medidor = typeof ResizeObserver !== "undefined" ? new ResizeObserver(ubicarVidrio) : null;
  const observarEncabezado = () => {
    if (!medidor) return;
    const ph = document.querySelector(".main .page-header");
    if (ph === encabezadoObservado) return;
    medidor.disconnect();
    encabezadoObservado = ph;
    if (ph) medidor.observe(ph);
    else document.documentElement.style.setProperty("--alto-enc", "0px");
    ubicarVidrio();
  };
  const observador = new MutationObserver(alCambiar);
  observador.observe(document.body, { childList: true, subtree: true });
  alCambiar();

  // Título de la página en la barra superior: aparece cuando el título grande ya salió de la vista.
  const actualizarTitulo = () => {
    const h1 = document.querySelector(".main h1");
    const caja = document.querySelector(".topbar-titulo");
    if (!h1 || !caja) return;
    if (caja.textContent !== h1.textContent) caja.textContent = h1.textContent;
    const fuera = h1.getBoundingClientRect().bottom < 64;
    if (fuera !== (document.documentElement.dataset.titulo === "1")) {
      if (fuera) document.documentElement.dataset.titulo = "1";
      else delete document.documentElement.dataset.titulo;
    }
  };

  // Barra superior de vidrio: se "materializa" apenas el contenido empieza a pasar por debajo.
  const alDesplazar = (e) => {
    const t = e.target;
    const y = Math.max(window.scrollY, t && t.scrollTop ? t.scrollTop : 0);
    actualizarTitulo();
    const sobre = y > 6;
    if (sobre !== (document.documentElement.dataset.scroll === "1")) {
      if (sobre) document.documentElement.dataset.scroll = "1";
      else delete document.documentElement.dataset.scroll;
    }
    marcarTitulosFijos();
  };

  // Fila de títulos de la tabla: cuando se queda fija (ya no está en su lugar natural) pasa a tener
  // las esquinas rectas; con las redondeadas se vería pasar el contenido por las puntas.
  const marcarTitulosFijos = () => {
    const th = document.querySelector(".data-table thead th");
    const tabla = th?.closest("table");
    const fijo = Boolean(th && tabla && th.getBoundingClientRect().top - tabla.getBoundingClientRect().top > 0.5);
    if (fijo !== (document.documentElement.dataset.titulosFijos === "1")) {
      if (fijo) document.documentElement.dataset.titulosFijos = "1";
      else delete document.documentElement.dataset.titulosFijos;
    }
  };

  // En una ventana emergente, el campo que se toca se lleva al centro para que el teclado no lo tape.
  const alEnfocar = (e) => {
    if (!esPantallaChica()) return;
    const el = e.target;
    if (!el.matches?.("input, select, textarea") || !el.closest(".modal-overlay")) return;
    setTimeout(() => el.scrollIntoView({ block: "center", behavior: "smooth" }), 320);
  };
  document.addEventListener("focusin", alEnfocar);
  const alCambiarCampo = () => alCambiar();
  document.addEventListener("change", alCambiarCampo, true);
  const quitarGestos = gestosHoja();
  document.addEventListener("click", alTocar, true);
  document.addEventListener("keydown", alTeclear);
  document.addEventListener("keydown", atajos);
  document.addEventListener("scroll", alDesplazar, { capture: true, passive: true });
  return () => {
    quitarGestos();
    document.removeEventListener("focusin", alEnfocar);
    document.removeEventListener("scroll", alDesplazar, true);
    document.removeEventListener("change", alCambiarCampo, true);
    delete document.documentElement.dataset.scroll;
    delete document.documentElement.dataset.titulo;
    delete document.documentElement.dataset.titulosFijos;
    cancelAnimationFrame(pendiente);
    observador.disconnect();
    medidor?.disconnect();
    window.removeEventListener("resize", ubicarVidrio);
    vidrio.remove();
    document.removeEventListener("click", alTocar, true);
    document.removeEventListener("keydown", alTeclear);
    document.removeEventListener("keydown", atajos);
    cerrarDetalleMovil();
  };
}
