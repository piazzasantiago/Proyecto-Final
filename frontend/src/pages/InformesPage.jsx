import { useEffect, useMemo, useState } from "react";
import { descargarInforme, getInforme } from "../api/informes";
import { listGalpones } from "../api/galpones";
import { listMateriasPrimas } from "../api/materias-primas";
import GraficoIndicador from "../components/GraficoIndicador";

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
                    ...(c.clave === "stock_actual" && f.bajo_minimo ? { color: "#c0392b", fontWeight: 700 } : {}),
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
  const [informe, setInforme] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [descargando, setDescargando] = useState(null);

  const actual = TABS.find((t) => t.id === tab);
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
  const periodoInvalido = usaPeriodo && (!periodo.desde || !periodo.hasta || periodo.desde > periodo.hasta);

  useEffect(() => {
    if (faltaFiltro || periodoInvalido) {
      setInforme(null);
      setError(null);
      setLoading(false);
      return undefined;
    }
    let cancelado = false;
    setLoading(true);
    setError(null);
    getInforme(actual.ruta, params)
      .then((data) => !cancelado && setInforme(data))
      .catch((err) => {
        if (cancelado) return;
        setInforme(null);
        setError(err.status === 0 ? err.message : err.message || "No se pudo generar el informe.");
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
      await descargarInforme(actual.ruta, params, formato);
    } catch (err) {
      setError(err.message);
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
          <h1>Informes</h1>
          <div className="desc">Indicadores productivos y reportes de producción, lotes, materias primas y descartes.</div>
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button className="btn btn-outline" disabled={!puedeExportar || descargando} onClick={() => exportar("pdf")}>
            <i className="fa-solid fa-file-pdf"></i> {descargando === "pdf" ? "Generando..." : "Exportar a PDF"}
          </button>
          <button className="btn btn-green" disabled={!puedeExportar || descargando} onClick={() => exportar("xlsx")}>
            <i className="fa-solid fa-file-excel"></i> {descargando === "xlsx" ? "Generando..." : "Exportar a Excel"}
          </button>
        </div>
      </div>

      <div className="tabs" role="tablist">
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

      <div className="toolbar">
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
        <div className="banner banner-error">Elegí un período válido: la fecha desde no puede ser posterior a la fecha hasta.</div>
      )}
      {error && <div className="banner banner-error">{error}</div>}
      {loading && <div className="banner banner-loading">Generando informe...</div>}
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
          <TablaInforme informe={informe} />
        </>
      )}

      {informe && !loading && !error && !periodoInvalido && tab === "indicadores" && (
        <>
          <div className="kpi-grid">
            <Kpi
              icono="fa-chart-line" fondo="var(--gold-100)" color="#96721e"
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
              <span className="legend-item"><span className="legend-dot" style={{ background: "#2e7d4f" }}></span> Valor real</span>
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
