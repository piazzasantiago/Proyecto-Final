import { useEffect, useState, useMemo } from "react";
import { listGalpones, createGalpon, updateGalpon, deleteGalpon, altaGalpon, bajaGalpon } from "../api/galpones";
import GalponFormModal from "../components/GalponFormModal";
import { useAuth } from "../context/AuthContext";

// El modelo solo tiene idGalpon (PK numérica) y galpon (nombre); "G-01"
// es puramente una etiqueta visual derivada del id real, no un campo aparte.
function formatCodigo(id) {
  return `G-${String(id).padStart(2, "0")}`;
}

export default function GalponesPage() {
  const { esAdministrador, esOperario } = useAuth();

  const [galpones, setGalpones] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [deleteError, setDeleteError] = useState(null);
  // Por defecto, los operarios ven solo sus galpones activos; el resto de
  // los roles arranca sin filtro (ve todos, activos e inactivos).
  const [estadoFilter, setEstadoFilter] = useState(esOperario ? "A" : "");
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
    setDeleteError(null);
    try {
      await deleteGalpon(selected.id_galpon);
      setSelectedId(null);
      await fetchGalpones();
    } catch (err) {
      // err.status === 0 → sin red; cualquier otro error es casi siempre
      // el PROTECT de Django porque el galpón tiene lotes asociados.
      if (err.status === 0) {
        setDeleteError("No se pudo conectar con el servidor.");
      } else {
        setDeleteError(
          "No se puede eliminar el galpón porque tiene lotes asociados. " +
          "Finalizá o eliminá los lotes primero."
        );
      }
    }
  }

  async function handleBaja() {
    if (!selected) return;
    await bajaGalpon(selected.id_galpon);
    await fetchGalpones();
  }

  async function handleAlta() {
    if (!selected) return;
    await altaGalpon(selected.id_galpon);
    await fetchGalpones();
  }

  return (
    <div className="page active" id="page-galpones">
      <div className="page-header">
        <div>
          <h1>Galpones</h1>
          <div className="desc">Administrá las instalaciones donde se alojan los lotes de gallinas ponedoras.</div>
        </div>
        {esAdministrador && (
          <button className="btn btn-green" onClick={() => setModalMode("create")}>
            <i className="fa-solid fa-plus"></i> Nuevo galpón
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
      {loading && <div className="banner banner-loading">Cargando galpones...</div>}

      {!loading && !error && (
        <div className="page-body-split">
          <div className="card-grid">
            {galpones.length === 0 && (
              <div className="empty-state">
                {esAdministrador
                  ? 'No hay galpones registrados todavía. Creá el primero con "Nuevo galpón".'
                  : "No tenés galpones asignados."}
              </div>
            )}
            {galpones.map((g) => (
              <div
                key={g.id_galpon}
                className={`galpon-card ${g.id_galpon === selectedId ? "card-selected" : ""}`}
                onClick={() => { setSelectedId(g.id_galpon); setDeleteError(null); }}
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
                  {g.lote_actual ? (
                    <>
                      <div className="gc-stat"><i className="fa-solid fa-layer-group"></i> {g.lote_actual.codigo}</div>
                      <div className="gc-stat"><i className="fa-solid fa-chart-simple"></i> {g.lote_actual.estado_display}</div>
                    </>
                  ) : (
                    <div className="gc-stat gc-stat-muted"><i className="fa-solid fa-layer-group"></i> Sin lote asignado</div>
                  )}
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
                {selected.descripcion && (
                  <div className="detail-row" style={{ borderBottom: "none", alignItems: "flex-start", flexDirection: "column", gap: 4 }}>
                    <span>Descripción</span>
                    <span style={{ fontWeight: 500, color: "var(--gray-700)", textAlign: "left" }}>
                      {selected.descripcion}
                    </span>
                  </div>
                )}

                {/* Lote actual */}
                <div className="detail-sec-title">Lote actual</div>
                {selected.lote_actual ? (
                  <>
                    <div className="detail-row"><span>Código</span><span>{selected.lote_actual.codigo}</span></div>
                    <div className="detail-row"><span>Etapa</span><span>{selected.lote_actual.estado_display}</span></div>
                    <div className="detail-row"><span>Cantidad actual</span><span>{selected.lote_actual.cantidad_actual.toLocaleString("es-AR")} aves</span></div>
                  </>
                ) : (
                  <div className="form-hint" style={{ marginBottom: 10 }}>
                    Este galpón no tiene un lote activo.
                  </div>
                )}

                {/* Operarios asignados */}
                {selected.operarios && selected.operarios.length > 0 && (
                  <>
                    <div className="detail-sec-title">Operarios asignados</div>
                    <div className="chip-group">
                      {selected.operarios.map((op) => (
                        <span key={op.id_usuario} className="chip">
                          <i className="fa-solid fa-user"></i> {op.nombre_completo}
                        </span>
                      ))}
                    </div>
                  </>
                )}
              </div>

              {deleteError && (
                <div className="banner banner-error" style={{ margin: "0 20px 0" }}>
                  <i className="fa-solid fa-triangle-exclamation" style={{ marginRight: 6 }}></i>
                  {deleteError}
                </div>
              )}
              {esAdministrador && (
                <div className="detail-actions">
                  <button className="btn btn-outline" onClick={() => setModalMode("edit")}>
                    <i className="fa-solid fa-pen"></i> Editar
                  </button>
                  {selected.estado === "A" ? (
                    <button className="btn btn-outline btn-warning-ghost" onClick={handleBaja}>
                      <i className="fa-solid fa-ban"></i> Dar de baja
                    </button>
                  ) : (
                    <button className="btn btn-outline btn-success-ghost" onClick={handleAlta}>
                      <i className="fa-solid fa-rotate-left"></i> Activar galpón
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
        <GalponFormModal onClose={() => setModalMode(null)} onSubmit={handleCreate} />
      )}
      {modalMode === "edit" && selected && (
        <GalponFormModal initialData={selected} onClose={() => setModalMode(null)} onSubmit={handleUpdate} />
      )}
    </div>
  );
}
