import { useEffect, useMemo, useState } from "react";
import { descargarInforme, getInforme } from "../api/informes";
import { listGalpones } from "../api/galpones";
import { listMateriasPrimas } from "../api/materias-primas";
import GraficoIndicador from "../components/GraficoIndicador";
import { BarrasHorizontales, COLORES, Dona } from "../components/GraficosInforme";
import { EsqueletoInforme } from "../components/Esqueleto";

import AyudaSeccion from "../components/AyudaSeccion";
const TABS = [
  { id: "produccion", ruta: "produccion", texto: "Producción", icono: "fa-egg", cu: "CU85" },
  { id: "lotes", ruta: "lotes", texto: "Lotes", icono: "fa-kiwi-bird", cu: "CU86" },
  { id: "materias", ruta: "materias-primas", texto: "Materias primas", icono: "fa-boxes-stacked", cu: "CU87" },
  { id: "descartes", ruta: "descartes", texto: "Descartes", icono: "fa-trash-can", cu: "CU88" },
  { id: "indicadores", ruta: "indicadores", texto: "Indicadores", icono: "fa-chart-line", cu: "CU89" },
];

const INDICADORES = [
  { id: "postura", texto: "Postura (%)" },
  { id: "mortandad", texto: "Mortandad (gallinas)" },
  { id: "consumo", texto: "Consumo de materia prima" },
];

const nfEntero = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 0 });
const nfDecimal = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 2 });

function isoLocal(fecha) {
  const m = String(fecha.getMonth() + 1).padStart(2, "0");
  const d = String(fecha.getDate()).padStart(2, "0");
  return `${fecha.getFullYear()}-${m}-${d}`;
}

function periodoInicial() {
  const hoy = new Date();
  const desde = new Date();
  desde.setDate(hoy.getDate() - 29);
  return { desde: isoLocal(desde), hasta: isoLocal(hoy) };
}

function formatear(valor, tipo) {
  if (valor === null || valor === undefined || valor === "") return "—";
  if (typeof valor === "string") {
    if (tipo === "fecha" && /^\d{4}-\d{2}-\d{2}$/.test(valor)) {
      const [a, m, d] = valor.split("-");
      return `${d}/${m}/${a}`;
    }
    return valor;
  }
  if (tipo === "entero") return nfEntero.format(valor);
  if (tipo === "decimal") return nfDecimal.format(valor);
  return String(valor);
}

/** Recorre todas las páginas de un listado paginado de DRF. */
async function traerTodas(listFn, params) {
  const resultados = [];
  for (let page = 1; page <= 50; page++) {
    const data = await listFn({ ...params, page });
    if (Array.isArray(data)) return data;
    resultados.push(...data.results);
    if (!data.next) break;
  }
  return resultados;
}

// ── Datos de los gráficos (salen de las filas del informe ya cargado) ────────

const promedio = (valores) => valores.reduce((a, b) => a + b, 0) / valores.length;

/** Postura promedio de cada galpón; los galpones sin recolecciones quedan en "—". */
function posturaPorGalpon(informe, galpones, idGalpon) {
  const porGalpon = {};
  for (const f of informe.filas) {
    if (f.postura_promedio !== null) (porGalpon[f.id_galpon] ||= []).push(f.postura_promedio);
  }
  return galpones
    .filter((g) => !idGalpon || String(g.id_galpon) === String(idGalpon))
    .map((g) => {
      const valor = porGalpon[g.id_galpon] ? promedio(porGalpon[g.id_galpon]) : null;
      // Por debajo de 70 % se vacía el galpón (criterio del productor).
      const color = valor === null ? COLORES.gris : valor < 70 ? COLORES.rojo : valor < 85 ? COLORES.dorado : COLORES.verde;
      return { etiqueta: g.galpon, valor, texto: valor === null ? "—" : `${nfDecimal.format(valor)}%`, color };
    });
}

