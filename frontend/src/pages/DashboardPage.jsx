import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { getResumenDashboard } from "../api/dashboard";
import { useAuth } from "../context/AuthContext";

// Ícono de cada tipo de alerta. La clave la define el backend (TiposAlerta);
// el dibujo es cosa de la pantalla, por eso el mapa vive acá.
const ICONO_ALERTA = {
  postura_baja: "fa-arrow-trend-down",
  mortandad_alta: "fa-kiwi-bird",
  transicion_por_vencer: "fa-clock",
  sin_recoleccion: "fa-calendar-xmark",
};

// Tonos que se van turnando en las tarjetas de stock y en el anillo. En la
// granja son tres productos (huevo Nº1, Nº2 y Nº3), pero si mañana hay más,
// el cuarto vuelve a empezar la vuelta.
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

function Kpi({ icono, fondo, color, valor, etiqueta, delta }) {
  return (
    <div className="kpi-card">
      <div className="kpi-top">
        <div className="kpi-icon" style={{ background: fondo, color }}>
          <i className={`fa-solid ${icono}`}></i>
        </div>
        {delta && <span className={`kpi-delta ${delta.clase}`}>{delta.texto}</span>}
      </div>
      <div className="value">{valor}</div>
      <div className="label">{etiqueta}</div>
    </div>
  );
}

