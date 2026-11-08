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
import ComprasRecientes from "../components/ComprasRecientes";
import { useAuth } from "../context/AuthContext";
import { useDialogo } from "../components/Dialogo";
import Paginacion, { useTamanoPagina } from "../components/Paginacion";
import AuditoriaBoton from "../components/AuditoriaBoton";
import { EsqueletoTarjetas } from "../components/Esqueleto";

import AyudaSeccion from "../components/AyudaSeccion";
import CerrarDetalle from "../components/CerrarDetalle";
export default function ProveedoresPage() {
  const { confirmar, avisar } = useDialogo();
  const { esAdministrador } = useAuth();

  const [proveedores, setProveedores] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useTamanoPagina("proveedores", 16);
  const [count, setCount] = useState(0);
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
      const params = { page, page_size: pageSize };
      if (search) params.search = search;
      if (estadoFilter) params.estado = estadoFilter;
      const data = await listProveedores(params);
      const lista = data.results ?? data;
      setProveedores(lista);
      setCount(data.count ?? lista.length);
      // Si el elemento seleccionado no está en esta página, se muestra el primero.
      setSelectedId((actual) =>
        lista.some((x) => x.id_proveedor === actual) ? actual : (lista[0]?.id_proveedor ?? null)
      );
    } catch (err) {
      if (err.status === 404 && page > 1) {
        // La página quedó vacía (se eliminó el último registro de la última página).
        setPage(page - 1);
        return;
      }
      setError("No se pudo conectar con el servidor. ¿Está corriendo el backend en el puerto 8000?");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchProveedores();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, estadoFilter, page, pageSize]);

  /** Cambia un filtro: vuelve a la primera página. */
  function cambiarFiltro(setter) {
    return (valor) => {
      setter(valor);
      setPage(1);
    };
  }

  const selected = useMemo(
    () => proveedores.find((p) => p.id_proveedor === selectedId) || null,
    [proveedores, selectedId]
  );

  async function handleCreate(data) {
    const created = await createProveedor(data);
    setModalMode(null);
    if (page !== 1) {
      // El alta puede quedar en la primera página: se vuelve a ella (el efecto recarga).
      setSelectedId(created.id_proveedor);
      setPage(1);
      return;
    }
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
    if (!(await confirmar({ titulo: "Eliminar proveedor", mensaje: `¿Eliminar al proveedor "${selected.nombre}"? Esta acción no se puede deshacer.`, confirmarTexto: "Eliminar", peligro: true }))) return;
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
          <div className="page-titulo"><h1>Proveedores</h1><AyudaSeccion seccion="proveedores" /></div>
          <div className="desc">Proveedores de materias primas y lotes de gallinas.</div>
        </div>
        {esAdministrador && (
          <button className="btn btn-green" data-tutorial="sec-nuevo" onClick={() => setModalMode("create")}>
            <i className="fa-solid fa-plus"></i> Nuevo proveedor
          </button>
        )}
      </div>

      <div className="toolbar" data-tutorial="sec-filtros">
        <div className="search-box">
          <i className="fa-solid fa-magnifying-glass"></i>
          <input
            type="text"
            placeholder="Buscar por nombre, CUIT, email, teléfono o dirección..."
            value={search}
            onChange={(e) => cambiarFiltro(setSearch)(e.target.value)}
          />
        </div>
        <select className="select-filter" value={estadoFilter} onChange={(e) => cambiarFiltro(setEstadoFilter)(e.target.value)}>
          <option value="">Estado: Todos</option>
          <option value="A">Activo</option>
          <option value="I">Inactivo</option>
        </select>
      </div>

      {error && <div className="banner banner-error">{error}</div>}
      {loading && <EsqueletoTarjetas texto="Cargando proveedores..." />}

      {!loading && !error && (
        <div className="page-body-split">
          <div className="card-column">
            <div className="card-grid" data-tutorial="sec-lista">
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
                  data-tutorial-fila=""
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
                    <div className="gc-stat"><i className="fa-solid fa-envelope"></i><span className="gc-stat-texto" title={p.email}>{p.email}</span></div>
                    <div className="gc-stat"><i className="fa-solid fa-phone"></i> {p.telefono}</div>
                    {p.direccion && (
                      <div className="gc-stat"><i className="fa-solid fa-location-dot"></i> {p.direccion}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
            <Paginacion
              page={page}
              count={count}
              pageSize={pageSize}
              onChange={setPage}
              onPageSizeChange={(n) => {
                setPageSize(n);
                setPage(1);
              }}
            />
          </div>

          {selected && (
            <div key={selectedId} className="detail-panel" data-tutorial="sec-detalle">
              <CerrarDetalle />
              <div className="detail-head">
                <div>
                  <h3>{selected.nombre}</h3>
                </div>
                <span className={`badge ${selected.estado === "A" ? "badge-green" : "badge-red"}`}>
                  {selected.estado_display}
                </span>
                <AuditoriaBoton auditoria={selected.auditoria} />
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
                <ComprasRecientes proveedorId={selected.id_proveedor} />
              </div>

              {actionError && (
                <div className="banner banner-error" style={{ margin: "0 20px 0" }}>
                  <i className="fa-solid fa-triangle-exclamation" style={{ marginRight: 6 }}></i>
                  {actionError}
                </div>
              )}
              {esAdministrador && (
                <div className="detail-actions" data-tutorial="sec-acciones">
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
