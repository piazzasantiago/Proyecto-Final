import { useEffect, useMemo, useState } from "react";
import { listEntradas, deleteEntrada, finalizarEntrada } from "../api/entradas";
import { listGalpones } from "../api/galpones";
import { listMateriasPrimas } from "../api/materias-primas";
import EntradaFormModal from "../components/EntradaFormModal";
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

function formatGalpon(e) {
  const id = e.galpon?.id_galpon;
  const nombre = e.galpon?.galpon || "";
  return id ? `G-${String(id).padStart(2, "0")} · ${nombre}` : "—";
}

function formatUsuario(e) {
  return e.usuario?.nombre_completo || e.usuario?.usuario || "—";
}

function formatCantidad(valor) {
  const n = Number(valor);
  return Number.isNaN(n) ? "—" : n.toLocaleString("es-AR", { maximumFractionDigits: 2 });
}

export default function EntradasPage() {
  const { confirmar, avisar } = useDialogo();
  const { esAdministrador, esOperario } = useAuth();
  const puedeEscribir = esAdministrador || esOperario;

  const [entradas, setEntradas] = useState([]);
  const [galpones, setGalpones] = useState([]);
  const [materiasPrimas, setMateriasPrimas] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useTamanoPagina("entradas", 16);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [fechaDesde, setFechaDesde] = useState("");
  const [fechaHasta, setFechaHasta] = useState("");
  const [galponFilter, setGalponFilter] = useState("");
  const [materiaFilter, setMateriaFilter] = useState("");
  const [estadoFilter, setEstadoFilter] = useState("");
  // Atajos del panel principal: abrir la sección con el filtro de estado ya puesto.
  useAtajoAlta(null, { estado: setEstadoFilter });
  const [modalMode, setModalMode] = useState(null); // null | "create" | "edit"

  const hayFiltros = Boolean(
    fechaDesde || fechaHasta || galponFilter || materiaFilter || estadoFilter
  );

  async function fetchEntradas(seleccionar) {
    setLoading(true);
    setError(null);
    try {
      const params = { page, page_size: pageSize };
      if (fechaDesde) params.fecha_desde = fechaDesde;
      if (fechaHasta) params.fecha_hasta = fechaHasta;
      if (galponFilter) params.id_galpon = galponFilter;
      if (materiaFilter) params.id_materia_prima = materiaFilter;
      if (estadoFilter) params.estado = estadoFilter;
      const data = await listEntradas(params);
      const lista = data.results ?? data;
      setEntradas(lista);
      setCount(data.count ?? lista.length);
      setSelectedId((actual) => {
        if (seleccionar) return seleccionar;
        if (actual && lista.some((e) => e.id_entrada === actual)) return actual;
        return lista.length > 0 ? lista[0].id_entrada : null;
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
    fetchEntradas();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fechaDesde, fechaHasta, galponFilter, materiaFilter, estadoFilter, page, pageSize]);

  // Catálogos para el formulario y los filtros: se cargan una vez.
  useEffect(() => {
    traerTodas(listGalpones, { estado: "A" }).then(setGalpones).catch(() => setGalpones([]));
    refrescarStock();
  }, []);

  const selected = useMemo(
    () => entradas.find((e) => e.id_entrada === selectedId) || null,
    [entradas, selectedId]
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
    setGalponFilter("");
    setMateriaFilter("");
    setEstadoFilter("");
  }

  // Finalizar una entrada cambia el stock de las materias primas, así que se
  // vuelve a pedir el catálogo que lo muestra.
  async function refrescarStock() {
    try {
      setMateriasPrimas(await traerTodas(listMateriasPrimas, { estado: "A" }));
    } catch {
      /* se mantiene el último stock conocido */
    }
  }

  async function handleSaved(result) {
    const eraAlta = modalMode === "create";
    setModalMode(null);
    if (eraAlta && page !== 1) {
      // El alta queda primera: se vuelve a la página 1 (el efecto recarga la lista).
      setSelectedId(result?.id_entrada ?? null);
      setPage(1);
      return;
    }
    await fetchEntradas(result?.id_entrada);
  }

  async function handleDelete() {
    if (!selected) return;
    if (
      !(await confirmar({
        titulo: "Eliminar entrada",
        mensaje: `¿Eliminar la entrada del ${formatFecha(selected.fecha)}? Esta acción no se puede deshacer.`,
        confirmarTexto: "Eliminar",
        peligro: true,
      }))
    )
      return;
    try {
      await deleteEntrada(selected.id_entrada);
      setSelectedId(null);
      await fetchEntradas();
    } catch (err) {
      await avisar({ titulo: "No se pudo eliminar la entrada", mensaje: err.message });
    }
  }

  async function handleFinalizar() {
    if (!selected) return;
    if (
      !(await confirmar({
        titulo: "Finalizar entrada",
        mensaje: `¿Finalizar la entrada del ${formatFecha(selected.fecha)}? No podrá editarse después. ` +
          "Se descontará del stock de cada materia prima.",
        confirmarTexto: "Finalizar",
        peligro: false,
      }))
    )
      return;
    try {
      await finalizarEntrada(selected.id_entrada);
      await fetchEntradas();
      await refrescarStock();
    } catch (err) {
      await avisar({ titulo: "No se pudo finalizar la entrada", mensaje: err.message });
    }
  }

  // Con auditoría disponible (Administrador y Consulta) la columna de usuario es opcional y se suma el ojito.
  const conAuditoria = entradas.some((x) => x.auditoria);

  return (
    <div className="page active" id="page-entradas">
      <div className="page-header">
        <div>
          <h1>Entradas</h1>
          <div className="desc">
            Materias primas que se retiran del stock y pasan a un galpón (por ejemplo, el
            balanceado que se carga en los comederos).
          </div>
        </div>
        {puedeEscribir && (
          <button className="btn btn-green" onClick={() => setModalMode("create")}>
            <i className="fa-solid fa-plus"></i> Nueva entrada
          </button>
        )}
      </div>

      {/* Filtros: fechas, galpón, materia prima y estado */}
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
          value={galponFilter}
          onChange={(e) => cambiarFiltro(setGalponFilter)(e.target.value)}
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
          value={materiaFilter}
          onChange={(e) => cambiarFiltro(setMateriaFilter)(e.target.value)}
        >
          <option value="">Materia prima: Todas</option>
          {materiasPrimas.map((m) => (
            <option key={m.id_materia_prima} value={m.id_materia_prima}>
              {m.materia_prima}
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
      {loading && <EsqueletoTabla texto="Cargando entradas..." />}

      {!loading && !error && (
        <div className="page-body-split">
          {/* ── Lista ─────────────────────────────────────────────────── */}
          <div className="list-panel">
            {entradas.length === 0 ? (
              <div className="empty-state" style={{ padding: 24 }}>
                {hayFiltros
                  ? "Ninguna entrada coincide con los filtros."
                  : puedeEscribir
                  ? 'No hay entradas registradas. Creá la primera con "Nueva entrada".'
                  : "No hay entradas disponibles."}
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Galpón</th>
                    <th>Ítems</th>
                    <th>Fecha</th>
                    <th>Estado</th>
                    <th className={conAuditoria ? "col-opcional" : undefined}>Cargada por</th>
                    {conAuditoria && <th className="col-auditoria"></th>}
                  </tr>
                </thead>
                <tbody>
                  {entradas.map((e) => {
                    const isSel = e.id_entrada === selectedId;
                    return (
                      <tr
                        key={e.id_entrada}
                        onClick={() => setSelectedId(e.id_entrada)}
                        style={{
                          cursor: "pointer",
                          background: isSel ? "var(--green-50, #f0fdf4)" : undefined,
                        }}
                      >
                        <td>{formatGalpon(e)}</td>
                        <td>{e.items_count ?? (e.lineas ?? []).length}</td>
                        <td>{formatFecha(e.fecha)}</td>
                        <td>
                          <span
                            className={`badge ${
                              e.estado === ESTADO_PENDIENTE ? "badge-gold" : "badge-green"
                            }`}
                          >
                            {e.estado_display}
                          </span>
                        </td>
                        <td className={conAuditoria ? "col-opcional" : undefined}>{formatUsuario(e)}</td>
                        {conAuditoria && (
                          <td className="col-auditoria" onClick={(e) => e.stopPropagation()}>
                            <AuditoriaBoton auditoria={e.auditoria} conFinalizacion />
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
                  <h3>Entrada · {formatGalpon(selected)}</h3>
                  <div className="sub">{formatFecha(selected.fecha)}</div>
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
                  Datos de la entrada
                </div>
                <div className="detail-row">
                  <span>Galpón</span>
                  <span>{formatGalpon(selected)}</span>
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
                      <th>Materia prima</th>
                      <th style={{ textAlign: "right" }}>Cantidad</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(selected.lineas ?? []).map((l) => (
                      <tr key={l.id_linea_entrada}>
                        <td>{l.materia_prima_nombre}</td>
                        <td style={{ textAlign: "right" }}>
                          {formatCantidad(l.cantidad)} {l.materia_prima_unidad}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                <div style={{ marginTop: 12, fontSize: 13, color: "var(--gray-500)" }}>
                  <i className="fa-solid fa-circle-info"></i>{" "}
                  {selected.estado === ESTADO_FINALIZADA
                    ? "Entrada finalizada: ya se descontó del stock de cada materia prima."
                    : "Al finalizarla se descontará del stock de cada materia prima."}
                </div>
              </div>

              {/* Una entrada finalizada ya hizo efecto: queda de solo lectura y no
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
                    <i className="fa-solid fa-lock"></i> Entrada finalizada. No se puede editar
                    ni eliminar.
                  </div>
                )
              )}
            </div>
          )}
        </div>
      )}

      {modalMode === "create" && (
        <EntradaFormModal
          galpones={galpones}
          materiasPrimas={materiasPrimas}
          onClose={() => setModalMode(null)}
          onSubmit={handleSaved}
        />
      )}
      {modalMode === "edit" && selected && (
        <EntradaFormModal
          galpones={galpones}
          materiasPrimas={materiasPrimas}
          initialData={selected}
          onClose={() => setModalMode(null)}
          onSubmit={handleSaved}
        />
      )}
    </div>
  );
}