/** Mortandad total de los lotes de cada galpón. */
function mortandadPorGalpon(informe) {
  const porGalpon = {};
  for (const f of informe.filas) porGalpon[f.galpon] = (porGalpon[f.galpon] || 0) + f.mortandad;
  const maximo = Math.max(0, ...Object.values(porGalpon));
  const filas = Object.entries(porGalpon).map(([galpon, valor]) => {
    const peso = maximo ? valor / maximo : 0;
    const color = !maximo ? COLORES.gris : peso >= 0.8 ? COLORES.rojo : peso < 0.25 ? COLORES.verde : COLORES.dorado;
    return { etiqueta: galpon, valor, texto: nfEntero.format(valor), color };
  });
  return { filas, maximo };
}

/** Cantidad de registros de descarte agrupados por la clave que devuelva `clave(fila)`. */
function contarPor(filas, clave) {
  const cuenta = {};
  for (const f of filas) {
    const k = clave(f);
    if (k) cuenta[k] = (cuenta[k] || 0) + 1;
  }
  return Object.entries(cuenta).map(([etiqueta, valor]) => ({ etiqueta, valor })).sort((a, b) => b.valor - a.valor);
}

/** Los 5 más frecuentes y el resto agrupado en "Otros". */
function conOtros(items, maximoItems = 5) {
  if (items.length <= maximoItems + 1) return items;
  const resto = items.slice(maximoItems).reduce((a, i) => a + i.valor, 0);
  return [...items.slice(0, maximoItems), { etiqueta: "Otros", valor: resto }];
}

const COLORES_RANKING = [COLORES.rojo, COLORES.dorado, COLORES.verde];

