import { useEffect, useState, useMemo } from "react";
import {
  listRecolecciones,
  deleteRecoleccion,
  finalizarRecoleccion,
} from "../api/recolecciones";
import { listGalpones } from "../api/galpones";
import { listProductos } from "../api/productos";
import RecoleccionFormModal from "../components/RecoleccionFormModal";
import { useAuth } from "../context/AuthContext";

const ESTADO_PENDIENTE = "P";
const ESTADO_FINALIZADA = "F";

function formatFecha(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("es-AR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatGalpon(rec) {
  const id = rec.galpon?.id_galpon;
  const nombre = rec.galpon?.galpon || "";
  return id ? `G-${String(id).padStart(2, "0")} · ${nombre}` : nombre;
}

export default function RecoleccionesPage() {
  const { esAdministrador, esOperario } = useAuth();
  const puedeEscribir = esAdministrador || esOperario;

  const [recolecciones, setRecolecciones] = useState([]);
  const [galpones, setGalpones] = useState([]);
  const [productos, setProductos] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [galponFilter, setGalponFilter] = useState("");
  const [estadoFilter, setEstadoFilter] = useState("");
  const [modalMode, setModalMode] = useState(null); // null | "create" | "edit"

  async function fetchRecolecciones() {
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (galponFilter) params.id_galpon = galponFilter;
      if (estadoFilter) params.estado = estadoFilter;
      const data = await listRecolecciones(params);
      const lista = data.results ?? data;
      setRecolecciones(lista);
      if (!selectedId && lista.length > 0) {
        setSelectedId(lista[0].id_recoleccion);
      }
    } catch {
      setError(
        "No se pudo conectar con el servidor. ¿Está corriendo el backend en el puerto 8000?"
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchRecolecciones();
    listGalpones({ estado: "A" })
      .then((d) => setGalpones(d.results ?? d))
      .catch(() => setGalpones([]));
    listProductos({ estado: "A" })
      .then((d) => setProductos(d.results ?? d))
      .catch(() => setProductos([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [galponFilter, estadoFilter]);

  const selected = useMemo(
    () => recolecciones.find((r) => r.id_recoleccion === selectedId) || null,
    [recolecciones, selectedId]
  );

  async function handleCreate() {
    setModalMode(null);
    await fetchRecolecciones();
  }

  async function handleUpdate() {
    setModalMode(null);
    await fetchRecolecciones();
  }

  async function handleDelete() {
    if (!selected) return;
    if (
      !confirm(
        `¿Eliminar la recolección del ${formatFecha(selected.fecha)}? Esta acción no se puede deshacer.`
      )
    )
      return;
    await deleteRecoleccion(selected.id_recoleccion);
    setSelectedId(null);
    await fetchRecolecciones();
  }

  async function handleFinalizar() {
    if (!selected) return;
    if (
      !confirm(
        `¿Finalizar la recolección del ${formatFecha(selected.fecha)}? No podrá editarse después.`
      )
    )
      return;
    try {
      await finalizarRecoleccion(selected.id_recoleccion);
      await fetchRecolecciones();
    } catch (err) {
      alert(err.message || "No se pudo finalizar la recolección.");
    }
  }

  // ── Totales por recolección ─────────────────────────────────────────────

  function totalUnidades(rec) {
    return (rec.lineas ?? []).reduce((s, l) => s + (l.cantidad || 0), 0);
  }

  return (
    <div className="page active" id="page-recoleccion">
      <div className="page-header">
        <div>
          <h1>Recolección diaria</h1>
          <div className="desc">
            Registro de huevos recolectados por galpón y producto.
          </div>
        </div>
        {puedeEscribir && (
          <button
            className="btn btn-green"
            onClick={() => setModalMode("create")}
          >
            <i className="fa-solid fa-plus"></i> Nueva recolección
          </button>
        )}
      </div>

      {/* Filtros */}
      <div className="toolbar">
        <select
          className="select-filter"
          value={galponFilter}
          onChange={(e) => {
            setGalponFilter(e.target.value);
            setSelectedId(null);
          }}
        >
          <option value="">Galpón: Todos</option>
          {galpones.map((g) => (
            <option key={g.id_galpon} value={g.id_galpon}>
              G-{String(g.id_galpon).padStart(2, "0")} · {g.galpon}
            </option>
          ))}
        </select>
        <select
          className="select-filter"
          value={estadoFilter}
          onChange={(e) => {
            setEstadoFilter(e.target.value);
            setSelectedId(null);
          }}
        >
          <option value="">Estado: Todos</option>
          <option value={ESTADO_PENDIENTE}>Pendiente</option>
          <option value={ESTADO_FINALIZADA}>Finalizada</option>
        </select>
      </div>

      {error && <div className="banner banner-error">{error}</div>}
      {loading && <div className="banner banner-loading">Cargando recolecciones...</div>}

      {!loading && !error && (
        <div className="page-body-split">
          {/* ── Lista ─────────────────────────────────────────────────── */}
          <div className="list-panel">
            {recolecciones.length === 0 ? (
              <div className="empty-state" style={{ padding: 24 }}>
                {puedeEscribir
                  ? 'No hay recolecciones registradas. Creá la primera con "Nueva recolección".'
                  : "No hay recolecciones disponibles."}
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th>Galpón</th>
                    <th>Lote</th>
                    <th>Estado</th>
                    <th>Ítems</th>
                    <th>Total uds.</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {recolecciones.map((rec) => {
                    const isSel = rec.id_recoleccion === selectedId;
                    return (
                      <tr
                        key={rec.id_recoleccion}
                        onClick={() => setSelectedId(rec.id_recoleccion)}
                        style={{
                          cursor: "pointer",
                          background: isSel
                            ? "var(--green-50, #f0fdf4)"
                            : undefined,
                        }}
                      >
                        <td>{formatFecha(rec.fecha)}</td>
                        <td>{formatGalpon(rec)}</td>
                        <td>{rec.lote?.codigo ?? "—"}</td>
                        <td>
                          <span
                            className={`badge ${
                              rec.estado === ESTADO_PENDIENTE
                                ? "badge-gold"
                                : "badge-gray"
                            }`}
                          >
                            {rec.estado_display}
                          </span>
                        </td>
                        <td>{(rec.lineas ?? []).length}</td>
                        <td>{totalUnidades(rec).toLocaleString("es-AR")}</td>
                        <td>
                          <i className="fa-solid fa-eye" style={{ color: "var(--gray-400)" }}></i>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>

          {/* ── Panel de detalle ────────────────────────────────────── */}
          {selected && (
            <div className="detail-panel">
              <div className="detail-head">
                <div>
                  <h3>{formatGalpon(selected)}</h3>
                  <div className="sub">Lote: {selected.lote?.codigo ?? "—"}</div>
                </div>
                <span
                  className={`badge ${
                    selected.estado === ESTADO_PENDIENTE
                      ? "badge-gold"
                      : "badge-gray"
                  }`}
                >
                  {selected.estado_display}
                </span>
              </div>

              <div className="detail-body">
                <div className="detail-sec-title">Datos de la recolección</div>
                <div className="detail-row">
                  <span>Galpón</span>
                  <span>{formatGalpon(selected)}</span>
                </div>
                <div className="detail-row">
                  <span>Lote</span>
                  <span>{selected.lote?.codigo ?? "—"}</span>
                </div>
                <div className="detail-row">
                  <span>Fecha y hora</span>
                  <span>{formatFecha(selected.fecha)}</span>
                </div>
                <div className="detail-row">
                  <span>Estado</span>
                  <span>{selected.estado_display}</span>
                </div>
                {selected.observaciones && (
                  <div
                    className="detail-row"
                    style={{
                      borderBottom: "none",
                      alignItems: "flex-start",
                      flexDirection: "column",
                      gap: 4,
                    }}
                  >
                    <span>Observaciones</span>
                    <span
                      style={{
                        fontWeight: 500,
                        color: "var(--gray-700)",
                        textAlign: "left",
                      }}
                    >
                      {selected.observaciones}
                    </span>
                  </div>
                )}

                <div className="detail-sec-title">Detalle</div>
                <table className="plan-table">
                  <thead>
                    <tr>
                      <th>Producto</th>
                      <th style={{ textAlign: "right" }}>Cantidad</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(selected.lineas ?? []).map((l) => (
                      <tr key={l.id_linea_recoleccion}>
                        <td>{l.producto?.producto ?? "—"}</td>
                        <td style={{ textAlign: "right" }}>
                          {l.cantidad?.toLocaleString("es-AR")}
                        </td>
                      </tr>
                    ))}
                    <tr style={{ fontWeight: 600, borderTop: "2px solid var(--gray-200)" }}>
                      <td>Total</td>
                      <td style={{ textAlign: "right" }}>
                        {totalUnidades(selected).toLocaleString("es-AR")}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* Acciones */}
              {selected.estado === ESTADO_PENDIENTE && puedeEscribir ? (
                <div className="detail-actions" style={{ flexWrap: "wrap" }}>
                  <button
                    className="btn btn-outline"
                    onClick={() => setModalMode("edit")}
                  >
                    <i className="fa-solid fa-pen"></i> Editar
                  </button>
                  <button
                    className="btn btn-outline btn-success-ghost"
                    onClick={handleFinalizar}
                  >
                    <i className="fa-solid fa-check"></i> Finalizar
                  </button>
                  {esAdministrador && (
                    <button
                      className="btn btn-outline btn-danger-ghost"
                      onClick={handleDelete}
                    >
                      <i className="fa-solid fa-trash"></i> Eliminar
                    </button>
                  )}
                </div>
              ) : (
                selected.estado === ESTADO_FINALIZADA && (
                  <div
                    className="detail-actions"
                    style={{ color: "var(--gray-500)", fontSize: 13 }}
                  >
                    <i className="fa-solid fa-lock"></i> Recolección finalizada. No se
                    puede editar.
                    {esAdministrador && (
                      <button
                        className="btn btn-outline btn-danger-ghost"
                        style={{ marginLeft: "auto" }}
                        onClick={handleDelete}
                      >
                        <i className="fa-solid fa-trash"></i> Eliminar
                      </button>
                    )}
                  </div>
                )
              )}
            </div>
          )}
        </div>
      )}

      {modalMode === "create" && (
        <RecoleccionFormModal
          galpones={galpones}
          productos={productos}
          onClose={() => setModalMode(null)}
          onSubmit={handleCreate}
          onCreated={(id) => setSelectedId(id)}
        />
      )}
      {modalMode === "edit" && selected && (
        <RecoleccionFormModal
          galpones={galpones}
          productos={productos}
          initialData={selected}
          onClose={() => setModalMode(null)}
          onSubmit={handleUpdate}
        />
      )}
    </div>
  );
}