/** Gráfico de barras de la última semana (altura relativa al mejor día). */
function Produccion({ dias, hoy }) {
  const maximo = Math.max(...dias.map((d) => d.huevos));
  if (maximo === 0) {
    return (
      <div className="empty-state">
        Todavía no hay recolecciones finalizadas en los últimos siete días.
      </div>
    );
  }
  return (
    <div className="bars">
      {dias.map((dia) => {
        const esHoy = dia.fecha === hoy;
        return (
          <div className="bar-col" key={dia.fecha}>
            <b>{entero(dia.huevos)}</b>
            <div
              className={`bar${esHoy ? " bar-hoy" : ""}`}
              style={{ height: `${Math.max((dia.huevos / maximo) * 100, 2)}%` }}
              title={`${entero(dia.huevos)} huevos`}
            ></div>
            <span>{esHoy ? "Hoy" : diaCorto(dia.fecha)}</span>
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

function Alerta({ alerta }) {
  const resuelta = alerta.estado === "R";
  const severidad = resuelta ? "sev-green" : alerta.severidad === "A" ? "sev-red" : "sev-gold";
  const icono = resuelta ? "fa-check" : ICONO_ALERTA[alerta.clave] || "fa-triangle-exclamation";
  return (
    <div className={`alert-item ${severidad}`}>
      <div className="alert-icon">
        <i className={`fa-solid ${icono}`}></i>
      </div>
      <div className="alert-text">
        <div className="alert-top">
          <b>{alerta.tipo}</b>
          <span className={`status-tag ${resuelta ? "tag-resuelta" : "tag-pendiente"}`}>
            {alerta.estado_display}
          </span>
        </div>
        <div className="alert-sub">{alerta.descripcion}</div>
      </div>
    </div>
  );
}

/** Anillo con el reparto del stock entre los productos. */
function Anillo({ items, total }) {
  // Cada producto ocupa su porción; el color es el mismo que el de su tarjeta,
  // así que se toma del lugar que ocupa en la lista completa y no en la de
  // los que tienen stock. Lo que sobre por el redondeo lo cubre el último.
  const tramos = [];
  let grados = 0;
  items.forEach((item, indice) => {
    if (item.porcentaje <= 0) return;
    const desde = grados;
    grados += (item.porcentaje / 100) * 360;
    tramos.push(`${TONOS[indice % TONOS.length].color} ${desde}deg ${grados}deg`);
  });
  const fondo = tramos.length ? `conic-gradient(${tramos.join(", ")})` : null;

  return (
    <div className="donut-wrap">
      <div className="donut" style={{ background: fondo ?? "var(--gray-200)" }}>
        <div className="donut-center">
          <b>{entero(total)}</b>
          <span>Stock total</span>
        </div>
      </div>
      <div className="donut-legend">
        {items.map((item, indice) => (
          <div className="legend-item" key={item.id_producto}>
            <span
              className="legend-dot"
              style={{ background: TONOS[indice % TONOS.length].color }}
            ></span>
            {item.producto} <b>{decimal(item.porcentaje, 0)}%</b>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const { esAdministrador, esOperario, esConsulta } = useAuth();

  const [datos, setDatos] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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

  if (loading) {
    return (
      <div className="page active" id="page-dashboard">
        <div className="banner banner-loading">Cargando el panel...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page active" id="page-dashboard">
        <div className="banner banner-error">{error}</div>
      </div>
    );
  }

  const stock = datos.stock_productos;

  return (
    <div className="page active" id="page-dashboard">
      <div className="page-header">
        <div>
          <h1>Panel principal</h1>
          <div className="desc">
            {fechaLarga(datos.fecha)} ·{" "}
            {esOperario
              ? "Resumen de los galpones que tenés asignados"
              : "Resumen general de la granja"}
          </div>
        </div>
      </div>

      <div className="kpi-grid">
        <Kpi
          icono="fa-egg"
          fondo="var(--green-100)"
          color="var(--green-700)"
          valor={entero(datos.huevos_hoy)}
          etiqueta="Huevos recolectados hoy"
          delta={deltaHuevos(datos.variacion_huevos)}
        />
        <Kpi
          icono="fa-chart-line"
          fondo="var(--gold-100)"
          color="#96721e"
          valor={porcentaje(datos.postura_hoy)}
          etiqueta="Postura promedio de hoy"
          delta={deltaPostura(datos.variacion_postura)}
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
        />
      </div>

      <div className="grid-2">
        <div className="card">
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

          <Produccion dias={datos.produccion} hoy={datos.fecha} />

          {puedeCargarProduccion && (
            <div className="quick-actions">
              <button type="button" className="qa-btn" onClick={() => irACargar("/app/recoleccion")}>
                <i className="fa-solid fa-egg"></i>
                <span>Nueva recolección</span>
              </button>
              <button type="button" className="qa-btn" onClick={() => irACargar("/app/descartes")}>
                <i className="fa-solid fa-trash-can"></i>
                <span>Registrar descarte</span>
              </button>
              {esAdministrador && (
                <button type="button" className="qa-btn" onClick={() => irACargar("/app/compras")}>
                  <i className="fa-solid fa-cart-plus"></i>
                  <span>Nueva compra</span>
                </button>
              )}
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-title">
            <h3>Alertas recientes</h3>
            {datos.alertas_pendientes > 0 && (
              <span className="card-nota">
                {datos.alertas_pendientes} {datos.alertas_pendientes === 1 ? "activa" : "activas"}
              </span>
            )}
          </div>
          {datos.alertas.length === 0 ? (
            <div className="empty-state">
              No hay alertas. Los lotes vienen trabajando dentro de lo esperado.
            </div>
          ) : (
            datos.alertas.map((alerta) => <Alerta key={alerta.id_alerta} alerta={alerta} />)
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-title">
          <h3>Stock actual de productos</h3>
        </div>
        {stock.items.length === 0 ? (
          <div className="empty-state">Todavía no hay productos con stock para mostrar.</div>
        ) : (
          <div className="stock-donut-row">
            <div className="stock-grid">
              {stock.items.map((item, indice) => (
                <div className="stock-item" key={item.id_producto}>
                  <div className={`stock-icon stock-icon-dato ${TONOS[indice % TONOS.length].clase}`}>
                    <i className="fa-solid fa-egg"></i>
                  </div>
                  <div className="stock-value">{entero(item.stock)}</div>
                  <div className="stock-label">{item.producto}</div>
                  <Etiqueta item={item} tono={TONOS[indice % TONOS.length].clase} />
                </div>
              ))}
            </div>
            <Anillo items={stock.items} total={stock.total} />
          </div>
        )}
      </div>
    </div>
  );
}
