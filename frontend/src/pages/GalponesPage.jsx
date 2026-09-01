import { useEffect, useState, useMemo } from "react";
import { listGalpones, createGalpon, updateGalpon, deleteGalpon } from "../api/galpones";
import GalponFormModal from "../components/GalponFormModal";

// El modelo solo tiene idGalpon (PK numérica) y galpon (nombre); "G-01"
// es puramente una etiqueta visual derivada del id real, no un campo aparte.
function formatCodigo(id) {
  return `G-${String(id).padStart(2, "0")}`;
}

export default function GalponesPage() {
  const [galpones, setGalpones] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [estadoFilter, setEstadoFilter] = useState("");
  const [modalMode, setModalMode] = useState(null); // null | "create" | "edit"

  async function fetchGalpones() {
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (search) params.search = search;
      if (estadoFilter) params.estado = estadoFilter;
      const data = await listGalpones(params);
      setGalpones(data.results ?? data);
      if (!selectedId && (data.results ?? data).length > 0) {
        setSelectedId((data.results ?? data)[0].id_galpon);
      }
    } catch {
      setError("No se pudo conectar con el servidor. ¿Está corriendo el backend en el puerto 8000?");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchGalpones();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, estadoFilter]);

  const selected = useMemo(
    () => galpones.find((g) => g.id_galpon === selectedId) || null,
    [galpones, selectedId]
  );

  async function handleCreate(data) {
    const created = await createGalpon(data);
    setModalMode(null);
    await fetchGalpones();
    setSelectedId(created.id_galpon);
  }

  async function handleUpdate(data) {
    const updated = await updateGalpon(selected.id_galpon, data);
    setModalMode(null);
    await fetchGalpones();
    setSelectedId(updated.id_galpon);
  }

  async function handleDelete() {
    if (!selected) return;
    if (!confirm(`¿Eliminar el galpón "${selected.galpon}"? Esta acción no se puede deshacer.`)) return;
    await deleteGalpon(selected.id_galpon);
    setSelectedId(null);
    await fetchGalpones();
  }

  return (
    <div className="page active" id="page-galpones">
      <div className="page-header">
        <div>
          <h1>Galpones</h1>
          <div className="desc">Administrá las instalaciones donde se alojan los lotes de gallinas ponedoras.</div>
        </div>
        <button className="btn btn-green" onClick={() => setModalMode("create")}>
          <i className="fa-solid fa-plus"></i> Nuevo galpón
        </button>
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
      {loading && <div className="banner banner-loading">Cargando galpones...</div>}

      {!loading && !error && (
        <div className="page-body-split">
          <div className="card-grid">
            {galpones.length === 0 && (
              <div className="empty-state">No hay galpones registrados todavía. Creá el primero con "Nuevo galpón".</div>
            )}
            {galpones.map((g) => (
              <div
                key={g.id_galpon}
                className={`galpon-card ${g.id_galpon === selectedId ? "card-selected" : ""}`}
                onClick={() => setSelectedId(g.id_galpon)}
              >
                <div className="gc-top">
                  <div>
                    <div className="gc-code">{formatCodigo(g.id_galpon)}</div>
                    <div className="gc-name">{g.galpon}</div>
                  </div>
                  <span className={`badge ${g.estado === "A" ? "badge-green" : "badge-red"}`}>
                    {g.estado_display}
                  </span>
                </div>
                <div className="gc-stats">
                  <div className="gc-stat"><i className="fa-solid fa-kiwi-bird"></i> {g.capacidad.toLocaleString("es-AR")} aves</div>
                  <div className="gc-stat"><i className="fa-solid fa-ruler-combined"></i> {Number(g.superficie).toLocaleString("es-AR")} m²</div>
                  <div className="gc-stat"><i className="fa-solid fa-location-dot"></i> {Number(g.latitud).toFixed(4)}, {Number(g.longitud).toFixed(4)}</div>
                </div>
              </div>
            ))}
          </div>

          {selected && (
            <div className="detail-panel">
              <div className="detail-head">
                <div>
                  <h3>{formatCodigo(selected.id_galpon)} · {selected.galpon}</h3>
                </div>
                <span className={`badge ${selected.estado === "A" ? "badge-green" : "badge-red"}`}>
                  {selected.estado_display}
                </span>
              </div>
              <div className="detail-body">
                <div className="detail-sec-title" style={{ marginTop: 0 }}>Datos del galpón</div>
                <div className="detail-row"><span>Capacidad</span><span>{selected.capacidad.toLocaleString("es-AR")} aves</span></div>
                <div className="detail-row"><span>Superficie</span><span>{Number(selected.superficie).toLocaleString("es-AR")} m²</span></div>
                <div className="detail-row"><span>Latitud / Longitud</span><span>{selected.latitud} / {selected.longitud}</span></div>
                <div className="detail-row" style={{ borderBottom: "none", alignItems: "flex-start", flexDirection: "column", gap: 4 }}>
                  <span>Descripción</span>
                  <span style={{ fontWeight: 500, color: "var(--gray-700)", textAlign: "left" }}>
                    {selected.descripcion || "Sin descripción."}
                  </span>
                </div>
              </div>
              <div className="detail-actions">
                <button className="btn btn-outline" onClick={() => setModalMode("edit")}>
                  <i className="fa-solid fa-pen"></i> Editar
                </button>
                <button className="btn btn-outline btn-danger-ghost" onClick={handleDelete}>
                  <i className="fa-solid fa-trash"></i> Eliminar
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {modalMode === "create" && (
        <GalponFormModal onClose={() => setModalMode(null)} onSubmit={handleCreate} />
      )}
      {modalMode === "edit" && selected && (
        <GalponFormModal initialData={selected} onClose={() => setModalMode(null)} onSubmit={handleUpdate} />
      )}
    </div>
  );
}
