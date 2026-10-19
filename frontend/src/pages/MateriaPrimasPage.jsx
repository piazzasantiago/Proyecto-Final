import { useEffect, useState, useMemo } from "react";
import {
  listMateriasPrimas,
  createMateriaPrima,
  updateMateriaPrima,
  deleteMateriaPrima,
  activarMateriaPrima,
  desactivarMateriaPrima,
} from "../api/materias-primas";
import MateriaPrimaFormModal from "../components/MateriaPrimaFormModal";
import { useAuth } from "../context/AuthContext";

export default function MateriaPrimasPage() {
  const { esAdministrador } = useAuth();

  const [materias, setMaterias] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [actionError, setActionError] = useState(null);
  const [estadoFilter, setEstadoFilter] = useState("");
  const [modalMode, setModalMode] = useState(null); // null | "create" | "edit"

  async function fetchMaterias() {
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (search) params.search = search;
      if (estadoFilter) params.estado = estadoFilter;
      const data = await listMateriasPrimas(params);
      setMaterias(data.results ?? data);
      if (!selectedId && (data.results ?? data).length > 0) {
        setSelectedId((data.results ?? data)[0].id_materia_prima);
      }
    } catch {
      setError("No se pudo conectar con el servidor. ¿Está corriendo el backend en el puerto 8000?");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchMaterias();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, estadoFilter]);

  const selected = useMemo(
    () => materias.find((m) => m.id_materia_prima === selectedId) || null,
    [materias, selectedId]
  );

  async function handleCreate(data) {
    const created = await createMateriaPrima(data);
    setModalMode(null);
    await fetchMaterias();
    setSelectedId(created.id_materia_prima);
  }

  async function handleUpdate(data) {
    const updated = await updateMateriaPrima(selected.id_materia_prima, data);
    setModalMode(null);
    await fetchMaterias();
    setSelectedId(updated.id_materia_prima);
  }

  async function handleDelete() {
    if (!selected) return;
    if (!confirm(`¿Eliminar la materia prima "${selected.materia_prima}"? Esta acción no se puede deshacer.`)) return;
    setActionError(null);
    try {
      await deleteMateriaPrima(selected.id_materia_prima);
      setSelectedId(null);
      await fetchMaterias();
    } catch (err) {
      if (err.status === 0) {
        setActionError("No se pudo conectar con el servidor.");
      } else {
        setActionError("No se puede eliminar la materia prima porque tiene registros asociados. Desactivala en su lugar.");
      }
    }
  }

  async function handleDesactivar() {
    if (!selected) return;
    setActionError(null);
    try {
      await desactivarMateriaPrima(selected.id_materia_prima);
      await fetchMaterias();
    } catch (err) {
      setActionError(err.message);
    }
  }

  async function handleActivar() {
    if (!selected) return;
    setActionError(null);
    try {
      await activarMateriaPrima(selected.id_materia_prima);
      await fetchMaterias();
    } catch (err) {
      setActionError(err.message);
    }
  }

  return (
    <div className="page active" id="page-materias-primas">
      <div className="page-header">
        <div>
          <h1>Materias Primas</h1>
          <div className="desc">
            Administrá el catálogo de materias primas (insumos y consumibles) utilizadas en los galpones.
          </div>
        </div>
        {esAdministrador && (
          <button className="btn btn-green" onClick={() => setModalMode("create")}>
            <i className="fa-solid fa-plus"></i> Nueva materia prima
          </button>
        )}
      </div>

      <div className="toolbar">
        <div className="search-box">
          <i className="fa-solid fa-magnifying-glass"></i>
          <input
            type="text"
            placeholder="Buscar por nombre o descripción..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select className="select-filter" value={estadoFilter} onChange={(e) => setEstadoFilter(e.target.value)}>
          <option value="">Estado: Todos</option>
          <option value="A">Activo</option>
          <option value="I">Inactivo</option>
        </select>
      </div>

      {error && <div className="banner banner-error">{error}</div>}
      {loading && <div className="banner banner-loading">Cargando materias primas...</div>}

      {!loading && !error && (
        <div className="page-body-split">
          <div className="card-grid">
            {materias.length === 0 && (
              <div className="empty-state">
                {esAdministrador
                  ? 'No hay materias primas registradas todavía. Creá la primera con "Nueva materia prima".'
                  : "No hay materias primas registradas."}
              </div>
            )}
            {materias.map((m) => {
              const stockBajo = Number(m.stock_actual) < Number(m.stock_minimo);
              return (
                <div
                  key={m.id_materia_prima}
                  className={`galpon-card ${m.id_materia_prima === selectedId ? "card-selected" : ""}`}
                  onClick={() => { setSelectedId(m.id_materia_prima); setActionError(null); }}
                >
                  <div className="gc-top">
                    <div>
                      <div className="gc-name" style={{ fontSize: "1rem", fontWeight: 600, color: "var(--gray-900)" }}>{m.materia_prima}</div>
                    </div>
                    <span className={`badge ${m.estado === "A" ? "badge-green" : "badge-red"}`}>
                      {m.estado_display}
                    </span>
                  </div>
                  <div className="gc-stats">
                    <div className="gc-stat">
                      <i className="fa-solid fa-cubes-stacked"></i> Stock actual: <strong>{m.stock_actual} {m.unidad}</strong>
                    </div>
                    <div className="gc-stat">
                      <i className="fa-solid fa-arrow-down-to-line"></i> Mínimo: {m.stock_minimo} {m.unidad}
                    </div>
                    {stockBajo && (
                      <div className="gc-stat" style={{ color: "#c0392b", fontWeight: 500 }}>
                        <i className="fa-solid fa-triangle-exclamation"></i> Stock por debajo del mínimo
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {selected && (
            <div className="detail-panel">
              <div className="detail-head">
                <div>
                  <h3>{selected.materia_prima}</h3>
                </div>
                <span className={`badge ${selected.estado === "A" ? "badge-green" : "badge-red"}`}>
                  {selected.estado_display}
                </span>
              </div>

              {Number(selected.stock_actual) < Number(selected.stock_minimo) && (
                <div className="banner banner-error" style={{ margin: "0 20px 12px", borderRadius: 8 }}>
                  <i className="fa-solid fa-triangle-exclamation" style={{ marginRight: 6 }}></i>
                  Stock por debajo del mínimo ({selected.stock_actual} / {selected.stock_minimo} {selected.unidad})
                </div>
              )}

              <div className="detail-body">
                <div className="detail-sec-title" style={{ marginTop: 0 }}>Datos de la materia prima</div>
                <div className="detail-row">
                  <span>Nombre</span>
                  <span>{selected.materia_prima}</span>
                </div>
                <div className="detail-row">
                  <span>Unidad</span>
                  <span>{selected.unidad}</span>
                </div>
                <div className="detail-row">
                  <span>Stock mínimo</span>
                  <span>{selected.stock_minimo} {selected.unidad}</span>
                </div>
                <div className="detail-row">
                  <span>Stock actual</span>
                  <span>{selected.stock_actual} {selected.unidad}</span>
                </div>
                <div className="detail-row">
                  <span>Stock inicial / ajuste</span>
                  <span>{selected.stock_inicial} {selected.unidad}</span>
                </div>
                {selected.descripcion && (
                  <div className="detail-row" style={{ borderBottom: "none", alignItems: "flex-start", flexDirection: "column", gap: 4 }}>
                    <span>Descripción</span>
                    <span style={{ fontWeight: 500, color: "var(--gray-700)", textAlign: "left" }}>
                      {selected.descripcion}
                    </span>
                  </div>
                )}

                <div className="detail-sec-title">Movimientos de stock</div>
                <div className="detail-row">
                  <span>Comprado (compras finalizadas)</span>
                  <span>{selected.stock_compras} {selected.unidad}</span>
                </div>
              </div>

              {actionError && (
                <div className="banner banner-error" style={{ margin: "0 20px 0" }}>
                  <i className="fa-solid fa-triangle-exclamation" style={{ marginRight: 6 }}></i>
                  {actionError}
                </div>
              )}
              {esAdministrador && (
                <div className="detail-actions">
                  <button className="btn btn-outline" onClick={() => setModalMode("edit")}>
                    <i className="fa-solid fa-pen"></i> Editar
                  </button>
                  {selected.estado === "A" ? (
                    <button className="btn btn-outline btn-warning-ghost" onClick={handleDesactivar}>
                      <i className="fa-solid fa-ban"></i> Dar de baja
                    </button>
                  ) : (
                    <button className="btn btn-outline btn-success-ghost" onClick={handleActivar}>
                      <i className="fa-solid fa-rotate-left"></i> Dar de alta
                    </button>
                  )}
                  <button className="btn btn-outline btn-danger-ghost" onClick={handleDelete}>
                    <i className="fa-solid fa-trash"></i> Eliminar
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {modalMode === "create" && (
        <MateriaPrimaFormModal onClose={() => setModalMode(null)} onSubmit={handleCreate} />
      )}
      {modalMode === "edit" && selected && (
        <MateriaPrimaFormModal
          initialData={selected}
          onClose={() => setModalMode(null)}
          onSubmit={handleUpdate}
        />
      )}
    </div>
  );
}
