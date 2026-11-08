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

/** Línea mínima de tendencia (sin ejes) para las tarjetas de indicadores. */
function Sparkline({ serie }) {
  const id = `sp-${useId().replace(/:/g, "")}`;
  if (!serie || serie.length < 2) return null;
  const w = 100, h = 28, pad = 3;
  const max = Math.max(...serie), min = Math.min(...serie);
  const rango = max - min || 1;
  const pts = serie.map((v, i) => [
    (i / (serie.length - 1)) * w,
    pad + (1 - (v - min) / rango) * (h - pad * 2),
  ]);
  const linea = pts.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(" ");
  const ultimo = pts[pts.length - 1];
  return (
    <svg className="kpi-spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="currentColor" stopOpacity=".22" />
          <stop offset="1" stopColor="currentColor" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${linea} L${w} ${h} L0 ${h} Z`} fill={`url(#${id})`} />
      <path d={linea} fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
      <circle cx={ultimo[0]} cy={ultimo[1]} r="0" />
    </svg>
  );
}

/**
 * Tarjeta de indicador. Si recibe `to` navega a la sección con el detalle (y
 * `state` con los filtros a aplicar); si recibe `onClick` hace esa acción; y
 * sin ninguna de las dos es solo informativa.
 */
function Kpi({ icono, fondo, color, valor, etiqueta, delta, sub, to, state, onClick, ayuda, serie }) {
  const contenido = (
    <>
      <div className="kpi-top">
        <div className="kpi-icon" style={{ background: fondo, color }}>
          <i className={`fa-solid ${icono}`}></i>
        </div>
        {delta && <span className={`kpi-delta ${delta.clase}`}>{delta.texto}</span>}
      </div>
      <div className="value">{valor}</div>
      <div className="label">{etiqueta}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
      {serie && <Sparkline serie={serie} />}
      {(to || onClick) && <i className="fa-solid fa-chevron-right kpi-flecha"></i>}
    </>
  );
  if (to) {
    return (
      <Link className="kpi-card kpi-link" to={to} state={state} title={ayuda}>
        {contenido}
      </Link>
    );
  }
  if (onClick) {
    return (
      <button type="button" className="kpi-card kpi-link" onClick={onClick} title={ayuda}>
        {contenido}
      </button>
    );
  }
  return <div className="kpi-card">{contenido}</div>;
}

/** Gráfico de barras de la última semana (altura relativa al mejor día). */
function Produccion({ dias, hoy, enlazar }) {
  const maximo = Math.max(...dias.map((d) => d.huevos));
  if (maximo === 0) {
    return (
      <div className="empty-state">
        Todavía no hay recolecciones finalizadas en los últimos siete días.
      </div>
    );
  }
  const promedio = dias.reduce((a, d) => a + d.huevos, 0) / dias.length;
  return (
    <div className="bars" style={{ "--prom": `${(promedio / maximo) * 100}%` }}>
      {dias.map((dia) => {
        const esHoy = dia.fecha === hoy;
        const columna = (
          <>
            <b>{entero(dia.huevos)}</b>
            <div className="bar-zona">
              <i className="bar-prom" aria-hidden="true"></i>
              <div
                className={`bar${esHoy ? " bar-hoy" : ""}`}
                style={{ height: `${Math.max((dia.huevos / maximo) * 100, 2)}%` }}
                title={`${entero(dia.huevos)} huevos`}
              ></div>
            </div>
            <span>{esHoy ? "Hoy" : diaCorto(dia.fecha)}</span>
          </>
        );
        return enlazar ? (
          <Link className="bar-col bar-col-link" key={dia.fecha} to="/app/informes">
            {columna}
          </Link>
        ) : (
          <div className="bar-col" key={dia.fecha}>
            {columna}
          </div>
        );
      })}
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

      <div className="kpi-grid">
        {[0, 1, 2, 3].map((i) => (
          <div className="kpi-card" key={i}>
            <div className="kpi-top">
              <Bloque ancho={34} alto={34} radio={9} />
              <Bloque ancho={64} alto={18} radio={20} />
            </div>
            <Bloque ancho={90} alto={28} style={{ marginTop: 6 }} />
            <Bloque ancho="70%" alto={14} style={{ marginTop: 10 }} />
            <Bloque ancho="40%" alto={12} style={{ marginTop: 10 }} />
          </div>
        ))}
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
              <i className="fa-solid fa-egg"></i> Nueva recolección
            </button>
            <button type="button" className="btn btn-outline" onClick={() => irACargar("/app/descartes")}>
              <i className="fa-solid fa-trash-can"></i> Registrar descarte
            </button>
            {esAdministrador && (
              <button type="button" className="btn btn-outline" onClick={() => irACargar("/app/compras")}>
                <i className="fa-solid fa-cart-plus"></i> Nueva compra
              </button>
            )}
          </div>
        )}
      </div>

      <div className="kpi-grid" data-tutorial="dash-kpis">
        <Kpi
          icono="fa-egg"
          fondo="var(--green-100)"
          color="var(--green-700)"
          valor={entero(datos.huevos_hoy)}
          etiqueta="Huevos recolectados hoy"
          delta={deltaHuevos(datos.variacion_huevos)}
          sub={`Ayer: ${entero(datos.huevos_ayer)}`}
          serie={datos.produccion?.map((d) => d.huevos)}
          to="/app/recoleccion"
          state={{ filtros: { estado: "F", fechaDesde: hoy, fechaHasta: hoy } }}
          ayuda="Ver las recolecciones de hoy"
        />
        <Kpi
          icono="fa-chart-line"
          fondo="var(--gold-100)"
          color="var(--gold-texto)"
          valor={porcentaje(datos.postura_hoy)}
          etiqueta="Postura promedio de hoy"
          delta={deltaPostura(datos.variacion_postura)}
          sub={
            datos.postura_hoy === null || datos.postura_hoy === undefined
              ? "Sin datos hoy"
              : `Ayer: ${porcentaje(datos.postura_ayer)}`
          }
          to={puedeVerInformes ? "/app/informes" : undefined}
          ayuda={puedeVerInformes ? "Ver los informes de postura" : undefined}
        />
        <Kpi
          icono="fa-warehouse"
          fondo="var(--green-100)"
          color="var(--green-700)"
          valor={entero(datos.galpones_en_produccion)}
          etiqueta="Galpones en producción"
          delta={{
            clase: "delta-neutral",
            texto: `${datos.galpones_en_produccion} de ${datos.galpones_activos}`,
          }}
          to="/app/galpones"
          ayuda="Ver los galpones"
        />
        <Kpi
          icono="fa-triangle-exclamation"
          fondo={datos.alertas_pendientes ? "var(--red-100)" : "var(--gray-200)"}
          color={datos.alertas_pendientes ? "var(--red-500)" : "var(--gray-700)"}
          valor={entero(datos.alertas_pendientes)}
          etiqueta="Alertas activas"
          delta={
            datos.alertas_pendientes
              ? { clase: "delta-down", texto: "Requieren atención" }
              : { clase: "delta-up", texto: "Todo en orden" }
          }
          onClick={() => alertasRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })}
          ayuda="Ir a las alertas"
        />
      </div>

      <div className="grid-2">
        <div className="card card-produccion" data-tutorial="dash-produccion">
          <div className="card-title">
            <div>
              <h3>Producción — últimos 7 días</h3>
              <div className="card-sub">Huevos de recolecciones finalizadas</div>
            </div>
            {puedeVerInformes && (
              <Link className="link" to="/app/informes">
                Ver informe completo
              </Link>
            )}
          </div>

          <Produccion dias={datos.produccion} hoy={hoy} enlazar={puedeVerInformes} />
        </div>

        <div className={`card${verTodasAlertas ? " alertas-todas" : ""}`} ref={alertasRef} data-tutorial="dash-alertas">
          <div className="card-title">
            <h3>Alertas recientes</h3>
            {datos.alertas_pendientes > 0 && (
              <span className="card-nota">
                {datos.alertas_pendientes} {datos.alertas_pendientes === 1 ? "activa" : "activas"}
              </span>
            )}
          </div>
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
