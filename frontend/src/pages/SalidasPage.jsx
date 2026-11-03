import { useEffect, useMemo, useState } from "react";
import { listSalidas, deleteSalida, finalizarSalida } from "../api/salidas";
import { listProductos } from "../api/productos";
import SalidaFormModal from "../components/SalidaFormModal";
import { useAuth } from "../context/AuthContext";
import { useDialogo } from "../components/Dialogo";
import Paginacion, { useTamanoPagina } from "../components/Paginacion";
import { traerTodas } from "../api/paginado";
import AuditoriaBoton from "../components/AuditoriaBoton";
import useAtajoAlta from "../components/useAtajoAlta";
import { EsqueletoTabla } from "../components/Esqueleto";

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

function formatUsuario(s) {
  return s.usuario?.nombre_completo || s.usuario?.usuario || "—";
}

function formatCantidad(valor) {
  const n = Number(valor);
  return Number.isNaN(n) ? "—" : n.toLocaleString("es-AR", { maximumFractionDigits: 0 });
}

function totalUnidades(s) {
  return (s.lineas ?? []).reduce((acc, l) => acc + Number(l.cantidad || 0), 0);
}

export default function SalidasPage() {
  const { confirmar, avisar } = useDialogo();
  const { esAdministrador, esOperario } = useAuth();
  const puedeEscribir = esAdministrador || esOperario;

  const [salidas, setSalidas] = useState([]);
  const [productos, setProductos] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useTamanoPagina("salidas", 16);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [fechaDesde, setFechaDesde] = useState("");
  const [fechaHasta, setFechaHasta] = useState("");
  const [productoFilter, setProductoFilter] = useState("");
  const [estadoFilter, setEstadoFilter] = useState("");
  // Atajos del panel principal: abrir la sección con el filtro de estado ya puesto.
  useAtajoAlta(null, { estado: setEstadoFilter });
  const [modalMode, setModalMode] = useState(null); // null | "create" | "edit"

  const hayFiltros = Boolean(fechaDesde || fechaHasta || productoFilter || estadoFilter);

  async function fetchSalidas(seleccionar) {
    setLoading(true);
    setError(null);
    try {
      const params = { page, page_size: pageSize };
      if (fechaDesde) params.fecha_desde = fechaDesde;
      if (fechaHasta) params.fecha_hasta = fechaHasta;
      if (productoFilter) params.id_producto = productoFilter;
      if (estadoFilter) params.estado = estadoFilter;
      const data = await listSalidas(params);
      const lista = data.results ?? data;
      setSalidas(lista);
      setCount(data.count ?? lista.length);
      setSelectedId((actual) => {
        if (seleccionar) return seleccionar;
        if (actual && lista.some((s) => s.id_salida === actual)) return actual;
        return lista.length > 0 ? lista[0].id_salida : null;
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
    fetchSalidas();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fechaDesde, fechaHasta, productoFilter, estadoFilter, page, pageSize]);

  // Catálogo de productos para el formulario y el filtro: se carga una vez.
  useEffect(() => {
    refrescarStock();
  }, []);

  const selected = useMemo(
    () => salidas.find((s) => s.id_salida === selectedId) || null,
    [salidas, selectedId]
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
    setFechaDesde("");
    setFechaHasta("");
    setProductoFilter("");
    setEstadoFilter("");
  }

  // Finalizar una salida cambia el stock de los productos, así que se vuelve a
  // pedir el catálogo que lo muestra.
  async function refrescarStock() {
    try {
      setProductos(await traerTodas(listProductos, {}));
    } catch {
      /* se mantiene el último stock conocido */
    }
  }

  async function handleSaved(result) {
    const eraAlta = modalMode === "create";
    setModalMode(null);
    if (eraAlta && page !== 1) {
      // El alta queda primera: se vuelve a la página 1 (el efecto recarga la lista).
      setSelectedId(result?.id_salida ?? null);
      setPage(1);
      return;
    }
    await fetchSalidas(result?.id_salida);
  }

  async function handleDelete() {
    if (!selected) return;
    if (
      !(await confirmar({
        titulo: "Eliminar salida",
        mensaje: `¿Eliminar la salida del ${formatFecha(selected.fecha)}? Esta acción no se puede deshacer.`,
        confirmarTexto: "Eliminar",
        peligro: true,
      }))
    )
      return;
    try {
      await deleteSalida(selected.id_salida);
      setSelectedId(null);
      await fetchSalidas();
    } catch (err) {
      await avisar({ titulo: "No se pudo eliminar la salida", mensaje: err.message });
    }
  }

  async function handleFinalizar() {
    if (!selected) return;
    if (
      !(await confirmar({
        titulo: "Finalizar salida",
        mensaje: `¿Finalizar la salida del ${formatFecha(selected.fecha)}? No podrá editarse después. ` +
          "Se descontará del stock de cada producto.",
        confirmarTexto: "Finalizar",
        peligro: false,
      }))
    )
      return;
    try {
      await finalizarSalida(selected.id_salida);
      await fetchSalidas();
      await refrescarStock();
    } catch (err) {
      await avisar({ titulo: "No se pudo finalizar la salida", mensaje: err.message });
    }
  }

  // Con auditoría disponible (Administrador y Consulta) la columna de usuario es opcional y se suma el ojito.
  const conAuditoria = salidas.some((x) => x.auditoria);

  return (
    <div className="page active" id="page-salidas">
      <div className="page-header">
        <div>
          <h1>Salidas</h1>
          <div className="desc">
            Productos que salen de la granja (por ejemplo, el camión que se lleva los huevos
            destinados a la venta).
          </div>
        </div>
        {puedeEscribir && (
          <button className="btn btn-green" onClick={() => setModalMode("create")}>
            <i className="fa-solid fa-plus"></i> Nueva salida
          </button>
        )}
      </div>

      {/* Filtros: fechas, producto y estado */}
      <div className="toolbar">
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
        <select
          className="select-filter"
          value={productoFilter}
          onChange={(e) => cambiarFiltro(setProductoFilter)(e.target.value)}
        >
          <option value="">Producto: Todos</option>
          {productos.map((p) => (
            <option key={p.id_producto} value={p.id_producto}>
              {p.producto}
              {p.estado === "I" ? " (inactivo)" : ""}
            </option>
          ))}
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
        {hayFiltros && (
          <button className="btn btn-outline" onClick={limpiarFiltros}>
            <i className="fa-solid fa-xmark"></i> Limpiar
          </button>
        )}
      </div>

      {error && <div className="banner banner-error">{error}</div>}
      {loading && <EsqueletoTabla texto="Cargando salidas..." />}

      {!loading && !error && (
        <div className="page-body-split">
          {/* ── Lista ─────────────────────────────────────────────────── */}
          <div className="list-panel">
            {salidas.length === 0 ? (
              <div className="empty-state" style={{ padding: 24 }}>
                {hayFiltros
                  ? "Ninguna salida coincide con los filtros."
                  : puedeEscribir
                  ? 'No hay salidas registradas. Creá la primera con "Nueva salida".'
                  : "No hay salidas disponibles."}
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Ítems</th>
                    <th>Total uds.</th>
                    <th>Fecha</th>
                    <th>Estado</th>
                    <th className={conAuditoria ? "col-opcional" : undefined}>Cargada por</th>
                    {conAuditoria && <th className="col-auditoria"></th>}
                  </tr>
                </thead>
                <tbody>
                  {salidas.map((s) => {
                    const isSel = s.id_salida === selectedId;
                    return (
                      <tr
                        key={s.id_salida}
                        onClick={() => setSelectedId(s.id_salida)}
                        style={{
                          cursor: "pointer",
                          background: isSel ? "var(--green-50, #f0fdf4)" : undefined,
                        }}
                      >
                        <td>{s.items_count ?? (s.lineas ?? []).length}</td>
                        <td>{formatCantidad(totalUnidades(s))}</td>
                        <td>{formatFecha(s.fecha)}</td>
                        <td>
                          <span
                            className={`badge ${
                              s.estado === ESTADO_PENDIENTE ? "badge-gold" : "badge-green"
                            }`}
                          >
                            {s.estado_display}
                          </span>
                        </td>
                        <td className={conAuditoria ? "col-opcional" : undefined}>{formatUsuario(s)}</td>
                        {conAuditoria && (
                          <td className="col-auditoria" onClick={(e) => e.stopPropagation()}>
                            <AuditoriaBoton auditoria={s.auditoria} conFinalizacion />
                          </td>
                        )}
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
                  <h3>Salida · {formatFecha(selected.fecha)}</h3>
                  <div className="sub">
                    {selected.items_count ?? (selected.lineas ?? []).length} ítems
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
                  Datos de la salida
                </div>
                <div className="detail-row">
                  <span>Fecha y hora</span>
                  <span>{formatFecha(selected.fecha)}</span>
                </div>
                <div className="detail-row">
                  <span>Estado</span>
                  <span>{selected.estado_display}</span>
                </div>
                <div className="detail-row">
                  <span>Total de unidades</span>
                  <span>{formatCantidad(totalUnidades(selected))}</span>
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
                      <th>Producto</th>
                      <th style={{ textAlign: "right" }}>Cantidad</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(selected.lineas ?? []).map((l) => (
                      <tr key={l.id_linea_salida}>
                        <td>{l.producto_nombre}</td>
                        <td style={{ textAlign: "right" }}>{formatCantidad(l.cantidad)} uds.</td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                <div style={{ marginTop: 12, fontSize: 13, color: "var(--gray-500)" }}>
                  <i className="fa-solid fa-circle-info"></i>{" "}
                  {selected.estado === ESTADO_FINALIZADA
                    ? "Salida finalizada: ya se descontó del stock de cada producto."
                    : "Al finalizarla se descontará del stock de cada producto."}
                </div>
              </div>

              {/* Una salida finalizada ya hizo efecto: queda de solo lectura y no
                  se puede eliminar. */}
              {selected.estado === ESTADO_PENDIENTE && puedeEscribir ? (
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
                    <i className="fa-solid fa-lock"></i> Salida finalizada. No se puede editar ni
                    eliminar.
                  </div>
                )
              )}
            </div>
          )}
        </div>
      )}

      {modalMode === "create" && (
        <SalidaFormModal
          productos={productos}
          onClose={() => setModalMode(null)}
          onSubmit={handleSaved}
        />
      )}
      {modalMode === "edit" && selected && (
        <SalidaFormModal
          productos={productos}
          initialData={selected}
          onClose={() => setModalMode(null)}
          onSubmit={handleSaved}
        />
      )}
    </div>
  );
}
