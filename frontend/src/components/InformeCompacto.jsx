import { useEffect, useRef, useState } from "react";

/**
 * Informes en celular: cada fila es una tarjeta compacta (nombre, dato principal y una línea con
 * los datos más importantes) y al tocarla se abre una hoja desde abajo con todas las columnas,
 * igual que el detalle del resto de las secciones. Sin tablas ni deslizamiento lateral.
 *
 * Qué se muestra en la tarjeta depende del informe (COMPACTO): `v(clave)` devuelve el dato ya
 * formateado y `f` es la fila sin formatear.
 */
const COMPACTO = {
  produccion: {
    titulo: (v) => v("galpon"),
    sub: (v) => v("lote"),
    principal: (v) => `${v("huevos_total")} huevos`,
    extra: (v) => [`Postura ${v("postura_promedio")} %`, `${v("promedio_diario")} por día`],
    barra: "huevos_total",
  },
  lotes: {
    titulo: (v) => v("lote"),
    sub: (v, f) => `${v("galpon")} · ${f.etapa}`,
    principal: (v) => `${v("cantidad_actual")} gallinas`,
    extra: (v) => [`Mortandad ${v("mortandad")} (${v("mortandad_pct")} %)`, `${v("edad_semanas")} semanas`],
    barra: "cantidad_actual",
  },
  materias: {
    titulo: (v) => v("materia_prima"),
    sub: (v) => `Consumido ${v("consumido")} · Comprado ${v("comprado")}`,
    principal: (v, f) => `${v("stock_actual")} ${f.unidad ?? ""}`,
    extra: (v, f) => [`Mínimo ${v("stock_minimo")} ${f.unidad ?? ""}`],
    alerta: (f) => Boolean(f.bajo_minimo),
  },
  descartes: {
    titulo: (v) => v("item"),
    sub: (v, f) => `${v("fecha")}${f.galpon && f.galpon !== "—" ? ` · ${f.galpon}` : ""}`,
    principal: (v, f) => `${v("cantidad")} ${f.unidad ?? ""}`.trim(),
    extra: (v, f) => [f.tipo, f.motivo].filter((x) => x && x !== "—"),
  },
};

export default function InformeCompacto({ tab, informe, formatear }) {
  const [abierta, setAbierta] = useState(null);
  const cfg = COMPACTO[tab];
  const { columnas, filas, totales } = informe;
  const tipoDe = (clave) => columnas.find((c) => c.clave === clave)?.tipo;
  const dato = (f) => (clave) => formatear(f[clave], tipoDe(clave));

  // Al cambiar de informe o de filtros se cierra la hoja.
  useEffect(() => setAbierta(null), [informe]);

  if (!cfg) return null;
  const maximo = cfg.barra ? Math.max(0, ...filas.map((f) => Number(f[cfg.barra]) || 0)) : 0;
  const principales = totales ? columnas.filter((c) => totales[c.clave] !== undefined) : [];

  return (
    <div className="inf-lista">
      {totales && principales.length > 0 && (
        <div className="inf-resumen">
          <b>Total del período</b>
          <div>
            {principales.map((c) => (
              <span key={c.clave}>
                <small>{c.titulo}</small>
                {formatear(totales[c.clave], c.tipo)}
              </span>
            ))}
          </div>
        </div>
      )}

      {filas.map((f, i) => {
        const v = dato(f);
        const peso = maximo ? (Number(f[cfg.barra]) || 0) / maximo : 0;
        return (
          <button type="button" key={i} className="inf-fila" onClick={() => setAbierta(f)}>
            <span className="inf-fila-arriba">
              <b>{cfg.titulo(v, f)}</b>
              <span className={`inf-fila-valor${cfg.alerta?.(f) ? " alerta" : ""}`}>{cfg.principal(v, f)}</span>
            </span>
            <span className="inf-fila-sub">{cfg.sub(v, f)}</span>
            {cfg.extra && <span className="inf-fila-extra">{cfg.extra(v, f).join(" · ")}</span>}
            {cfg.barra && (
              <span className="inf-fila-barra" aria-hidden="true">
                <i style={{ width: `${Math.max(peso * 100, peso > 0 ? 3 : 0)}%` }}></i>
              </span>
            )}
          </button>
        );
      })}

      {abierta && (
        <HojaFila
          titulo={cfg.titulo(dato(abierta), abierta)}
          sub={cfg.sub(dato(abierta), abierta)}
          columnas={columnas}
          fila={abierta}
          formatear={formatear}
          onCerrar={() => setAbierta(null)}
        />
      )}
    </div>
  );
}

/** Hoja desde abajo con todas las columnas de la fila. Se cierra con la X, tocando afuera, arrastrando hacia abajo o con Escape. */
function HojaFila({ titulo, sub, columnas, fila, formatear, onCerrar }) {
  const hoja = useRef(null);
  const arrastre = useRef(null);

  useEffect(() => {
    const tecla = (e) => e.key === "Escape" && onCerrar();
    document.addEventListener("keydown", tecla);
    return () => document.removeEventListener("keydown", tecla);
  }, [onCerrar]);

  function abajo(e) {
    arrastre.current = { y0: e.clientY, t0: performance.now(), dy: 0 };
    e.currentTarget.setPointerCapture(e.pointerId);
    hoja.current.style.transition = "none";
  }
  function mover(e) {
    const a = arrastre.current;
    if (!a) return;
    a.dy = Math.max(e.clientY - a.y0, 0);
    hoja.current.style.transform = `translateY(${a.dy}px)`;
  }
  function soltar() {
    const a = arrastre.current;
    arrastre.current = null;
    if (!a) return;
    const v = a.dy / Math.max(performance.now() - a.t0, 1);
    if (a.dy > 110 || v > 0.7) {
      hoja.current.style.transition = "transform .25s ease-in";
      hoja.current.style.transform = "translateY(100%)";
      setTimeout(onCerrar, 220);
    } else {
      hoja.current.style.transition = "transform .45s var(--resorte)";
      hoja.current.style.transform = "";
    }
  }

  return (
    <>
      <div className="inf-hoja-velo" onClick={onCerrar} aria-hidden="true"></div>
      <div className="inf-hoja" ref={hoja} role="dialog" aria-label={titulo}>
        <div className="inf-hoja-asa" onPointerDown={abajo} onPointerMove={mover} onPointerUp={soltar} onPointerCancel={soltar}>
          <span></span>
        </div>
        <div className="inf-hoja-cabeza">
          <div>
            <h3>{titulo}</h3>
            {sub && <div className="sub">{sub}</div>}
          </div>
          <button type="button" className="inf-hoja-cerrar" onClick={onCerrar} aria-label="Cerrar">
            <i className="fa-solid fa-xmark"></i>
          </button>
        </div>
        <div>
          {columnas.map((c) => (
            <div className="detail-row" key={c.clave}>
              <span>{c.titulo}</span>
              <span style={c.clave === "stock_actual" && fila.bajo_minimo ? { color: "var(--red-alerta)" } : undefined}>
                {formatear(fila[c.clave], c.tipo)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
