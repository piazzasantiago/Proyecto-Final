import { useEffect, useState, useMemo } from "react";
import {
  listProductos,
  createProducto,
  updateProducto,
  deleteProducto,
  activarProducto,
  desactivarProducto,
} from "../api/productos";
import ProductoFormModal from "../components/ProductoFormModal";
import { useAuth } from "../context/AuthContext";

export default function ProductosPage() {
  const { esAdministrador } = useAuth();

  const [productos, setProductos] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [actionError, setActionError] = useState(null);
  const [estadoFilter, setEstadoFilter] = useState("");
  const [modalMode, setModalMode] = useState(null); // null | "create" | "edit"

  async function fetchProductos() {
    setLoading(true);
    setError(null);
    try {
      const params = {};
      if (search) params.search = search;
      if (estadoFilter) params.estado = estadoFilter;
      const data = await listProductos(params);
      setProductos(data.results ?? data);
      if (!selectedId && (data.results ?? data).length > 0) {
        setSelectedId((data.results ?? data)[0].id_producto);
      }
    } catch {
      setError("No se pudo conectar con el servidor. ¿Está corriendo el backend en el puerto 8000?");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchProductos();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, estadoFilter]);

  const selected = useMemo(
    () => productos.find((p) => p.id_producto === selectedId) || null,
    [productos, selectedId]
  );

  async function handleCreate(data) {
    const created = await createProducto(data);
    setModalMode(null);
    await fetchProductos();
    setSelectedId(created.id_producto);
  }

  async function handleUpdate(data) {
    const updated = await updateProducto(selected.id_producto, data);
    setModalMode(null);
    await fetchProductos();
    setSelectedId(updated.id_producto);
  }

  async function handleDelete() {
    if (!selected) return;
    if (!confirm(`¿Eliminar el producto "${selected.producto}"? Esta acción no se puede deshacer.`)) return;
    setActionError(null);
    try {
      await deleteProducto(selected.id_producto);
      setSelectedId(null);
      await fetchProductos();
    } catch (err) {
      if (err.status === 0) {
        setActionError("No se pudo conectar con el servidor.");
      } else {
        setActionError(
          "No se puede eliminar el producto porque tiene registros asociados " +
          "(por ejemplo, líneas de recolección). Desactivalo en su lugar."
        );
      }
    }
  }

  async function handleDesactivar() {
    if (!selected) return;
    setActionError(null);
    try {
      await desactivarProducto(selected.id_producto);
      await fetchProductos();
    } catch (err) {
      setActionError(err.message);
    }
  }

  async function handleActivar() {
    if (!selected) return;
    setActionError(null);
    try {
      await activarProducto(selected.id_producto);
      await fetchProductos();
    } catch (err) {
      setActionError(err.message);
    }
  }

  return (
    <div className="page active" id="page-productos">
      <div className="page-header">
        <div>
          <h1>Productos</h1>
          <div className="desc">Administrá el catálogo de productos (huevos clasificados por tamaño) que se registran en cada recolección.</div>
        </div>
        {esAdministrador && (
          <button className="btn btn-green" onClick={() => setModalMode("create")}>
            <i className="fa-solid fa-plus"></i> Nuevo producto
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
      {loading && <div className="banner banner-loading">Cargando productos...</div>}

      {!loading && !error && (
        <div className="page-body-split">
          <div className="producto-grid">
            {productos.length === 0 && (
              <div className="empty-state">
                {esAdministrador
                  ? 'No hay productos registrados todavía. Creá el primero con "Nuevo producto".'
                  : "No hay productos registrados."}
              </div>
            )}
            {productos.map((p) => (
              <div
                key={p.id_producto}
                className={`producto-card ${p.id_producto === selectedId ? "card-selected" : ""}`}
                onClick={() => { setSelectedId(p.id_producto); setActionError(null); }}
              >
                <div className="pc-top">
                  <div className="pc-icon"><i className="fa-solid fa-egg"></i></div>
                  <span className={`badge ${p.estado === "A" ? "badge-green" : "badge-red"}`}>
                    {p.estado_display}
                  </span>
                </div>
                <div>
                  <div className="pc-name">{p.producto}</div>
                  {p.descripcion && <div className="pc-desc">{p.descripcion}</div>}
                </div>
                <div className="pc-stock">
                  <span className="pc-stock-value">{p.stock_actual}</span>
                  <span className="pc-stock-label">en stock</span>
                </div>
              </div>
            ))}
          </div>

          {selected && (
            <div className="detail-panel">
              <div className="detail-head">
                <div>
                  <h3>{selected.producto}</h3>
                </div>
                <span className={`badge ${selected.estado === "A" ? "badge-green" : "badge-red"}`}>
                  {selected.estado_display}
                </span>
              </div>
              <div className="detail-body">
                <div className="detail-sec-title" style={{ marginTop: 0 }}>Datos del producto</div>
                <div className="detail-row"><span>Nombre</span><span>{selected.producto}</span></div>
                <div className="detail-row"><span>Stock actual</span><span><strong>{selected.stock_actual}</strong></span></div>
                <div className="detail-row"><span>Stock inicial / ajuste</span><span>{selected.stock_inicial}</span></div>
                <div className="detail-row"><span>Recolectado (finalizadas)</span><span>{selected.stock_recolectado}</span></div>
                <div className="detail-row"><span>Descartado (finalizados)</span><span>{selected.stock_descartado}</span></div>
                <div className="detail-row"><span>Salidas (finalizadas)</span><span>{selected.stock_salidas}</span></div>
                {selected.descripcion && (
                  <div className="detail-row" style={{ borderBottom: "none", alignItems: "flex-start", flexDirection: "column", gap: 4 }}>
                    <span>Descripción</span>
                    <span style={{ fontWeight: 500, color: "var(--gray-700)", textAlign: "left" }}>
                      {selected.descripcion}
                    </span>
                  </div>
                )}
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
                      <i className="fa-solid fa-ban"></i> Desactivar
                    </button>
                  ) : (
                    <button className="btn btn-outline btn-success-ghost" onClick={handleActivar}>
                      <i className="fa-solid fa-rotate-left"></i> Activar producto
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
        <ProductoFormModal onClose={() => setModalMode(null)} onSubmit={handleCreate} />
      )}
      {modalMode === "edit" && selected && (
        <ProductoFormModal initialData={selected} onClose={() => setModalMode(null)} onSubmit={handleUpdate} />
      )}
    </div>
  );
}
