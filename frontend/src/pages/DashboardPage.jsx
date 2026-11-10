import { useEffect, useId, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { getResumenDashboard } from "../api/dashboard";
import { useAuth } from "../context/AuthContext";
import { Bloque } from "../components/Esqueleto";

// Ícono de cada tipo de alerta. La clave la define el backend (TiposAlerta);
// el dibujo es cosa de la pantalla, por eso el mapa vive acá.
const ICONO_ALERTA = {
  postura_baja: "fa-arrow-trend-down",
  mortandad_alta: "fa-kiwi-bird",
  transicion_por_vencer: "fa-clock",
  sin_recoleccion: "fa-calendar-xmark",
};

// Tonos que se van turnando en las tarjetas de stock. En la granja son tres
// productos (huevo Nº1, Nº2 y Nº3), pero si mañana hay más, el cuarto vuelve
// a empezar la vuelta.
const TONOS = [
  { clase: "stock-tono-a", color: "var(--green-600)" },
  { clase: "stock-tono-b", color: "var(--gold-500)" },
  { clase: "stock-tono-c", color: "var(--gray-500)" },
  { clase: "stock-tono-d", color: "var(--green-800)" },
];

const entero = (valor) => Number(valor ?? 0).toLocaleString("es-AR");

const decimal = (valor, decimales = 1) =>
  valor === null || valor === undefined
    ? "—"
    : Number(valor).toLocaleString("es-AR", {
        minimumFractionDigits: decimales,
        maximumFractionDigits: decimales,
      });

const porcentaje = (valor) =>
  valor === null || valor === undefined ? "—" : `${decimal(valor)}%`;

/** "2026-08-09" → Date del mediodía local (evita correrse de día por la zona horaria). */
function fechaDe(iso) {
  const [anio, mes, dia] = iso.split("-").map(Number);
  return new Date(anio, mes - 1, dia, 12);
}

function conMayuscula(texto) {
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

/** "Domingo, 9 de agosto de 2026" */
function fechaLarga(iso) {
  return conMayuscula(
    fechaDe(iso).toLocaleDateString("es-AR", {
      weekday: "long",
      day: "numeric",
      month: "long",
      year: "numeric",
    })
  );
}

/** "Lun", "Mar"... para el pie de cada barra. */
function diaCorto(iso) {
  const texto = fechaDe(iso).toLocaleDateString("es-AR", { weekday: "short" });
  return conMayuscula(texto.replace(".", ""));
}

/** Variación de los huevos frente a ayer, como etiqueta de la tarjeta. */
function deltaHuevos(variacion) {
  if (variacion === null || variacion === undefined) return null;
  if (Math.abs(variacion) < 0.1) return { clase: "delta-neutral", texto: "Igual que ayer" };
  const signo = variacion > 0 ? "+" : "−";
  return {
    clase: variacion > 0 ? "delta-up" : "delta-down",
    texto: `${signo}${decimal(Math.abs(variacion))}%`,
  };
}

/**
 * Variación de la postura. Se mide en puntos y no en porcentaje: pasar de 70%
 * a 72% son 2 puntos, no un 2,8% más.
 */
function deltaPostura(variacion) {
  if (variacion === null || variacion === undefined) return null;
  if (Math.abs(variacion) < 0.5) return { clase: "delta-neutral", texto: "Estable" };
  const signo = variacion > 0 ? "+" : "−";
  return {
    clase: variacion > 0 ? "delta-up" : "delta-down",
    texto: `${signo}${decimal(Math.abs(variacion))} pts`,
  };
}

/**
 * Postura del día como anillo: el porcentaje llena el círculo (100 % = vuelta
 * completa) y debajo van la variación frente a ayer y el promedio semanal.
 */
function AnilloPostura({ valor, ayer, delta, promedio }) {
  const hay = valor !== null && valor !== undefined;
  const radio = 56;
  const vuelta = 2 * Math.PI * radio;
  const lleno = hay ? Math.min(Math.max(Number(valor), 0), 100) / 100 : 0;
  return (
    <div className="anillo">
      <div className="anillo-fila">
        <div className="anillo-dibujo">
          <svg viewBox="0 0 140 140" role="img" aria-label={hay ? `Postura de hoy: ${porcentaje(valor)}` : "Sin datos de postura hoy"}>
            <circle className="anillo-pista" cx="70" cy="70" r={radio} fill="none" strokeWidth="14" />
            {hay && (
              <circle
                className="anillo-valor"
                cx="70"
                cy="70"
                r={radio}
                fill="none"
                strokeWidth="14"
                strokeLinecap="round"
                strokeDasharray={`${(vuelta * lleno).toFixed(1)} ${vuelta.toFixed(1)}`}
                transform="rotate(-90 70 70)"
              />
            )}
          </svg>
          <div className="anillo-centro">
            {hay ? (
              <span className="anillo-cifra">{decimal(valor)}<small>%</small></span>
            ) : (
              <span className="anillo-cifra anillo-vacio">—</span>
            )}
          </div>
        </div>
        <div className="anillo-pie">
          {hay ? (
            <>
              {delta && <span className={`kpi-delta ${delta.clase}`}>{delta.texto}</span>}
              <span>{ayer !== null && ayer !== undefined ? `Ayer: ${porcentaje(ayer)}` : "Sin datos de ayer"}</span>
            </>
          ) : (
            <span>Sin datos hoy</span>
          )}
          {promedio !== null && <span className="anillo-prom">Semana: {porcentaje(promedio)}</span>}
        </div>
      </div>
    </div>
  );
}

const SITUACION = {
  P: { texto: "En producción", clase: "mapa-prod" },
  T: { texto: "En transición", clase: "mapa-trans" },
  S: { texto: "Activo sin lote", clase: "mapa-sinlote" },
  I: { texto: "Inactivo", clase: "mapa-inactivo" },
};

/**
 * Mapa de galpones: una casilla por galpón, pintada según su situación y con
 * un punto rojo si tiene alertas. Tocar una casilla muestra al lado su lote,
 * sus gallinas y su postura; desde ahí se abre el galpón.
 */
function MapaGalpones({ galpones, datos, hoy }) {
  const [elegido, setElegido] = useState(null);
  if (!galpones?.length) return null;
  const actual =
    galpones.find((g) => g.id_galpon === elegido) ||
    galpones.find((g) => g.alerta) ||
    galpones[0];
  const etiquetaDato = (g) => {
    if (g.estado === "T") return "Trans.";
    if (g.estado === "S") return "Sin lote";
    if (g.estado === "I") return "Inactivo";
    return porcentaje(g.postura);
  };
  const numero = (nombre) => nombre.replace(/^galp[oó]n\s*/i, "");
  const situacion = SITUACION[actual.estado];
  const posturaDia =
    actual.postura_fecha && actual.postura_fecha !== hoy ? ` · ${diaCorto(actual.postura_fecha)}` : "";
  return (
    <div className="card mapa">
      <div className="mapa-cabecera">
        <div className="mapa-titulo">
          <h3>Galpones</h3>
          <span className="card-sub">
            {datos.galpones_en_produccion} de {datos.galpones_activos} en producción
            {datos.gallinas_en_produccion > 0 && ` · ${entero(datos.gallinas_en_produccion)} gallinas`}
          </span>
        </div>
        <div className="mapa-leyenda" aria-hidden="true">
          <span><i className="mapa-prod"></i>Producción</span>
          <span><i className="mapa-trans"></i>Transición</span>
          <span><i className="mapa-sinlote"></i>Sin lote</span>
          <span><i className="mapa-inactivo"></i>Inactivo</span>
          <span><i className="mapa-punto"></i>Alerta</span>
        </div>
      </div>
      <div className="mapa-fila">
        <div className="mapa-tiles">
          {galpones.map((g) => (
            <button
              key={g.id_galpon}
              type="button"
              className={`mapa-tile ${SITUACION[g.estado].clase}${g.id_galpon === actual.id_galpon ? " elegido" : ""}`}
              aria-pressed={g.id_galpon === actual.id_galpon}
              aria-label={`${g.galpon}, ${SITUACION[g.estado].texto.toLowerCase()}${g.alerta ? ", con alerta" : ""}`}
              onClick={() => setElegido(g.id_galpon)}
            >
              <b>G{numero(g.galpon)}</b>
              <span>{etiquetaDato(g)}</span>
              {g.alerta && <i className="mapa-punto" aria-hidden="true"></i>}
            </button>
          ))}
        </div>
        <div className="mapa-detalle" aria-live="polite">
          <div className="mapa-detalle-top">
            {actual.alerta && <i className="mapa-punto" aria-hidden="true"></i>}
            <b>{actual.galpon}</b>
            <span className={`mapa-chip ${situacion.clase}`}>{situacion.texto}</span>
            {actual.alerta && <span className="sr-only">, con alerta</span>}
            <Link className="link" to="/app/galpones" state={{ id_galpon: actual.id_galpon }}>
              Abrir →
            </Link>
          </div>
          <div className="mapa-detalle-datos">
            <span>Lote<b>{actual.lote ?? "—"}</b></span>
            <span>Gallinas<b>{actual.gallinas === null ? "—" : entero(actual.gallinas)}</b></span>
            <span>Postura<b>{actual.postura === null ? "—" : `${porcentaje(actual.postura)}${posturaDia}`}</b></span>
          </div>
        </div>
      </div>
    </div>
  );
}

const ANCHO_GRAFICO = 640;
/** Alto del gráfico (en unidades del dibujo): más bajo en escritorio, donde el ancho lo hace más largo que alto. */
const ALTO_ANCHO = 150;
const ALTO_ANGOSTO = 200;

/** true mientras la pantalla mide hasta `px` de ancho. */
function useAnchoMaximo(px) {
  const consulta = `(max-width:${px}px)`;
  const [coincide, setCoincide] = useState(() => window.matchMedia(consulta).matches);
  useEffect(() => {
    const mq = window.matchMedia(consulta);
    const cambiar = () => setCoincide(mq.matches);
    mq.addEventListener("change", cambiar);
    return () => mq.removeEventListener("change", cambiar);
  }, [consulta]);
  return coincide;
}

/** Curva suave (Catmull-Rom pasada a Bézier) que pasa por todos los puntos. */
function curvaSuave(puntos) {
  let d = `M${puntos[0][0].toFixed(1)} ${puntos[0][1].toFixed(1)}`;
  for (let i = 0; i < puntos.length - 1; i += 1) {
    const p0 = puntos[i - 1] || puntos[i];
    const p1 = puntos[i];
    const p2 = puntos[i + 1];
    const p3 = puntos[i + 2] || p2;
    const c1x = p1[0] + (p2[0] - p0[0]) / 6;
    const c1y = p1[1] + (p2[1] - p0[1]) / 6;
    const c2x = p2[0] - (p3[0] - p1[0]) / 6;
    const c2y = p2[1] - (p3[1] - p1[1]) / 6;
    d += ` C${c1x.toFixed(1)} ${c1y.toFixed(1)} ${c2x.toFixed(1)} ${c2y.toFixed(1)} ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`;
  }
  return d;
}

/**
 * Producción de los últimos siete días: el número de hoy, su variación frente
 * a ayer y la curva de la semana. Pasar el cursor (o el dedo) por el gráfico
 * muestra el valor de cada día; al soltar vuelve a «Hoy».
 */
function Produccion({ dias, hoy, huevosHoy, delta }) {
  const idGrad = useId();
  const [activo, setActivo] = useState(null);
  const ALTO_GRAFICO = useAnchoMaximo(700) ? ALTO_ANGOSTO : ALTO_ANCHO;
  const valores = dias.map((d) => d.huevos);
  const maximo = Math.max(...valores);
  if (maximo === 0) {
    return (
      <div className="empty-state">
        Todavía no hay recolecciones finalizadas en los últimos siete días.
      </div>
    );
  }
  const minimo = Math.min(...valores);
  const total = valores.reduce((a, v) => a + v, 0);
  const margen = Math.max(maximo - minimo, maximo * 0.02);
  const piso = minimo - margen * 0.25;
  const techo = maximo + margen * 0.12;
  const n = dias.length;
  const puntos = valores.map((v, i) => [
    (i / (n - 1)) * ANCHO_GRAFICO,
    26 + ((techo - v) / (techo - piso)) * (ALTO_GRAFICO - 26 - 12),
  ]);
  const linea = curvaSuave(puntos);
  const area = `${linea} L${puntos[n - 1][0].toFixed(1)} ${ALTO_GRAFICO} L${puntos[0][0].toFixed(1)} ${ALTO_GRAFICO} Z`;
  const encontrado = dias.findIndex((d) => d.fecha === hoy);
  const indiceHoy = encontrado === -1 ? n - 1 : encontrado;
  const i = activo ?? indiceHoy;
  const [px, py] = puntos[i];
  const nombre = (k) => (dias[k].fecha === hoy ? "Hoy" : diaCorto(dias[k].fecha));
  const mejor = valores.indexOf(maximo);

  const mover = (e) => {
    const caja = e.currentTarget.getBoundingClientRect();
    const k = Math.round(((e.clientX - caja.left) / caja.width) * (n - 1));
    setActivo(Math.min(Math.max(k, 0), n - 1));
  };

  return (
    <div className="prod">
      <div className="prod-cifra">
        <span className="prod-numero">{entero(huevosHoy)}</span>
        {delta && <span className={`delta ${delta.clase}`}>{delta.texto}</span>}
      </div>

      <div
        className="prod-grafico"
        onPointerMove={mover}
        onPointerLeave={() => setActivo(null)}
        onPointerCancel={() => setActivo(null)}
      >
        <svg
          viewBox={`0 0 ${ANCHO_GRAFICO} ${ALTO_GRAFICO}`}
          role="img"
          aria-label={`Huevos recolectados por día en la última semana. Hoy: ${entero(huevosHoy)}.`}
        >
          <defs>
            <linearGradient id={idGrad} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--serie-real)" stopOpacity="0.28" />
              <stop offset="100%" stopColor="var(--serie-real)" stopOpacity="0" />
            </linearGradient>
          </defs>
          {[0.25, 0.5, 0.75].map((f) => (
            <line key={f} x1="0" x2={ANCHO_GRAFICO} y1={ALTO_GRAFICO * f} y2={ALTO_GRAFICO * f} stroke="var(--linea-grafico)" />
          ))}
          <path d={area} fill={`url(#${idGrad})`} />
          <path d={linea} className="prod-linea" fill="none" />
          <line className="prod-guia" x1={px} x2={px} y1={py} y2={ALTO_GRAFICO} />
          <circle cx={px} cy={py} r="9" className="prod-halo" />
          <circle cx={px} cy={py} r="5" className="prod-punto" />
        </svg>
        <span
          className="prod-tip"
          style={{ left: `${Math.min(Math.max(px / ANCHO_GRAFICO, 0.13), 0.87) * 100}%`, top: `${(py / ALTO_GRAFICO) * 100}%` }}
        >
          {nombre(i)} · {entero(valores[i])}
        </span>
      </div>

      <div className="prod-dias">
        {dias.map((d, k) => (
          <span
            key={d.fecha}
            className={k === i ? "activo" : ""}
            style={{ left: `${(k / (n - 1)) * 100}%`, transform: `translateX(-${(k / (n - 1)) * 100}%)` }}
          >
            {nombre(k)}
          </span>
        ))}
      </div>

      <div className="prod-datos">
        <div><span>Promedio diario</span><b>{entero(Math.round(total / n))}</b></div>
        <div><span>Mejor día ({nombre(mejor)})</span><b>{entero(maximo)}</b></div>
        <div><span>Total de la semana</span><b>{entero(total)}</b></div>
      </div>
    </div>
  );
}

/**
 * Etiqueta de la tarjeta de stock: el tamaño del huevo si la descripción es
 * corta («Grande», «Mediano») y, si el producto está dado de baja, eso.
 */
function Etiqueta({ item, tono }) {
  if (item.estado === "I") {
    return <span className="stock-size-tag stock-tono-c">Inactivo</span>;
  }
  const texto = (item.descripcion || "").trim();
  if (!texto || texto.length > 16) return null;
  return <span className={`stock-size-tag ${tono}`}>{texto}</span>;
}

/** Quita el «Lote X · Galpón Y — » del comienzo: ya va como título de la fila. */
function sinEncabezado(descripcion) {
  const corte = descripcion.indexOf(" — ");
  return corte === -1 ? descripcion : descripcion.slice(corte + 3);
}

/** Agrupa las alertas por tipo conservando el orden en que llegan. */
function agruparPorTipo(alertas) {
  const grupos = new Map();
  alertas.forEach((alerta) => {
    if (!grupos.has(alerta.clave)) grupos.set(alerta.clave, { tipo: alerta.tipo, items: [] });
    grupos.get(alerta.clave).items.push(alerta);
  });
  return [...grupos.entries()].map(([clave, grupo]) => ({ clave, ...grupo }));
}

/** Una alerta: al pasar el cursor se despliega la descripción; al hacer clic abre Lotes buscando el lote afectado. */
function Alerta({ alerta, clave, extra }) {
  const resuelta = alerta.estado === "R";
  const severidad = resuelta ? "sev-green" : alerta.severidad === "A" ? "sev-red" : "sev-gold";
  const icono = resuelta ? "fa-check" : ICONO_ALERTA[clave] || "fa-triangle-exclamation";
  const etiqueta = resuelta ? "Resuelta" : alerta.severidad === "A" ? "Alta" : "Media";
  return (
    <Link
      className={`alert-item alert-link ${severidad}${extra ? " alerta-extra" : ""}`}
      to="/app/lotes"
      state={{ filtros: { search: alerta.lote, fechaDesde: "", fechaHasta: "" } }}
    >
      <div className="alert-icon">
        <i className={`fa-solid ${icono}`}></i>
      </div>
      <div className="alert-text">
        <div className="alert-top">
          <b>
            Lote {alerta.lote} · {alerta.galpon}
          </b>
          <span className={`status-tag ${resuelta ? "tag-resuelta" : "tag-pendiente"}`}>{etiqueta}</span>
        </div>
        <div className="alert-sub">
          <div>{sinEncabezado(alerta.descripcion)}</div>
        </div>
      </div>
    </Link>
  );
}

// Módulos con registros que pueden quedar sin finalizar.
const MODULOS_PENDIENTES = [
  { clave: "recolecciones", texto: "Recolecciones", ruta: "/app/recoleccion", icono: "fa-egg" },
  { clave: "entradas", texto: "Entradas", ruta: "/app/entradas", icono: "fa-dolly" },
  { clave: "salidas", texto: "Salidas", ruta: "/app/salidas", icono: "fa-truck-ramp-box" },
  { clave: "compras", texto: "Compras", ruta: "/app/compras", icono: "fa-cart-shopping" },
  { clave: "descartes", texto: "Descartes", ruta: "/app/descartes", icono: "fa-trash-can" },
];

/**
 * Lo que se ve mientras llegan los datos: el panel con su misma estructura, en
 * gris y con un brillo que lo recorre. Mantener acá la misma disposición que
 * la pantalla real evita que el contenido «salte» al aparecer.
 */
function EsqueletoPanel({ conAcciones, conCompras }) {
  const alturas = [88, 52, 64, 70, 58, 66, 40];
  const modulos = conCompras ? 5 : 4;
  return (
    <div className="page active" id="page-dashboard" role="status" aria-busy="true">
      <span className="sr-only">Cargando el panel...</span>

      <div className="page-header">
        <div>
          <Bloque ancho={230} alto={28} />
          <Bloque ancho={340} alto={14} style={{ marginTop: 10 }} />
        </div>
        {conAcciones && (
          <div className="page-header-actions">
            <Bloque ancho={150} alto={38} radio={9} />
            <Bloque ancho={150} alto={38} radio={9} />
          </div>
        )}
      </div>

      <div className="grid-2">
        <div className="card">
          <Bloque ancho={220} alto={18} />
          <Bloque ancho={180} alto={12} style={{ marginTop: 8 }} />
          <div className="esqueleto-barras">
            {alturas.map((alto, i) => (
              <div className="esqueleto-barra-col" key={i}>
                <Bloque ancho="100%" alto={`${alto}%`} radio="6px 6px 0 0" />
                <Bloque ancho={28} alto={10} />
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <Bloque ancho={160} alto={18} />
          {[0, 1, 2].map((i) => (
            <div className="esqueleto-fila" key={i}>
              <Bloque ancho={34} alto={34} radio="50%" style={{ flexShrink: 0 }} />
              <div style={{ flex: 1 }}>
                <Bloque ancho="60%" alto={14} />
                <Bloque ancho="90%" alto={12} style={{ marginTop: 8 }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="fila-postura">
        <div className="card">
          <Bloque ancho={180} alto={18} />
          <Bloque ancho={150} alto={150} radio="50%" style={{ margin: "18px auto 0" }} />
        </div>
        <div className="card">
          <Bloque ancho={140} alto={18} />
          <Bloque alto={62} radio={16} style={{ marginTop: 16 }} />
          <Bloque alto={70} radio={16} style={{ marginTop: 14 }} />
        </div>
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <Bloque ancho={200} alto={18} />
        <Bloque ancho={280} alto={12} style={{ marginTop: 8 }} />
        <div className="pendientes-grid" style={{ marginTop: 16 }}>
          {Array.from({ length: modulos }, (_, i) => (
            <Bloque key={i} alto={76} radio={12} />
          ))}
        </div>
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <Bloque ancho={220} alto={18} />
        <div className="stock-grid" style={{ marginTop: 16 }}>
          {[0, 1, 2].map((i) => (
            <Bloque key={i} alto={150} radio={12} />
          ))}
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const { esAdministrador, esOperario, esConsulta } = useAuth();

  const alertasRef = useRef(null);
  const [datos, setDatos] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [verTodasAlertas, setVerTodasAlertas] = useState(false); // en el celular se muestran solo las primeras

  useEffect(() => {
    let vigente = true;
    async function cargar() {
      try {
        const resumen = await getResumenDashboard();
        if (vigente) setDatos(resumen);
      } catch (err) {
        if (vigente) setError(err.message || "No se pudo cargar el panel.");
      } finally {
        if (vigente) setLoading(false);
      }
    }
    cargar();
    // Si el usuario sale de la pantalla antes de que llegue la respuesta, no
    // se intenta actualizar algo que ya no está.
    return () => {
      vigente = false;
    };
  }, []);

  /** Los accesos directos abren la sección con el formulario de alta ya puesto. */
  function irACargar(ruta) {
    navigate(ruta, { state: { alta: true } });
  }

  const puedeCargarProduccion = esAdministrador || esOperario;
  const puedeVerInformes = esAdministrador || esConsulta;
  // Productos e Informes no están disponibles para el Operario (ver config/menu.js).
  const puedeVerProductos = esAdministrador || esConsulta;

  if (loading) {
    return <EsqueletoPanel conAcciones={puedeCargarProduccion} conCompras={!esOperario} />;
  }

  if (error) {
    return (
      <div className="page active" id="page-dashboard">
        <div className="banner banner-error">{error}</div>
      </div>
    );
  }

  const stock = datos.stock_productos;
  const hoy = datos.fecha;
  // Postura de los últimos 7 días (sin los días sin recolección) para la tendencia y el promedio.
  const seriePostura = (datos.postura_serie ?? []).map((d) => d.valor).filter((v) => v !== null && v !== undefined);
  const promedioPostura = seriePostura.length
    ? seriePostura.reduce((suma, v) => suma + v, 0) / seriePostura.length
    : null;
  const pendientes = datos.pendientes || {};
  const modulosPendientes = MODULOS_PENDIENTES.filter((m) => m.clave in pendientes);
  const grupos = agruparPorTipo(datos.alertas);
  const alertasMostradas = datos.alertas.filter((a) => a.estado === "P").length;
  const alertasOcultas = datos.alertas_pendientes - alertasMostradas;

  return (
    <div className="page active" id="page-dashboard">
      <div className="page-header">
        <div data-tutorial="dash-titulo">
          <h1>Panel principal</h1>
          <div className="desc">
            {fechaLarga(hoy)} ·{" "}
            {esOperario
              ? "Resumen de los galpones que tenés asignados"
              : "Resumen general de la granja"}
          </div>
        </div>
        {puedeCargarProduccion && (
          <div className="page-header-actions" data-tutorial="dash-acciones">
            <button type="button" className="btn btn-green" onClick={() => irACargar("/app/recoleccion")}>
              <i className="fa-solid fa-egg"></i><span className="btn-txt">Nueva recolección</span>
            </button>
            <button type="button" className="btn btn-outline" onClick={() => irACargar("/app/descartes")}>
              <i className="fa-solid fa-trash-can"></i><span className="btn-txt">Registrar descarte</span>
            </button>
            {esAdministrador && (
              <button type="button" className="btn btn-outline" onClick={() => irACargar("/app/compras")}>
                <i className="fa-solid fa-cart-plus"></i><span className="btn-txt">Nueva compra</span>
              </button>
            )}
          </div>
        )}
      </div>

      <div className="grid-2">
        <div className="card card-produccion" data-tutorial="dash-produccion">
          <div className="card-title">
            <div>
              <h3>Producción de los últimos 7 días</h3>
              <div className="card-sub">Huevos de recolecciones finalizadas</div>
            </div>
            {puedeVerInformes && (
              <Link className="link" to="/app/informes">
                Ver informe completo
              </Link>
            )}
          </div>

          <Produccion dias={datos.produccion} hoy={hoy} huevosHoy={datos.huevos_hoy} delta={deltaHuevos(datos.variacion_huevos)} />
        </div>

        <div className={`card card-alertas${verTodasAlertas ? " alertas-todas" : ""}`} ref={alertasRef} data-tutorial="dash-alertas">
          <div className="card-title">
            <h3>Alertas recientes</h3>
            {datos.alertas_pendientes > 0 && (
              <span className="card-nota">
                {datos.alertas_pendientes} {datos.alertas_pendientes === 1 ? "activa" : "activas"}
              </span>
            )}
          </div>
          <div className="alertas-scroll">
            {grupos.length === 0 ? (
              <div className="empty-state">
                No hay alertas. Los lotes vienen trabajando dentro de lo esperado.
              </div>
            ) : (
              (() => {
                let n = 0; // cuántas alertas ya se dibujaron: en el celular solo se ven las primeras 3
                return grupos.map((grupo) => {
                  const inicio = n;
                  n += grupo.items.length;
                  return (
                    <div className={`alert-grupo${inicio >= 3 ? " alerta-extra" : ""}`} key={grupo.clave}>
                      <div className="alert-grupo-titulo">
                        {grupo.tipo} <span>{grupo.items.length}</span>
                      </div>
                      {grupo.items.map((alerta, i) => (
                        <Alerta key={alerta.id_alerta} alerta={alerta} clave={grupo.clave} extra={inicio + i >= 3} />
                      ))}
                    </div>
                  );
                });
              })()
            )}
            {grupos.reduce((t, g) => t + g.items.length, 0) > 3 && (
              <button type="button" className="alertas-ver-todas" onClick={() => setVerTodasAlertas((v) => !v)}>
                {verTodasAlertas ? "Ver menos" : `Ver todas (${grupos.reduce((t, g) => t + g.items.length, 0)})`}
              </button>
            )}
            {alertasOcultas > 0 && (
              <div className="alert-resto">
                Hay {alertasOcultas} {alertasOcultas === 1 ? "alerta activa más" : "alertas activas más"} que
                no se muestran acá.
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="fila-postura" data-tutorial="dash-galpones">
        <div className="card card-anillo">
          <div className="card-title">
            <h3>Postura promedio de hoy</h3>
          </div>
          <AnilloPostura
            valor={datos.postura_hoy}
            ayer={datos.postura_ayer}
            delta={deltaPostura(datos.variacion_postura)}
            promedio={promedioPostura}
          />
        </div>

        <MapaGalpones galpones={datos.mapa_galpones} datos={datos} hoy={hoy} />
      </div>

      <div className="par-tarjetas">
      <div className="card" style={{ marginTop: 18 }} data-tutorial="dash-pendientes">
        <div className="card-title">
          <div>
            <h3>Pendientes de finalizar</h3>
            <div className="card-sub">Registros cargados que todavía no impactan en el stock</div>
          </div>
          {datos.pendientes_total > 0 && (
            <span className="card-nota">{entero(datos.pendientes_total)} en total</span>
          )}
        </div>
        {datos.pendientes_total === 0 ? (
          <div className="empty-state">No hay registros pendientes. Todo está finalizado.</div>
        ) : (
          <div className="pendientes-grid">
            {modulosPendientes.map((modulo) => (
              <Link
                key={modulo.clave}
                className={`pendiente-item${pendientes[modulo.clave] ? "" : " pendiente-cero"}`}
                to={modulo.ruta}
                state={{ filtros: { estado: "P" } }}
                title={`Ver ${modulo.texto.toLowerCase()} pendientes`}
              >
                <i className={`fa-solid ${modulo.icono}`}></i>
                <b>{entero(pendientes[modulo.clave])}</b>
                <span>{modulo.texto}</span>
              </Link>
            ))}
          </div>
        )}
      </div>

      <div className="card" style={{ marginTop: 18 }} data-tutorial="dash-stock">
        <div className="card-title">
          <h3>Stock actual de productos</h3>
          {stock.items.length > 0 && (
            <span className="card-nota">{entero(stock.total)} huevos en total</span>
          )}
        </div>
        {stock.items.length === 0 ? (
          <div className="empty-state">Todavía no hay productos con stock para mostrar.</div>
        ) : (
          <>
          <div className="stock-reparto" aria-hidden="true">
            {stock.items.map((item, indice) => (
              <span
                key={item.id_producto}
                style={{ flexGrow: Math.max(item.stock, 0), background: TONOS[indice % TONOS.length].color }}
                title={`${item.producto}: ${decimal(item.porcentaje, 0)}%`}
              ></span>
            ))}
          </div>
          <div className="stock-grid">
            {stock.items.map((item, indice) => {
              const tono = TONOS[indice % TONOS.length];
              const cuerpo = (
                <>
                  <div className={`stock-icon stock-icon-dato ${tono.clase}`}>
                    <i className="fa-solid fa-egg"></i>
                  </div>
                  <div className="stock-value">{entero(item.stock)}</div>
                  <div className="stock-label">{item.producto}</div>
                  <Etiqueta item={item} tono={tono.clase} />
                  <div className="stock-bar" title={`${decimal(item.porcentaje, 0)}% del total`}>
                    <div
                      className="stock-bar-fill"
                      style={{ width: `${Math.min(Math.max(item.porcentaje, 0), 100)}%`, background: tono.color }}
                    ></div>
                  </div>
                  <div className="stock-pct">{decimal(item.porcentaje, 0)}% del total</div>
                </>
              );
              return puedeVerProductos ? (
                <Link className="stock-item stock-link" key={item.id_producto} to="/app/productos">
                  {cuerpo}
                </Link>
              ) : (
                <div className="stock-item" key={item.id_producto}>
                  {cuerpo}
                </div>
              );
            })}
          </div>
          </>
        )}
      </div>
      </div>
    </div>
  );
}
