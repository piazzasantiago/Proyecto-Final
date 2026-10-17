import { useEffect, useMemo, useState } from "react";
import {
  listProveedores,
  createProveedor,
  updateProveedor,
  deleteProveedor,
  altaProveedor,
  bajaProveedor,
} from "../api/proveedores";
import ProveedorFormModal from "../components/ProveedorFormModal";
import { useAuth } from "../context/AuthContext";

export default function ProveedoresPage() {
  const { esAdministrador } = useAuth();

  const [proveedores, setProveedores] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [estadoFilter, setEstadoFilter] = useState("");
  const [actionError, setActionError] = useState(null);
  const [modalMode, setModalMode] = useState(null); // null | "create" | "edit"

  async function fetchProveedores() {
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (search) params.search = search;
      if (estadoFilter) params.estado = estadoFilter;
      const data = await listProveedores(params);
      const lista = data.results ?? data;
      setProveedores(lista);
      if (!selectedId && lista.length > 0) setSelectedId(lista[0].id_proveedor);
    } catch {
      setError("No se pudo conectar con el servidor. ¿Está corriendo el backend en el puerto 8000?");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchProveedores();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, estadoFilter]);

  const selected = useMemo(
    () => proveedores.find((p) => p.id_proveedor === selectedId) || null,
    [proveedores, selectedId]
  );

  async function handleCreate(data) {
    const created = await createProveedor(data);
    setModalMode(null);
    await fetchProveedores();
    setSelectedId(created.id_proveedor);
  }

  async function handleUpdate(data) {
    const updated = await updateProveedor(selected.id_proveedor, data);
    setModalMode(null);
    await fetchProveedores();
    setSelectedId(updated.id_proveedor);
  }

  async function handleDelete() {
    if (!selected) return;
    if (!confirm(`¿Eliminar al proveedor "${selected.nombre}"? Esta acción no se puede deshacer.`)) return;
    setActionError(null);
    try {
      await deleteProveedor(selected.id_proveedor);
      setSelectedId(null);
      await fetchProveedores();
    } catch (err) {
      setActionError(
        err.status === 0
          ? "No se pudo conectar con el servidor."
          : err.message || "No se pudo eliminar el proveedor. Dalo de baja en su lugar."
      );
    }
  }

  async function cambiarEstado(accion) {
    if (!selected) return;
    setActionError(null);
    try {
      await accion(selected.id_proveedor);
      await fetchProveedores();
    } catch (err) {
      setActionError(err.message);
    }
  }

  return (
    <div className="page active" id="page-proveedores">
      <div className="page-header">
        <div>
          <h1>Proveedores</h1>
          <div className="desc">Proveedores de materias primas y lotes de gallinas.</div>
        </div>
        {esAdministrador && (
          <button className="btn btn-green" onClick={() => setModalMode("create")}>
            <i className="fa-solid fa-plus"></i> Nuevo proveedor
          </button>
        )}
      </div>

      <div className="toolbar">
        <div className="search-box">
          <i className="fa-solid fa-magnifying-glass"></i>
          <input
            type="text"
            placeholder="Buscar por nombre, CUIT, email, teléfono o dirección..."
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
      {loading && <div className="banner banner-loading">Cargando proveedores...</div>}

      {!loading && !error && (
        <div className="page-body-split">
          <div className="card-grid">
            {proveedores.length === 0 && (
              <div className="empty-state">
                {esAdministrador
                  ? 'No hay proveedores registrados todavía. Creá el primero con "Nuevo proveedor".'
                  : "No hay proveedores registrados."}
              </div>
            )}
            {proveedores.map((p) => (
              <div
                key={p.id_proveedor}
                className={`galpon-card ${p.id_proveedor === selectedId ? "card-selected" : ""}`}
                onClick={() => { setSelectedId(p.id_proveedor); setActionError(null); }}
              >
                <div className="gc-top">
                  <div className="gc-name" style={{ fontSize: "1rem", fontWeight: 600, color: "var(--gray-900)" }}>
                    {p.nombre}
                  </div>
                  <span className={`badge ${p.estado === "A" ? "badge-green" : "badge-red"}`}>
                    {p.estado_display}
                  </span>
                </div>
                <div className="gc-stats">
                  <div className="gc-stat"><i className="fa-solid fa-envelope"></i> {p.email}</div>
                  <div className="gc-stat"><i className="fa-solid fa-phone"></i> {p.telefono}</div>
                  {p.direccion && (
                    <div className="gc-stat"><i className="fa-solid fa-location-dot"></i> {p.direccion}</div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {selected && (
            <div className="detail-panel">
              <div className="detail-head">
                <div>
                  <h3>{selected.nombre}</h3>
                </div>
                <span className={`badge ${selected.estado === "A" ? "badge-green" : "badge-red"}`}>
                  {selected.estado_display}
                </span>
              </div>

              <div className="detail-body">
                <div className="detail-sec-title" style={{ marginTop: 0 }}>Datos del proveedor</div>
                <div className="detail-row"><span>Nombre</span><span>{selected.nombre}</span></div>
                <div className="detail-row">
                  <span>CUIT</span>
                  <span>{selected.cuit_formateado || "—"}</span>
                </div>
                <div className="detail-row"><span>Email</span><span>{selected.email}</span></div>
                <div className="detail-row"><span>Teléfono</span><span>{selected.telefono}</span></div>
                {/* Una dirección larga ocupa varias líneas: el título no se achica y el
                    texto queda alineado a la derecha como el resto de las filas. */}
                <div className="detail-row" style={{ gap: 16 }}>
                  <span style={{ flexShrink: 0 }}>Dirección</span>
                  <span style={{ textAlign: "right" }}>{selected.direccion || "—"}</span>
                </div>

                <div className="detail-sec-title">Compras recientes</div>
                <div className="empty-state" style={{ margin: "8px 0", fontSize: "0.85rem" }}>
                  El módulo de compras estará disponible próximamente.
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
                    <button className="btn btn-outline btn-warning-ghost" onClick={() => cambiarEstado(bajaProveedor)}>
                      <i className="fa-solid fa-ban"></i> Dar de baja
                    </button>
                  ) : (
                    <button className="btn btn-outline btn-success-ghost" onClick={() => cambiarEstado(altaProveedor)}>
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
        <ProveedorFormModal onClose={() => setModalMode(null)} onSubmit={handleCreate} />
      )}
      {modalMode === "edit" && selected && (
        <ProveedorFormModal
          initialData={selected}
          onClose={() => setModalMode(null)}
          onSubmit={handleUpdate}
        />
      )}
    </div>
  );
}
