import { useEffect, useMemo, useState } from "react";
import { listCompras, deleteCompra, finalizarCompra } from "../api/compras";
import { listProveedores } from "../api/proveedores";
import { listMateriasPrimas } from "../api/materias-primas";
import CompraFormModal from "../components/CompraFormModal";
import { useAuth } from "../context/AuthContext";
import Paginacion, { useTamanoPagina } from "../components/Paginacion";
import { traerTodas } from "../api/paginado";

const ESTADO_PENDIENTE = "P";
const ESTADO_FINALIZADA = "F";
const CATEGORIA_LOTES = "L";

function formatFecha(iso) {
  if (!iso) return "—";
  const [y, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
}

function formatUsuario(c) {
  return c.usuario?.nombre_completo || c.usuario?.usuario || "—";
}

function formatNumero(valor) {
  const n = Number(valor);
  return Number.isNaN(n) ? "—" : n.toLocaleString("es-AR", { maximumFractionDigits: 2 });
}

function formatPrecio(valor) {
  const n = Number(valor);
  return Number.isNaN(n)
    ? "—"
    : n.toLocaleString("es-AR", {
        style: "currency",
        currency: "ARS",
        minimumFractionDigits: 2,
      });
}

export default function ComprasPage() {
  // Solo el administrador escribe; el rol Consulta únicamente lee.
  const { esAdministrador } = useAuth();

  const [compras, setCompras] = useState([]);
  const [proveedores, setProveedores] = useState([]);
  const [materiasPrimas, setMateriasPrimas] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useTamanoPagina("compras", 16);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [proveedorFilter, setProveedorFilter] = useState("");
  const [categoriaFilter, setCategoriaFilter] = useState("");
  const [estadoFilter, setEstadoFilter] = useState("");
  const [fechaDesde, setFechaDesde] = useState("");
  const [fechaHasta, setFechaHasta] = useState("");
  const [modalMode, setModalMode] = useState(null); // null | "create" | "edit"

  const hayFiltros = Boolean(
    search || proveedorFilter || categoriaFilter || estadoFilter || fechaDesde || fechaHasta
  );

  async function fetchCompras(seleccionar) {
    setLoading(true);
    setError(null);
    try {
      const params = { page, page_size: pageSize };
      if (search) params.search = search;
      if (proveedorFilter) params.id_proveedor = proveedorFilter;
      if (categoriaFilter) params.categoria = categoriaFilter;
      if (estadoFilter) params.estado = estadoFilter;
      if (fechaDesde) params.fecha_desde = fechaDesde;
      if (fechaHasta) params.fecha_hasta = fechaHasta;
      const data = await listCompras(params);
      const lista = data.results ?? data;
      setCompras(lista);
      setCount(data.count ?? lista.length);
      setSelectedId((actual) => {
        if (seleccionar) return seleccionar;
        if (actual && lista.some((c) => c.id_compra === actual)) return actual;
        return lista.length > 0 ? lista[0].id_compra : null;
      });
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
    fetchCompras();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, proveedorFilter, categoriaFilter, estadoFilter, fechaDesde, fechaHasta, page, pageSize]);

  // Catálogos para el formulario y los filtros: se cargan una vez.
  useEffect(() => {
    traerTodas(listProveedores, {}).then(setProveedores).catch(() => setProveedores([]));
    traerTodas(listMateriasPrimas, { estado: "A" })
      .then(setMateriasPrimas)
      .catch(() => setMateriasPrimas([]));
  }, []);

  const selected = useMemo(
    () => compras.find((c) => c.id_compra === selectedId) || null,
    [compras, selectedId]
  );

  /** Cambia un filtro: vuelve a la primera página. */
  function cambiarFiltro(setter) {
    return (valor) => {
      setter(valor);
      setPage(1);
    };
  }

  function limpiarFiltros() {
    setPage(1);
    setSearch("");
    setProveedorFilter("");
    setCategoriaFilter("");
    setEstadoFilter("");
    setFechaDesde("");
    setFechaHasta("");
  }

  async function handleSaved(result) {
    const eraAlta = modalMode === "create";
    setModalMode(null);
    if (eraAlta && page !== 1) {
      // El alta queda primera: se vuelve a la página 1 (el efecto recarga la lista).
      setSelectedId(result?.id_compra ?? null);
      setPage(1);
      return;
    }
    await fetchCompras(result?.id_compra);
  }

  async function handleDelete() {
    if (!selected) return;
    if (
      !confirm(
        `¿Eliminar la compra ${selected.nro_factura}? Esta acción no se puede deshacer.`
      )
    )
      return;
    try {
      await deleteCompra(selected.id_compra);
      setSelectedId(null);
      await fetchCompras();
    } catch (err) {
      alert(err.message || "No se pudo eliminar la compra.");
    }
  }

  async function handleFinalizar() {
    if (!selected) return;
    const efecto =
      selected.categoria === CATEGORIA_LOTES
        ? "Los lotes quedarán esperando que los asignes a un galpón."
        : "Se sumará al stock de cada materia prima.";
    if (
      !confirm(
        `¿Finalizar la compra ${selected.nro_factura}? No podrá editarse ni eliminarse después. ${efecto}`
      )
    )
      return;
    try {
      await finalizarCompra(selected.id_compra);
      await fetchCompras();
    } catch (err) {
      alert(err.message || "No se pudo finalizar la compra.");
    }
  }

  const esDeLotes = selected?.categoria === CATEGORIA_LOTES;

  return (
    <div className="page active" id="page-compras">
      <div className="page-header">
        <div>
          <h1>Compras</h1>
          <div className="desc">
            Registro de compras de materias primas y de lotes de gallinas a proveedores.
          </div>
        </div>
        {esAdministrador && (
          <button className="btn btn-green" onClick={() => setModalMode("create")}>
            <i className="fa-solid fa-plus"></i> Nueva compra
          </button>
        )}
      </div>

      <div className="toolbar">
        <div className="search-box">
          <i className="fa-solid fa-magnifying-glass"></i>
          <input
            type="text"
            placeholder="Buscar por Nº de factura..."
            value={search}
            onChange={(e) => cambiarFiltro(setSearch)(e.target.value)}
          />
        </div>
        <select
          className="select-filter"
          value={proveedorFilter}
          onChange={(e) => cambiarFiltro(setProveedorFilter)(e.target.value)}
        >
          <option value="">Proveedor: Todos</option>
          {proveedores.map((p) => (
            <option key={p.id_proveedor} value={p.id_proveedor}>
              {p.nombre}
            </option>
          ))}
        </select>
        <select
          className="select-filter"
          value={categoriaFilter}
          onChange={(e) => cambiarFiltro(setCategoriaFilter)(e.target.value)}
        >
          <option value="">Categoría: Todas</option>
          <option value="M">Materias primas</option>
          <option value="L">Lotes</option>
        </select>
        <select
          className="select-filter"
          value={estadoFilter}
          onChange={(e) => cambiarFiltro(setEstadoFilter)(e.target.value)}
        >
          <option value="">Estado: Todos</option>
          <option value={ESTADO_PENDIENTE}>Pendiente</option>
          <option value={ESTADO_FINALIZADA}>Finalizada</option>
        </select>
        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 14 }}>
          <span style={{ color: "var(--gray-500)" }}>Desde</span>
          <input
            type="date"
            className="filter-date"
            value={fechaDesde}
            max={fechaHasta || undefined}
            onChange={(e) => cambiarFiltro(setFechaDesde)(e.target.value)}
          />
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 14 }}>
          <span style={{ color: "var(--gray-500)" }}>Hasta</span>
          <input
            type="date"
            className="filter-date"
            value={fechaHasta}
            min={fechaDesde || undefined}
            onChange={(e) => cambiarFiltro(setFechaHasta)(e.target.value)}
          />
        </label>
        {hayFiltros && (
          <button className="btn btn-outline" onClick={limpiarFiltros}>
            <i className="fa-solid fa-xmark"></i> Limpiar
          </button>
        )}
      </div>

      {error && <div className="banner banner-error">{error}</div>}
      {loading && <div className="banner banner-loading">Cargando compras...</div>}

      {!loading && !error && (
        <div className="page-body-split">
          {/* ── Lista ─────────────────────────────────────────────────── */}
          <div className="list-panel">
            {compras.length === 0 ? (
              <div className="empty-state" style={{ padding: 24 }}>
                {hayFiltros
                  ? "Ninguna compra coincide con los filtros."
                  : esAdministrador
                  ? 'No hay compras registradas. Creá la primera con "Nueva compra".'
                  : "No hay compras disponibles."}
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Nº factura</th>
                    <th>Proveedor</th>
                    <th>Fecha</th>
                    <th>Categoría</th>
                    <th>Tipo</th>
                    <th>Estado</th>
                    <th>Cargada por</th>
                  </tr>
                </thead>
                <tbody>
                  {compras.map((c) => {
                    const isSel = c.id_compra === selectedId;
                    return (
                      <tr
                        key={c.id_compra}
                        onClick={() => setSelectedId(c.id_compra)}
                        style={{
                          cursor: "pointer",
                          background: isSel ? "var(--green-50, #f0fdf4)" : undefined,
                        }}
                      >
                        <td>{c.nro_factura}</td>
                        <td>{c.proveedor?.nombre ?? "—"}</td>
                        <td>{formatFecha(c.fecha)}</td>
                        <td>{c.categoria_display}</td>
                        <td>{c.tipo_display}</td>
                        <td>
                          <span
                            className={`badge ${
                              c.estado === ESTADO_PENDIENTE ? "badge-gold" : "badge-green"
                            }`}
                          >
                            {c.estado_display}
                          </span>
                        </td>
                        <td>{formatUsuario(c)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
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

          {/* ── Panel de detalle ────────────────────────────────────── */}
          {selected && (
            <div className="detail-panel">
              <div className="detail-head">
                <div>
                  <h3>Compra {selected.nro_factura}</h3>
                  <div className="sub">
                    {selected.proveedor?.nombre} · {formatFecha(selected.fecha)}
                  </div>
                </div>
                <span
                  className={`badge ${
                    selected.estado === ESTADO_PENDIENTE ? "badge-gold" : "badge-green"
                  }`}
                >
                  {selected.estado_display}
                </span>
              </div>

              <div className="detail-body">
                <div className="detail-sec-title" style={{ marginTop: 0 }}>
                  Datos de la compra
                </div>
                <div className="detail-row">
                  <span>Proveedor</span>
                  <span>{selected.proveedor?.nombre ?? "—"}</span>
                </div>
                <div className="detail-row">
                  <span>Nº factura</span>
                  <span>{selected.nro_factura}</span>
                </div>
                <div className="detail-row">
                  <span>Fecha</span>
                  <span>{formatFecha(selected.fecha)}</span>
                </div>
                <div className="detail-row">
                  <span>Categoría</span>
                  <span>{selected.categoria_display}</span>
                </div>
                <div className="detail-row">
                  <span>Tipo</span>
                  <span>{selected.tipo_display}</span>
                </div>
                <div className="detail-row">
                  <span>Estado</span>
                  <span>{selected.estado_display}</span>
                </div>
                <div className="detail-row">
                  <span>Cargada por</span>
                  <span>{formatUsuario(selected)}</span>
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
                      style={{ fontWeight: 500, color: "var(--gray-700)", textAlign: "left" }}
                    >
                      {selected.observaciones}
                    </span>
                  </div>
                )}

                <div className="detail-sec-title">Detalle</div>
                <table className="plan-table">
                  <thead>
                    <tr>
                      <th>{esDeLotes ? "Concepto" : "Materia prima"}</th>
                      <th style={{ textAlign: "right" }}>Cant.</th>
                      <th style={{ textAlign: "right" }}>P. unit.</th>
                      <th style={{ textAlign: "right" }}>Subtotal</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(selected.lineas ?? []).map((l) => (
                      <tr key={l.id_linea_compra}>
                        <td>
                          {esDeLotes ? (
                            <>
                              Lote de gallinas
                              <div style={{ fontSize: 12, color: "var(--gray-500)" }}>
                                {l.lote_codigo
                                  ? `Asignado: ${l.lote_codigo}`
                                  : selected.estado === ESTADO_FINALIZADA
                                  ? "Pendiente de asignar a un galpón"
                                  : "Sin asignar"}
                              </div>
                            </>
                          ) : (
                            l.materia_prima_nombre
                          )}
                        </td>
                        <td style={{ textAlign: "right" }}>
                          {formatNumero(l.cantidad)}
                          {esDeLotes ? " aves" : ` ${l.materia_prima_unidad ?? ""}`}
                        </td>
                        <td style={{ textAlign: "right" }}>{formatPrecio(l.precio_unitario)}</td>
                        <td style={{ textAlign: "right" }}>{formatPrecio(l.subtotal)}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr>
                      <td colSpan={3} style={{ textAlign: "right", fontWeight: 600 }}>
                        Total
                      </td>
                      <td style={{ textAlign: "right", fontWeight: 600 }}>
                        {formatPrecio(selected.total)}
                      </td>
                    </tr>
                  </tfoot>
                </table>

                <div style={{ marginTop: 12, fontSize: 13, color: "var(--gray-500)" }}>
                  <i className="fa-solid fa-circle-info"></i>{" "}
                  {selected.estado === ESTADO_FINALIZADA
                    ? esDeLotes
                      ? "Compra finalizada: los lotes se asignan a un galpón desde Lotes de gallinas."
                      : "Compra finalizada: ya se sumó al stock de cada materia prima."
                    : esDeLotes
                    ? "Al finalizarla, los lotes quedarán esperando que los asignes a un galpón."
                    : "Al finalizarla se sumará al stock de cada materia prima."}
                </div>
              </div>

              {/* Una compra finalizada ya hizo efecto: queda de solo lectura y no
                  se puede eliminar. */}
              {selected.estado === ESTADO_PENDIENTE && esAdministrador ? (
                <div className="detail-actions" style={{ flexWrap: "wrap" }}>
                  <button className="btn btn-outline" onClick={() => setModalMode("edit")}>
                    <i className="fa-solid fa-pen"></i> Editar
                  </button>
                  <button
                    className="btn btn-outline btn-success-ghost"
                    onClick={handleFinalizar}
                  >
                    <i className="fa-solid fa-check"></i> Finalizar
                  </button>
                  <button className="btn btn-outline btn-danger-ghost" onClick={handleDelete}>
                    <i className="fa-solid fa-trash"></i> Eliminar
                  </button>
                </div>
              ) : (
                selected.estado === ESTADO_FINALIZADA && (
                  <div className="detail-actions" style={{ color: "var(--gray-500)", fontSize: 13 }}>
                    <i className="fa-solid fa-lock"></i> Compra finalizada. No se puede editar
                    ni eliminar.
                  </div>
                )
              )}
            </div>
          )}
        </div>
      )}

      {modalMode === "create" && (
        <CompraFormModal
          proveedores={proveedores}
          materiasPrimas={materiasPrimas}
          onClose={() => setModalMode(null)}
          onSubmit={handleSaved}
        />
      )}
      {modalMode === "edit" && selected && (
        <CompraFormModal
          proveedores={proveedores}
          materiasPrimas={materiasPrimas}
          initialData={selected}
          onClose={() => setModalMode(null)}
          onSubmit={handleSaved}
        />
      )}
    </div>
  );
}