function TablaInforme({ informe }) {
  const { columnas, filas, totales } = informe;
  if (filas.length === 0) {
    return <div className="empty-state" style={{ padding: 28 }}>No hay datos para los filtros elegidos.</div>;
  }
  return (
    <div className="table-wrap" style={{ overflowX: "auto" }}>
      <table>
        <thead>
          <tr>
            {columnas.map((c) => (
              <th key={c.clave} style={c.tipo === "entero" || c.tipo === "decimal" ? { textAlign: "right" } : undefined}>
                {c.titulo}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filas.map((f, i) => (
            <tr key={i}>
              {columnas.map((c) => (
                <td
                  key={c.clave}
                  style={{
                    textAlign: c.tipo === "entero" || c.tipo === "decimal" ? "right" : undefined,
                    ...(c.clave === "stock_actual" && f.bajo_minimo ? { color: "var(--red-alerta)", fontWeight: 700 } : {}),
                  }}
                >
                  {formatear(f[c.clave], c.tipo)}
                  {c.clave === "stock_actual" && f.bajo_minimo && (
                    <i className="fa-solid fa-triangle-exclamation" title="Por debajo del mínimo" style={{ marginLeft: 6 }}></i>
                  )}
                </td>
              ))}
            </tr>
          ))}
          {totales && (
            <tr style={{ fontWeight: 700, background: "var(--gray-100)" }}>
              {columnas.map((c) => (
                <td
                  key={c.clave}
                  style={{ textAlign: c.tipo === "entero" || c.tipo === "decimal" ? "right" : undefined }}
                >
                  {totales[c.clave] === undefined ? "" : formatear(totales[c.clave], c.tipo)}
                </td>
              ))}
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function GraficosDescartes({ informe }) {
  const porGalpon = conOtros(contarPor(informe.filas, (f) => (f.galpon === "—" ? "Stock" : f.galpon)), 6);
  const materias = contarPor(informe.filas, (f) => (f.tipo === "Materia prima" ? f.item : null));
  const totalMaterias = materias.reduce((a, m) => a + m.valor, 0);
  const rankingMaterias = conOtros(materias).map((m, i) => ({
    etiqueta: m.etiqueta,
    valor: (m.valor / totalMaterias) * 100,
    texto: `${nfDecimal.format((m.valor / totalMaterias) * 100)}%`,
    color: m.etiqueta === "Otros" ? COLORES.gris : COLORES_RANKING[Math.min(i, 2)],
  }));
  return (
    <div className="grid-2" style={{ gridTemplateColumns: "1fr 1fr", marginBottom: 16 }}>
      <Dona
        titulo="Descartes por galpón"
        segmentos={porGalpon}
        centro={{ numero: nfEntero.format(informe.filas.length), texto: "Registros" }}
        nota='Los descartes de stock no pertenecen a un galpón y figuran como "Stock".'
      />
      {rankingMaterias.length > 0 ? (
        <BarrasHorizontales
          titulo="Descartes por materia prima"
          filas={rankingMaterias}
          maximo={100}
          nota="Porcentaje de los registros de descarte de materias primas."
        />
      ) : (
        <div className="card">
          <div className="card-title"><h3>Descartes por materia prima</h3></div>
          <div className="empty-state">No hay descartes de materias primas en este período.</div>
        </div>
      )}
    </div>
  );
}

function Kpi({ icono, fondo, color, valor, etiqueta }) {
  return (
    <div className="kpi-card">
      <div className="kpi-top">
        <div className="kpi-icon" style={{ background: fondo, color }}>
          <i className={`fa-solid ${icono}`}></i>
        </div>
      </div>
      <div className="value">{valor}</div>
      <div className="label">{etiqueta}</div>
    </div>
  );
}

// Debe coincidir con MAX_DIAS del backend (informes/calculos.py).
const MAX_DIAS_PERIODO = 366;
const MENSAJE_PERIODO_LARGO = `El período no puede superar los ${MAX_DIAS_PERIODO} días (un año). Acortá el rango de fechas.`;

/** Cantidad de días del período, contando los dos extremos. */
function diasDelPeriodo(desde, hasta) {
  const ms = new Date(`${hasta}T00:00:00`) - new Date(`${desde}T00:00:00`);
  return Math.round(ms / 86400000) + 1;
}

/** Texto de un error del informe, sin el nombre interno del campo (fecha_desde: ...). */
function mensajeDeInforme(err) {
  const detalle = err?.detail;
  if (detalle && typeof detalle === "object" && typeof detalle.detail !== "string") {
    const texto = Object.values(detalle).flat().join(" ");
    if (texto) return texto;
  }
  return err?.message || "No se pudo generar el informe.";
}

export default function InformesPage() {
  const [tab, setTab] = useState("produccion");
  const [periodo, setPeriodo] = useState(periodoInicial);
  const [idGalpon, setIdGalpon] = useState("");
  const [estadoLote, setEstadoLote] = useState("");
  const [idMateria, setIdMateria] = useState("");
  const [tipoDescarte, setTipoDescarte] = useState("");
  const [indicador, setIndicador] = useState("postura");
  const [objetivo, setObjetivo] = useState("");

  const [galpones, setGalpones] = useState([]);
  const [materias, setMaterias] = useState([]);
  // El informe se guarda junto con la pestaña que lo pidió: al cambiar de pestaña
  // no se debe mostrar, ni por un instante, el informe de la anterior.
  const [resultado, setResultado] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [descargando, setDescargando] = useState(null);

  const actual = TABS.find((t) => t.id === tab);
  const informe = resultado && resultado.tab === tab ? resultado.data : null;
  const usaPeriodo = tab !== "lotes";
  const usaGalpon = tab === "produccion" || tab === "lotes" || tab === "descartes" || tab === "indicadores";
  const usaMateria = tab === "materias" || (tab === "indicadores" && indicador === "consumo");

  useEffect(() => {
    traerTodas(listGalpones, {}).then(setGalpones).catch(() => setGalpones([]));
    traerTodas(listMateriasPrimas, {}).then(setMaterias).catch(() => setMaterias([]));
  }, []);

  // Parámetros del informe activo (solo los que usa cada pestaña).
  const params = useMemo(() => {
    const p = {};
    if (usaPeriodo) {
      p.fecha_desde = periodo.desde;
      p.fecha_hasta = periodo.hasta;
    }
    if (usaGalpon && idGalpon) p.id_galpon = idGalpon;
    if (tab === "lotes" && estadoLote) p.estado = estadoLote;
    if (usaMateria && idMateria) p.id_materia_prima = idMateria;
    if (tab === "descartes" && tipoDescarte) p.tipo = tipoDescarte;
    if (tab === "indicadores") p.indicador = indicador;
    return p;
  }, [tab, periodo, idGalpon, estadoLote, idMateria, tipoDescarte, indicador, usaPeriodo, usaGalpon, usaMateria]);

  const faltaFiltro = tab === "indicadores" && indicador === "consumo" && !idMateria;
  const periodoCompleto = Boolean(periodo.desde && periodo.hasta);
  const periodoInvertido = usaPeriodo && periodoCompleto && periodo.desde > periodo.hasta;
  const periodoExcedido =
    usaPeriodo && periodoCompleto && !periodoInvertido && diasDelPeriodo(periodo.desde, periodo.hasta) > MAX_DIAS_PERIODO;
  const periodoInvalido = usaPeriodo && (!periodoCompleto || periodoInvertido || periodoExcedido);

  useEffect(() => {
    if (faltaFiltro || periodoInvalido) {
      setResultado(null);
      setError(null);
      setLoading(false);
      return undefined;
    }
    let cancelado = false;
    setLoading(true);
    setError(null);
    getInforme(actual.ruta, params)
      .then((data) => !cancelado && setResultado({ tab: actual.id, data }))
      .catch((err) => {
        if (cancelado) return;
        setResultado(null);
        setError(err.status === 0 ? err.message : mensajeDeInforme(err));
      })
      .finally(() => !cancelado && setLoading(false));
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params, faltaFiltro, periodoInvalido]);

  async function exportar(formato) {
    setDescargando(formato);
    setError(null);
    try {
      const extra = tab === "indicadores" && objetivo !== "" ? { objetivo } : {};
      await descargarInforme(actual.ruta, { ...params, ...extra }, formato);
    } catch (err) {
      setError(mensajeDeInforme(err));
    } finally {
      setDescargando(null);
    }
  }

  const objetivoNumero = objetivo === "" ? null : Number(objetivo);
  const diferencia =
    informe?.promedio !== null && informe?.promedio !== undefined && objetivoNumero !== null
      ? informe.promedio - objetivoNumero
      : null;
  const puedeExportar = informe && !loading && !error && !periodoInvalido;

  return (
    <div className="page active" id="page-informes">
      <div className="page-header">
        <div>
          <div className="page-titulo"><h1>Informes</h1><AyudaSeccion seccion="informes" /></div>
          <div className="desc">Indicadores productivos y reportes de producción, lotes, materias primas y descartes.</div>
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }} data-tutorial="inf-exportar">
          <button className="btn btn-outline" disabled={!puedeExportar || descargando} onClick={() => exportar("pdf")}>
            <i className="fa-solid fa-file-pdf"></i> {descargando === "pdf" ? "Generando..." : "Exportar a PDF"}
          </button>
          <button className="btn btn-green" disabled={!puedeExportar || descargando} onClick={() => exportar("xlsx")}>
            <i className="fa-solid fa-file-excel"></i> {descargando === "xlsx" ? "Generando..." : "Exportar a Excel"}
          </button>
        </div>
      </div>

      {/* En celular los informes (tablas anchas y gráficos) no se leen bien: se avisa y se oculta el resto. */}
      <div className="aviso-informes">
        <i className="fa-solid fa-display"></i>
        <div>
          <b>Mejor en una pantalla más grande</b>
          <p>Los informes tienen tablas y gráficos que necesitan más espacio. Abrí AviGest desde una computadora o una tablet para verlos y exportarlos.</p>
        </div>
      </div>

      <div className="tabs" role="tablist" data-tutorial="inf-tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={t.id === tab}
            className={`tab-btn ${t.id === tab ? "tab-active" : ""}`}
            onClick={() => setTab(t.id)}
          >
            <i className={`fa-solid ${t.icono}`}></i> {t.texto}
          </button>
        ))}
      </div>

      <div className="toolbar" data-tutorial="sec-filtros">
        {usaPeriodo && (
          <>
            <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 14 }}>
              <span style={{ color: "var(--gray-500)" }}>Desde</span>
              <input
                type="date" className="filter-date" value={periodo.desde} max={periodo.hasta || undefined}
                onChange={(e) => setPeriodo((p) => ({ ...p, desde: e.target.value }))}
              />
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 14 }}>
              <span style={{ color: "var(--gray-500)" }}>Hasta</span>
              <input
                type="date" className="filter-date" value={periodo.hasta} min={periodo.desde || undefined}
                onChange={(e) => setPeriodo((p) => ({ ...p, hasta: e.target.value }))}
              />
            </label>
          </>
        )}
        {usaGalpon && (
          <select className="select-filter" value={idGalpon} onChange={(e) => setIdGalpon(e.target.value)}>
            <option value="">Galpón: Todos</option>
            {galpones.map((g) => (
              <option key={g.id_galpon} value={g.id_galpon}>{g.galpon}</option>
            ))}
          </select>
        )}
        {tab === "lotes" && (
          <select className="select-filter" value={estadoLote} onChange={(e) => setEstadoLote(e.target.value)}>
            <option value="">Etapa: Todas</option>
            <option value="T">Transición</option>
            <option value="P">Producción</option>
            <option value="F">Finalizado</option>
          </select>
        )}
        {tab === "descartes" && (
          <select className="select-filter" value={tipoDescarte} onChange={(e) => setTipoDescarte(e.target.value)}>
            <option value="">Tipo: Todos</option>
            <option value="G">Gallinas</option>
            <option value="M">Materia prima</option>
            <option value="P">Producto</option>
          </select>
        )}
        {tab === "indicadores" && (
          <select className="select-filter" value={indicador} onChange={(e) => setIndicador(e.target.value)}>
            {INDICADORES.map((i) => (
              <option key={i.id} value={i.id}>{i.texto}</option>
            ))}
          </select>
        )}
        {usaMateria && (
          <select className="select-filter" value={idMateria} onChange={(e) => setIdMateria(e.target.value)}>
            <option value="">{tab === "materias" ? "Materia prima: Todas" : "Elegí la materia prima"}</option>
            {materias.map((m) => (
              <option key={m.id_materia_prima} value={m.id_materia_prima}>{m.materia_prima}</option>
            ))}
          </select>
        )}
      </div>

      {periodoInvalido && (
        <div className="banner banner-error">
          {periodoExcedido
            ? MENSAJE_PERIODO_LARGO
            : "Elegí un período válido: la fecha desde no puede ser posterior a la fecha hasta."}
        </div>
      )}
      {error && <div className="banner banner-error">{error}</div>}
      {loading && <EsqueletoInforme texto="Generando informe..." />}
      {faltaFiltro && (
        <div className="empty-state" style={{ padding: 28 }}>
          Elegí una materia prima para ver su consumo en el período.
        </div>
      )}

      {informe && !loading && !error && !periodoInvalido && tab !== "indicadores" && (
        <>
          {tab === "descartes" && informe.resumen && Object.keys(informe.resumen).length > 0 && (
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 14 }}>
              {Object.entries(informe.resumen).map(([tipo, n]) => (
                <span key={tipo} className="badge badge-green">{tipo}: {n}</span>
              ))}
            </div>
          )}
          {tab === "materias" && (
            <div className="form-hint" style={{ marginBottom: 10 }}>
              "Consumido" es lo enviado a los galpones en entradas finalizadas. El stock actual es el total, no solo el del período.
            </div>
          )}
          {tab === "produccion" && informe.filas.length > 0 && galpones.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <BarrasHorizontales
                titulo="Postura por galpón"
                filas={posturaPorGalpon(informe, galpones, idGalpon)}
                maximo={100}
                nota="Verde: 85 % o más · Dorado: entre 70 % y 85 % · Rojo: menos de 70 % (criterio de vaciado sanitario)."
              />
            </div>
          )}
          {tab === "lotes" && informe.filas.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <BarrasHorizontales
                titulo="Mortandad por galpón"
                {...mortandadPorGalpon(informe)}
                nota="Gallinas perdidas desde el ingreso de los lotes (iniciales menos actuales)."
              />
            </div>
          )}
          {tab === "descartes" && informe.filas.length > 0 && <GraficosDescartes informe={informe} />}
          <TablaInforme informe={informe} />
        </>
      )}

      {informe && !loading && !error && !periodoInvalido && tab === "indicadores" && (
        <>
          <div className="kpi-grid">
            <Kpi
              icono="fa-chart-line" fondo="var(--gold-100)" color="var(--gold-texto)"
              valor={informe.resumen.postura_promedio === null ? "—" : `${nfDecimal.format(informe.resumen.postura_promedio)} %`}
              etiqueta="Postura promedio del período"
            />
            <Kpi
              icono="fa-egg" fondo="var(--green-100)" color="var(--green-700)"
              valor={nfEntero.format(informe.resumen.huevos_producidos)} etiqueta="Huevos producidos"
            />
            <Kpi
              icono="fa-box-open" fondo="var(--red-100)" color="var(--red-500)"
              valor={nfEntero.format(informe.resumen.descartes_registrados)} etiqueta="Descartes registrados"
            />
            <Kpi
              icono="fa-skull" fondo="var(--red-100)" color="var(--red-500)"
              valor={nfEntero.format(informe.resumen.mortandad_total)} etiqueta="Mortandad (gallinas)"
            />
          </div>

          <div className="card">
            <div className="card-title">
              <h3>{informe.titulo.replace("Indicador: ", "")}</h3>
              <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 14 }}>
                <span style={{ color: "var(--gray-500)" }}>
                  Valor objetivo{informe.unidad ? ` (${informe.unidad})` : ""}
                </span>
                <input
                  type="number" min="0" step="any" className="filter-date" style={{ width: 110 }}
                  value={objetivo} placeholder="Opcional"
                  onChange={(e) => setObjetivo(e.target.value)}
                />
              </label>
            </div>

            <GraficoIndicador serie={informe.serie} objetivo={objetivoNumero} unidad={informe.unidad} />

            <div style={{ display: "flex", gap: 20, flexWrap: "wrap", marginTop: 12 }}>
              <span className="legend-item"><span className="legend-dot" style={{ background: "var(--serie-real)" }}></span> Valor real</span>
              {objetivoNumero !== null && (
                <span className="legend-item"><span className="legend-dot" style={{ background: "#c9962b" }}></span> Valor objetivo</span>
              )}
            </div>

            {informe.promedio !== null && (
              <div className="form-hint" style={{ marginTop: 10, fontSize: 14 }}>
                Promedio del período: <b>{nfDecimal.format(informe.promedio)} {informe.unidad}</b>
                {diferencia !== null && (
                  <>
                    {" "}· {Math.abs(diferencia) < 0.005
                      ? "coincide con el objetivo."
                      : `${nfDecimal.format(Math.abs(diferencia))} ${informe.unidad} ${diferencia > 0 ? "por encima" : "por debajo"} del objetivo.`}
                  </>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
