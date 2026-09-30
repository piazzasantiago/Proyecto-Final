import { useEffect, useState, useMemo } from "react";
import { listLotes, deleteLote, iniciarProduccion, vaciarLote } from "../api/lotes";
import { listGalpones } from "../api/galpones";
import LoteFormModal from "../components/LoteFormModal";
import { useAuth } from "../context/AuthContext";

const ESTADO_TRANSICION = "T";
const ESTADO_PRODUCCION = "P";
const ESTADO_FINALIZADO = "F";

const BADGE = {
  T: "badge-gold",
  P: "badge-green",
  F: "badge-gray",
};

function formatFecha(iso) {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

function formatGalpon(lote) {
  const id = lote.galpon?.id_galpon;
  const nombre = lote.galpon?.galpon || "";
  return id ? `G-${String(id).padStart(2, "0")} · ${nombre}` : nombre;
}

/** Calcula qué semana del plan de transición es la "semana actual". */
function semanaActual(lote) {
  if (!lote.plan_transicion?.fecha_inicio) return null;
  const inicio = new Date(lote.plan_transicion.fecha_inicio);
  const hoy = new Date();
  const dias = Math.floor((hoy - inicio) / (1000 * 60 * 60 * 24));
  const semana = Math.floor(dias / 7) + 1;
  return semana >= 1 && semana <= 4 ? semana : null;
}

export default function LotesPage() {
  const { esAdministrador } = useAuth();

  const [lotes, setLotes] = useState([]);
  const [galpones, setGalpones] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [galponFilter, setGalponFilter] = useState("");
  const [modalMode, setModalMode] = useState(null); // null | "create" | "edit"

  async function fetchLotes() {
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (search) params.search = search;
      if (galponFilter) params.id_galpon = galponFilter;
      const data = await listLotes(params);
      const lista = data.results ?? data;
      setLotes(lista);
      if (!selectedId && lista.length > 0) {
        setSelectedId(lista[0].id_lote);
      }
    } catch {
      setError("No se pudo conectar con el servidor. ¿Está corriendo el backend en el puerto 8000?");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchLotes();
    listGalpones({ estado: "A" })
      .then((d) => setGalpones(d.results ?? d))
      .catch(() => setGalpones([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, galponFilter]);

  const selected = useMemo(
    () => lotes.find((l) => l.id_lote === selectedId) || null,
    [lotes, selectedId]
  );

  const porEstado = useMemo(() => ({
    [ESTADO_TRANSICION]: lotes.filter((l) => l.estado === ESTADO_TRANSICION),
    [ESTADO_PRODUCCION]: lotes.filter((l) => l.estado === ESTADO_PRODUCCION),
    [ESTADO_FINALIZADO]: lotes.filter((l) => l.estado === ESTADO_FINALIZADO),
  }), [lotes]);

  async function handleCreate(data) {
    setModalMode(null);
    await fetchLotes();
  }

  async function handleUpdate(data) {
    setModalMode(null);
    await fetchLotes();
  }

  async function handleDelete() {
    if (!selected) return;
    if (!confirm(`¿Eliminar el lote "${selected.codigo}"? Esta acción no se puede deshacer.`)) return;
    await deleteLote(selected.id_lote);
    setSelectedId(null);
    await fetchLotes();
  }

  async function handleIniciarProduccion() {
    if (!selected) return;
    if (!confirm(`¿Iniciar producción para el lote ${selected.codigo}? El plan de transición quedará finalizado.`)) return;
    try {
      await iniciarProduccion(selected.id_lote);
      await fetchLotes();
    } catch (err) {
      alert(err.message || "No se pudo iniciar la producción.");
    }
  }

  async function handleVaciar() {
    if (!selected) return;
    if (!confirm(`¿Confirmar vaciado sanitario para el lote ${selected.codigo}? El lote pasará a estado Finalizado.`)) return;
    try {
      await vaciarLote(selected.id_lote);
      await fetchLotes();
    } catch (err) {
      alert(err.message || "No se pudo realizar el vaciado.");
    }
  }

  function renderLoteCard(lote) {
    const isSel = lote.id_lote === selectedId;
    return (
      <div
        key={lote.id_lote}
        className={`lote-card${isSel ? " card-selected" : ""}`}
        onClick={() => setSelectedId(lote.id_lote)}
      >
        <div className="lc-top">
          <div>
            <div className="lc-code">{lote.codigo}</div>
            <div className="lc-galpon">{formatGalpon(lote)}</div>
          </div>
          <span className={`badge ${BADGE[lote.estado]}`}>{lote.estado_display}</span>
        </div>
        <div className="gc-stats">
          <div className="gc-stat"><i className="fa-solid fa-kiwi-bird"></i> {lote.cantidad_actual?.toLocaleString("es-AR")} aves</div>
          <div className="gc-stat"><i className="fa-solid fa-calendar"></i> Ingreso {formatFecha(lote.fecha_ingreso)}</div>
          {lote.estado === ESTADO_FINALIZADO
            ? <div className="gc-stat"><i className="fa-solid fa-shower"></i> Vaciado {formatFecha(lote.fecha_vaciado)}</div>
            : <div className="gc-stat"><i className="fa-solid fa-hourglass-half"></i> {lote.edad_semanas} semanas</div>
          }
        </div>
      </div>
    );
  }

  function renderStepper(lote) {
    const estado = lote.estado;
    const plan = lote.plan_transicion;

    const steps = [
      { label: "Ingreso", sub: formatFecha(lote.fecha_ingreso), done: true, current: false },
      {
        label: "Transición",
        sub: plan ? `${formatFecha(plan.fecha_inicio)} – ${formatFecha(plan.fecha_fin)}` : "4 sem.",
        done: estado === ESTADO_PRODUCCION || estado === ESTADO_FINALIZADO,
        current: estado === ESTADO_TRANSICION,
      },
      {
        label: "Producción",
        sub: estado === ESTADO_PRODUCCION ? "En curso" : estado === ESTADO_FINALIZADO ? "completada" : "Pendiente",
        done: estado === ESTADO_FINALIZADO,
        current: estado === ESTADO_PRODUCCION,
      },
      {
        label: "Vaciado sanitario",
        sub: lote.fecha_vaciado ? formatFecha(lote.fecha_vaciado) : "Pendiente",
        done: estado === ESTADO_FINALIZADO,
        current: false,
      },
    ];

    return (
      <div className="stepper">
        {steps.map((s, i) => (
          <div key={i} className={`step${s.done ? " done" : ""}${s.current ? " current" : ""}`}>
            <div className="step-line"></div>
            <div className="step-circle">
              {s.done ? <i className="fa-solid fa-check"></i> : i + 1}
            </div>
            <div className="step-label">{s.label}</div>
            <div className="step-sub">{s.sub}</div>
          </div>
        ))}
      </div>
    );
  }

  function renderPlanTable(lote) {
    const plan = lote.plan_transicion;
    if (!plan) return null;
    const actual = lote.estado === ESTADO_TRANSICION ? semanaActual(lote) : null;
    const semanas = [1, 2, 3, 4];
    return (
      <table className="plan-table">
        <thead>
          <tr>
            <th>Semana</th>
            <th>Agua (L)</th>
            <th>Alimento (kg)</th>
            <th>Luz (hs)</th>
          </tr>
        </thead>
        <tbody>
          {semanas.map((s) => (
            <tr key={s} className={actual === s ? "week-current" : ""}>
              <td>{s}{actual === s ? " ★" : ""}</td>
              <td>{Number(plan[`agua_semana${s}`]).toFixed(2)}</td>
              <td>{Number(plan[`alimento_semana${s}`]).toFixed(2)}</td>
              <td>{Number(plan[`horas_luz_semana${s}`]).toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  }

  return (
    <div className="page active" id="page-lotes">
      <div className="page-header">
        <div>
          <h1>Lotes de gallinas</h1>
          <div className="desc">Seguimiento del ciclo de vida productivo de cada lote, desde su ingreso hasta el vaciado sanitario.</div>
        </div>
        {esAdministrador && (
          <button className="btn btn-green" onClick={() => setModalMode("create")}>
            <i className="fa-solid fa-plus"></i> Nuevo lote
          </button>
        )}
      </div>

      <div className="toolbar">
        <div className="search-box">
          <i className="fa-solid fa-magnifying-glass"></i>
          <input
            type="text"
            placeholder="Buscar por código de lote..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select
          className="select-filter"
          value={galponFilter}
          onChange={(e) => setGalponFilter(e.target.value)}
        >
          <option value="">Galpón: Todos</option>
          {galpones.map((g) => (
            <option key={g.id_galpon} value={g.id_galpon}>
              G-{String(g.id_galpon).padStart(2, "0")} · {g.galpon}
            </option>
          ))}
        </select>
      </div>

      {error && <div className="banner banner-error">{error}</div>}
      {loading && <div className="banner banner-loading">Cargando lotes...</div>}

      {!loading && !error && (
        <div className="page-body-split">
          {/* ---- Kanban ---- */}
          <div className="kanban-cols">
            {[
              { key: ESTADO_TRANSICION, label: "Transición" },
              { key: ESTADO_PRODUCCION, label: "Producción" },
              { key: ESTADO_FINALIZADO, label: "Finalizado" },
            ].map(({ key, label }) => (
              <div key={key} className="kanban-col">
                <div className="kanban-col-head">
                  <span>{label}</span>
                  <span className="kanban-count">{porEstado[key].length}</span>
                </div>
                {porEstado[key].length === 0 && (
                  <div className="empty-state" style={{ padding: "20px 10px", fontSize: 13 }}>Sin lotes</div>
                )}
                {porEstado[key].map(renderLoteCard)}
              </div>
            ))}
          </div>

          {/* ---- Panel de detalle ---- */}
          {selected ? (
            <div className="detail-panel">
              <div className="detail-head">
                <div>
                  <h3>{selected.codigo}</h3>
                  <div className="sub">{formatGalpon(selected)}</div>
                </div>
                <span className={`badge ${BADGE[selected.estado]}`}>{selected.estado_display}</span>
              </div>

              <div className="detail-body">
                {/* Stepper de ciclo de vida */}
                {renderStepper(selected)}

                <div className="detail-sec-title" style={{ marginTop: 14 }}>Datos del lote</div>
                <div className="detail-row"><span>Cantidad inicial</span><span>{selected.cantidad_inicial?.toLocaleString("es-AR")}</span></div>
                <div className="detail-row"><span>Cantidad actual</span><span>{selected.cantidad_actual?.toLocaleString("es-AR")}</span></div>
                <div className="detail-row"><span>Fecha de ingreso</span><span>{formatFecha(selected.fecha_ingreso)}</span></div>
                <div className="detail-row"><span>Fecha de vaciado</span><span>{formatFecha(selected.fecha_vaciado)}</span></div>
                {selected.observaciones && (
                  <div className="detail-row" style={{ borderBottom: "none", alignItems: "flex-start", flexDirection: "column", gap: 4 }}>
                    <span>Observaciones</span>
                    <span style={{ fontWeight: 500, color: "var(--gray-700)", textAlign: "left" }}>{selected.observaciones}</span>
                  </div>
                )}

                <div className="detail-sec-title">Indicadores</div>
                <div className="detail-row"><span>Edad del lote</span><span>{selected.edad_semanas} semanas</span></div>
                <div className="detail-row"><span>% Postura actual</span><span>—</span></div>

                <div className="detail-sec-title">
                  Plan de transición
                  {selected.plan_transicion && (
                    <span style={{ fontWeight: 400, textTransform: "none", fontSize: 12, marginLeft: 6 }}>
                      ({formatFecha(selected.plan_transicion.fecha_inicio)} – {formatFecha(selected.plan_transicion.fecha_fin)})
                    </span>
                  )}
                </div>
                {renderPlanTable(selected)}
              </div>

              {esAdministrador && (
                <div className="detail-actions" style={{ flexWrap: "wrap" }}>
                  <button className="btn btn-outline" onClick={() => setModalMode("edit")}>
                    <i className="fa-solid fa-pen"></i> Editar
                  </button>
                  {selected.estado === ESTADO_TRANSICION && (
                    <button className="btn btn-outline btn-success-ghost" onClick={handleIniciarProduccion}>
                      <i className="fa-solid fa-play"></i> Iniciar producción
                    </button>
                  )}
                  {selected.estado !== ESTADO_FINALIZADO && (
                    <button className="btn btn-outline btn-warning-ghost" onClick={handleVaciar}>
                      <i className="fa-solid fa-shower"></i> Vaciado sanitario
                    </button>
                  )}
                  <button className="btn btn-outline btn-danger-ghost" onClick={handleDelete}>
                    <i className="fa-solid fa-trash"></i> Eliminar
                  </button>
                </div>
              )}
            </div>
          ) : (
            !loading && lotes.length === 0 && (
              <div className="detail-panel" style={{ padding: 24 }}>
                <div className="empty-state">
                  {esAdministrador
                    ? 'No hay lotes registrados todavía. Creá el primero con "Nuevo lote".'
                    : "No hay lotes disponibles para tu usuario."}
                </div>
              </div>
            )
          )}
        </div>
      )}

      {modalMode === "create" && (
        <LoteFormModal
          galpones={galpones}
          onClose={() => setModalMode(null)}
          onSubmit={handleCreate}
          onCreated={(id) => setSelectedId(id)}
        />
      )}
      {modalMode === "edit" && selected && (
        <LoteFormModal
          galpones={galpones}
          initialData={selected}
          onClose={() => setModalMode(null)}
          onSubmit={handleUpdate}
        />
      )}
    </div>
  );
}
