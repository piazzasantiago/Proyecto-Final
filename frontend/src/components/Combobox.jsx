import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

/** Cuántas opciones se muestran de a poco al desplazarse por la lista. */
const PAGINA = 20;

/** Minúsculas y sin tildes, para buscar sin importar cómo se escriba. */
function normalizar(texto) {
  return String(texto ?? "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

/**
 * Combobox con buscador y carga a medida que se desplaza (estilo select2).
 * Reemplaza al <select> nativo en los formularios.
 *
 * Es compatible con el patrón del <select>: `onChange` recibe un objeto con
 * `target.name` y `target.value` (texto), y `required` / `onInvalid` siguen
 * funcionando con la validación nativa del formulario. Además de `target`,
 * `onChange` recibe `option` (la opción elegida completa, con sus `data`).
 *
 * Dos modos de datos:
 *  · `options`: lista ya cargada [{ value, label, sub?, disabled?, data? }].
 *    Busca en el navegador y va mostrando de a 20 al llegar al final.
 *  · `loader({ search, page })`: pide cada página al servidor y devuelve
 *    { results: [opción], hasMore }. Busca en el servidor (con demora al
 *    tipear) y trae la página siguiente al llegar al final de la lista.
 *
 * `valueLabel` es el texto a mostrar si la opción elegida no está en la lista
 * (por ejemplo, un registro que se dio de baja después de usarlo).
 * El buscador se muestra siempre con `loader` y, con `options`, cuando hay
 * `minForSearch` opciones o más (en listas cortas, como Estado, estorbaría).
 */
export default function Combobox({
  name,
  value,
  onChange,
  options = [],
  loader,
  valueLabel,
  placeholder = "Seleccioná...",
  searchPlaceholder = "Buscar...",
  required = false,
  disabled = false,
  onInvalid,
  compact = false,
  minForSearch = 8,
  emptyText = "Sin resultados",
}) {
  const [abierto, setAbierto] = useState(false);
  const [busqueda, setBusqueda] = useState("");
  const [visibles, setVisibles] = useState(PAGINA);
  const [resaltado, setResaltado] = useState(-1);
  const [pos, setPos] = useState(null);
  // Modo servidor
  const [remotos, setRemotos] = useState([]);
  const [pagina, setPagina] = useState(0);
  const [hayMas, setHayMas] = useState(false);
  const [cargando, setCargando] = useState(false);
  const [fallo, setFallo] = useState(false);

  const triggerRef = useRef(null);
  const panelRef = useRef(null);
  const listaRef = useRef(null);
  const buscadorRef = useRef(null);
  const ocultoRef = useRef(null);
  const loaderRef = useRef(loader);
  const pedidoRef = useRef(0);
  // Opciones vistas: permiten mostrar el rótulo de la selección en modo servidor.
  const conocidas = useRef(new Map());

  loaderRef.current = loader;
  const esRemoto = typeof loader === "function";
  const hayValor = value !== undefined && value !== null && String(value) !== "";

  // ── Datos ──────────────────────────────────────────────────────────────────
  const filtradas = useMemo(() => {
    if (esRemoto) return remotos;
    const q = normalizar(busqueda).trim();
    return q ? options.filter((o) => normalizar(`${o.label} ${o.sub ?? ""}`).includes(q)) : options;
  }, [esRemoto, remotos, options, busqueda]);

  const lista = esRemoto ? filtradas : filtradas.slice(0, visibles);

  const mostrarBuscador = esRemoto || options.length >= minForSearch;

  const etiqueta = useMemo(() => {
    if (!hayValor) return "";
    const clave = String(value);
    const opcion = options.find((o) => String(o.value) === clave) ?? conocidas.current.get(clave);
    return opcion?.label ?? valueLabel ?? "";
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, options, valueLabel, remotos, hayValor]);

  const cargarPagina = useCallback(async (numero, texto, reemplazar) => {
    const id = ++pedidoRef.current;
    setCargando(true);
    setFallo(false);
    try {
      const r = await loaderRef.current({ search: texto, page: numero });
      if (id !== pedidoRef.current) return; // llegó una respuesta vieja
      r.results.forEach((o) => conocidas.current.set(String(o.value), o));
      setRemotos((previas) => (reemplazar ? r.results : [...previas, ...r.results]));
      setPagina(numero);
      setHayMas(Boolean(r.hasMore));
    } catch {
      if (id === pedidoRef.current) setFallo(true);
    } finally {
      if (id === pedidoRef.current) setCargando(false);
    }
  }, []);

  // Al abrir o al cambiar la búsqueda (modo servidor): primera página otra vez.
  useEffect(() => {
    if (!esRemoto || !abierto) return undefined;
    const espera = setTimeout(() => cargarPagina(1, busqueda.trim(), true), busqueda ? 300 : 0);
    return () => clearTimeout(espera);
  }, [esRemoto, abierto, busqueda, cargarPagina]);

  // Cada búsqueda nueva vuelve al principio de la lista.
  useEffect(() => {
    setVisibles(PAGINA);
    setResaltado(filtradas.length ? 0 : -1);
    if (listaRef.current) listaRef.current.scrollTop = 0;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [busqueda, abierto]);

  // ── Posición del panel (portal: no lo recortan los modales ni las tablas) ──
  const ubicar = useCallback(() => {
    const el = triggerRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const debajo = window.innerHeight - r.bottom;
    const arriba = r.top;
    const subir = debajo < 280 && arriba > debajo;
    setPos({
      left: r.left,
      width: Math.max(r.width, 220),
      ...(subir
        ? { bottom: window.innerHeight - r.top + 4, maxHeight: Math.min(320, arriba - 12) }
        : { top: r.bottom + 4, maxHeight: Math.min(320, debajo - 12) }),
    });
  }, []);

  useLayoutEffect(() => {
    if (!abierto) return undefined;
    ubicar();
    window.addEventListener("resize", ubicar);
    window.addEventListener("scroll", ubicar, true);
    return () => {
      window.removeEventListener("resize", ubicar);
      window.removeEventListener("scroll", ubicar, true);
    };
  }, [abierto, ubicar]);

  // Cierra al hacer clic afuera.
  useEffect(() => {
    if (!abierto) return undefined;
    function afuera(e) {
      if (panelRef.current?.contains(e.target) || triggerRef.current?.contains(e.target)) return;
      cerrar();
    }
    document.addEventListener("mousedown", afuera);
    return () => document.removeEventListener("mousedown", afuera);
  }, [abierto]);

  // Foco al abrir: en el buscador si hay, si no en la lista (para el teclado).
  useEffect(() => {
    if (!abierto || !pos) return;
    (buscadorRef.current ?? panelRef.current)?.focus({ preventScroll: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [abierto, pos === null]);

  function abrir() {
    if (disabled) return;
    setBusqueda("");
    setRemotos([]);
    setPagina(0);
    setHayMas(false);
    setAbierto(true);
  }

  function cerrar() {
    setAbierto(false);
    setPos(null);
  }

  function elegir(opcion) {
    if (opcion.disabled) return;
    conocidas.current.set(String(opcion.value), opcion);
    onChange?.({
      target: {
        name,
        value: String(opcion.value),
        // Los formularios limpian el mensaje de validación al cambiar el valor.
        setCustomValidity: (m) => ocultoRef.current?.setCustomValidity(m),
      },
      option: opcion,
    });
    // El campo oculto ya tiene su valor nuevo: la validación anterior no aplica.
    ocultoRef.current?.setCustomValidity("");
    cerrar();
    triggerRef.current?.focus();
  }

  // ── Carga a medida que se desplaza ─────────────────────────────────────────
  function alDesplazar(e) {
    const el = e.currentTarget;
    if (el.scrollTop + el.clientHeight < el.scrollHeight - 32) return;
    if (esRemoto) {
      if (hayMas && !cargando) cargarPagina(pagina + 1, busqueda.trim(), false);
    } else if (visibles < filtradas.length) {
      setVisibles((v) => v + PAGINA);
    }
  }

  // ── Teclado ────────────────────────────────────────────────────────────────
  function moverResaltado(delta) {
    if (!lista.length) return;
    const siguiente = Math.min(Math.max((resaltado < 0 ? -1 : resaltado) + delta, 0), lista.length - 1);
    setResaltado(siguiente);
    listaRef.current?.children[siguiente]?.scrollIntoView({ block: "nearest" });
    if (!esRemoto && siguiente >= visibles - 2) setVisibles((v) => v + PAGINA);
  }

  function alTeclear(e) {
    if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      cerrar();
      triggerRef.current?.focus();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      moverResaltado(1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      moverResaltado(-1);
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (lista[resaltado]) elegir(lista[resaltado]);
    }
  }

  function alTeclearBoton(e) {
    if (["ArrowDown", "ArrowUp", "Enter", " "].includes(e.key)) {
      e.preventDefault();
      abrir();
    }
  }

  return (
    <div className={`cb${compact ? " cb-compact" : ""}`}>
      <button
        type="button"
        ref={triggerRef}
        className={`cb-trigger${abierto ? " abierto" : ""}${hayValor ? "" : " vacio"}`}
        onClick={() => (abierto ? cerrar() : abrir())}
        onKeyDown={alTeclearBoton}
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={abierto}
      >
        <span className="cb-texto">{hayValor ? etiqueta || "…" : placeholder}</span>
        <i className="fa-solid fa-chevron-down cb-flecha"></i>
      </button>

      {/* Campo oculto: mantiene la validación nativa (obligatorio + mensaje propio). */}
      <input
        ref={ocultoRef}
        className="cb-oculto"
        tabIndex={-1}
        aria-hidden="true"
        value={hayValor ? String(value) : ""}
        onChange={() => {}}
        required={required}
        onInvalid={onInvalid}
      />

      {abierto &&
        pos &&
        createPortal(
          <div
            ref={panelRef}
            className="cb-panel"
            style={{ ...pos }}
            tabIndex={-1}
            onKeyDown={alTeclear}
          >
            {mostrarBuscador && (
              <div className="cb-buscador">
                <i className="fa-solid fa-magnifying-glass"></i>
                <input
                  ref={buscadorRef}
                  type="text"
                  value={busqueda}
                  onChange={(e) => setBusqueda(e.target.value)}
                  placeholder={searchPlaceholder}
                  autoComplete="off"
                />
              </div>
            )}
            <div className="cb-lista" ref={listaRef} onScroll={alDesplazar} role="listbox">
              {lista.map((o, i) => {
                const elegida = hayValor && String(o.value) === String(value);
                return (
                  <div
                    key={o.value}
                    role="option"
                    aria-selected={elegida}
                    className={`cb-op${i === resaltado ? " resaltada" : ""}${elegida ? " elegida" : ""}${
                      o.disabled ? " deshabilitada" : ""
                    }`}
                    onMouseEnter={() => setResaltado(i)}
                    onClick={() => elegir(o)}
                  >
                    <span className="cb-op-texto">
                      {o.label}
                      {o.sub && <small>{o.sub}</small>}
                    </span>
                    {elegida && <i className="fa-solid fa-check"></i>}
                  </div>
                );
              })}
              {cargando && <div className="cb-estado">Cargando...</div>}
              {fallo && !cargando && <div className="cb-estado">No se pudieron cargar las opciones.</div>}
              {!cargando && !fallo && lista.length === 0 && <div className="cb-estado">{emptyText}</div>}
            </div>
          </div>,
          document.body
        )}
    </div>
  );
}
