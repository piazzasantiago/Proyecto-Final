import { useEffect, useMemo, useState } from "react";
import { listDescartes, deleteDescarte, finalizarDescarte } from "../api/descartes";
import { listGalpones } from "../api/galpones";
import { listMateriasPrimas } from "../api/materias-primas";
import { listProductos } from "../api/productos";
import DescarteFormModal, {
  CATEGORIAS,
  CATEGORIA_GALPON,
  CATEGORIA_STOCK,
  TIPOS,
} from "../components/DescarteFormModal";
import { useAuth } from "../context/AuthContext";
import { useDialogo } from "../components/Dialogo";
import Paginacion, { useTamanoPagina } from "../components/Paginacion";
import { traerTodas } from "../api/paginado";
import AuditoriaBoton from "../components/AuditoriaBoton";
import useAtajoAlta from "../components/useAtajoAlta";
import AyudaSeccion from "../components/AyudaSeccion";
import { EsqueletoTabla } from "../components/Esqueleto";

import CerrarDetalle from "../components/CerrarDetalle";
const ESTADO_PENDIENTE = "P";
const ESTADO_FINALIZADO = "F";

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

function formatGalpon(d) {
  const id = d.galpon?.id_galpon;
  const nombre = d.galpon?.galpon || "";
  return id ? `G-${String(id).padStart(2, "0")} · ${nombre}` : "—";
}

function formatUsuario(d) {
  return d.usuario?.nombre_completo || d.usuario?.usuario || "—";
}

function formatCantidad(valor) {
  const n = Number(valor);
  return Number.isNaN(n) ? "—" : n.toLocaleString("es-AR", { maximumFractionDigits: 2 });
}

/** Cantidad con su unidad cuando es una materia prima ("15 kg"). */
function cantidadDeLinea(l) {
  const base = formatCantidad(l.cantidad);
  return l.materia_prima_unidad ? `${base} ${l.materia_prima_unidad}` : base;
}

function nombreDeLinea(l) {
  return l.materia_prima_nombre ?? l.producto_nombre ?? l.lote_codigo ?? "—";
}

function etiquetaDeTipo(tipo) {
  return TIPOS.find((t) => t.value === tipo)?.label ?? "—";
}

function categoriaDe(valor) {
  return CATEGORIAS.find((c) => c.value === valor);
}

/** Texto que explica qué efecto tiene (o tuvo) el descarte seleccionado. */
function notaDeEfecto(d) {
  const finalizado = d.estado === ESTADO_FINALIZADO;
  if (d.categoria === CATEGORIA_STOCK) {
    return finalizado
      ? "Descarte de stock finalizado: ya se descontó del stock de cada ítem."
      : "Descarte de stock: al finalizarlo se descontará del stock de cada ítem.";
  }
  const hayGallinas = (d.lineas ?? []).some((l) => l.tipo === "lote");
  const base = "Descarte de galpón: es estadístico y no modifica el stock.";
  if (!hayGallinas) return base;
  return finalizado
    ? `${base} Las gallinas ya se descontaron de la cantidad actual del lote.`
    : `${base} Al finalizarlo se descontarán las gallinas de la cantidad actual del lote.`;
}

export default function DescartesPage() {
  const { confirmar, avisar } = useDialogo();
  const { esAdministrador, esOperario } = useAuth();
  const puedeEscribir = esAdministrador || esOperario;

  const [descartes, setDescartes] = useState([]);
  const [galpones, setGalpones] = useState([]);
  const [materiasPrimas, setMateriasPrimas] = useState([]);
  const [productos, setProductos] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useTamanoPagina("descartes", 16);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [fechaDesde, setFechaDesde] = useState("");
  const [fechaHasta, setFechaHasta] = useState("");
  const [categoriaFilter, setCategoriaFilter] = useState("");
  const [estadoFilter, setEstadoFilter] = useState("");
  const [modalMode, setModalMode] = useState(null); // null | "create" | "edit"

  // Atajo "Registrar descarte" del panel principal.
  useAtajoAlta(() => setModalMode("create"), { estado: setEstadoFilter });

  const hayFiltros = Boolean(fechaDesde || fechaHasta || categoriaFilter || estadoFilter);

  async function fetchDescartes(seleccionar) {
    setLoading(true);
    setError(null);
    try {
      const params = { page, page_size: pageSize };
      if (fechaDesde) params.fecha_desde = fechaDesde;
      if (fechaHasta) params.fecha_hasta = fechaHasta;
      if (categoriaFilter) params.categoria = categoriaFilter;
      if (estadoFilter) params.estado = estadoFilter;
      const data = await listDescartes(params);
      const lista = data.results ?? data;
      setDescartes(lista);
      setCount(data.count ?? lista.length);
      setSelectedId((actual) => {
        if (seleccionar) return seleccionar;
        if (actual && lista.some((d) => d.id_descarte === actual)) return actual;
        return lista.length > 0 ? lista[0].id_descarte : null;
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
    fetchDescartes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fechaDesde, fechaHasta, categoriaFilter, estadoFilter, page, pageSize]);

  // Catálogos para el formulario: solo se cargan una vez.
  useEffect(() => {
    traerTodas(listGalpones, { estado: "A" }).then(setGalpones).catch(() => setGalpones([]));
    traerTodas(listMateriasPrimas, { estado: "A" })
      .then(setMateriasPrimas)
      .catch(() => setMateriasPrimas([]));
    traerTodas(listProductos, { estado: "A" }).then(setProductos).catch(() => setProductos([]));
  }, []);

  const selected = useMemo(
    () => descartes.find((d) => d.id_descarte === selectedId) || null,
    [descartes, selectedId]
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
    setCategoriaFilter("");
    setEstadoFilter("");
  }

  // Después de crear, editar o finalizar un descarte de stock cambia el stock
  // disponible, así que se vuelven a pedir los catálogos que lo muestran.
  async function refrescarStock() {
    try {
      const [mps, prods] = await Promise.all([
        traerTodas(listMateriasPrimas, { estado: "A" }),
        traerTodas(listProductos, { estado: "A" }),
      ]);
      setMateriasPrimas(mps);
      setProductos(prods);
    } catch {
      /* se mantiene el último stock conocido */
    }
  }

  async function handleSaved(result) {
    const eraAlta = modalMode === "create";
    setModalMode(null);
    if (eraAlta && page !== 1) {
      // El alta queda primera: se vuelve a la página 1 (el efecto recarga la lista).
      setSelectedId(result?.id_descarte ?? null);
      setPage(1);
      return;
    }
    await fetchDescartes(result?.id_descarte);
  }

  async function handleDelete() {
    if (!selected) return;
    if (
      !(await confirmar({
        titulo: "Eliminar descarte",
        mensaje: `¿Eliminar el descarte del ${formatFecha(selected.fecha)}? Esta acción no se puede deshacer.`,
        confirmarTexto: "Eliminar",
        peligro: true,
      }))
    )
      return;
    try {
      await deleteDescarte(selected.id_descarte);
      setSelectedId(null);
      await fetchDescartes();
    } catch (err) {
      await avisar({ titulo: "No se pudo eliminar el descarte", mensaje: err.message });
    }
  }

  async function handleFinalizar() {
    if (!selected) return;
    let aviso = "";
    if (selected.categoria === CATEGORIA_STOCK) {
      aviso = " Se descontará del stock de cada ítem.";
    } else if ((selected.lineas ?? []).some((l) => l.tipo === "lote")) {
      aviso = " Se descontarán las gallinas descartadas de la cantidad actual del lote.";
    }
    if (
      !(await confirmar({
        titulo: "Finalizar descarte",
        mensaje: `¿Finalizar el descarte del ${formatFecha(selected.fecha)}? No podrá editarse después.${aviso}`,
        confirmarTexto: "Finalizar",
        peligro: false,
      }))
    )
      return;
    try {
      await finalizarDescarte(selected.id_descarte);
      await fetchDescartes();
      if (selected.categoria === CATEGORIA_STOCK) await refrescarStock();
    } catch (err) {
      await avisar({ titulo: "No se pudo finalizar el descarte", mensaje: err.message });
    }
  }

  const categoriaSel = selected ? categoriaDe(selected.categoria) : null;

  // Con auditoría disponible (Administrador y Consulta) la columna de usuario es opcional y se suma el ojito.
  const conAuditoria = descartes.some((x) => x.auditoria);

  return (
    <div className="page active" id="page-descartes">
      <div className="page-header">
        <div>
          <div className="page-titulo"><h1>Descartes</h1><AyudaSeccion seccion="descartes" /></div>
          <div className="desc">
            Bajas ocurridas en un galpón (con fines estadísticos) y bajas del stock de productos y
            materias primas.
          </div>
        </div>
        {puedeEscribir && (
          <button className="btn btn-green" data-tutorial="sec-nuevo" onClick={() => setModalMode("create")}>
            <i className="fa-solid fa-plus"></i> Nuevo descarte
          </button>
        )}
      </div>

      {/* Filtros: fechas, categoría y estado */}
      <div className="toolbar" data-tutorial="sec-filtros">
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
          value={categoriaFilter}
          onChange={(e) => cambiarFiltro(setCategoriaFilter)(e.target.value)}
        >
          <option value="">Categoría: Todas</option>
          <option value={CATEGORIA_GALPON}>Galpones</option>
          <option value={CATEGORIA_STOCK}>Stock</option>
        </select>
        <select
          className="select-filter"
          value={estadoFilter}
          onChange={(e) => cambiarFiltro(setEstadoFilter)(e.target.value)}
        >
          <option value="">Estado: Todos</option>
          <option value={ESTADO_PENDIENTE}>Pendiente</option>
          <option value={ESTADO_FINALIZADO}>Finalizado</option>
        </select>
        {hayFiltros && (
          <button className="btn btn-outline" onClick={limpiarFiltros}>
            <i className="fa-solid fa-xmark"></i> Limpiar
          </button>
        )}
      </div>

      {error && <div className="banner banner-error">{error}</div>}
      {loading && <EsqueletoTabla texto="Cargando descartes..." />}

      {!loading && !error && (
        <div className="page-body-split">
          {/* ── Lista ─────────────────────────────────────────────────── */}
          <div className="list-panel" data-tutorial="sec-lista">
            {descartes.length === 0 ? (
              <div className="empty-state" style={{ padding: 24 }}>
                {hayFiltros
                  ? "Ningún descarte coincide con los filtros."
                  : puedeEscribir
                  ? 'No hay descartes registrados. Creá el primero con "Nuevo descarte".'
                  : "No hay descartes disponibles."}
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Categoría</th>
                    <th>Galpón</th>
                    <th>Ítems</th>
                    <th>Fecha</th>
                    <th>Estado</th>
                    <th className={conAuditoria ? "col-opcional" : undefined}>Cargado por</th>
                    {conAuditoria && <th className="col-auditoria"></th>}
                  </tr>
                </thead>
                <tbody>
                  {descartes.map((d) => {
                    const isSel = d.id_descarte === selectedId;
                    const cat = categoriaDe(d.categoria);
                    return (
                      <tr
                        data-tutorial-fila=""
                        key={d.id_descarte}
                        onClick={() => setSelectedId(d.id_descarte)}
                        className={isSel ? "row-selected" : undefined}
                        style={{ cursor: "pointer" }}
                      >
                        <td>
                          {cat && <i className={`fa-solid ${cat.icono}`}></i>} {d.categoria_display}
                        </td>
                        <td>{formatGalpon(d)}</td>
                        <td>{d.items_count ?? (d.lineas ?? []).length}</td>
                        <td>{formatFecha(d.fecha)}</td>
                        <td>
                          <span
                            className={`badge ${
                              d.estado === ESTADO_PENDIENTE ? "badge-gold" : "badge-green"
                            }`}
                          >
                            {d.estado_display}
                          </span>
                        </td>
                        <td className={conAuditoria ? "col-opcional" : undefined}>{formatUsuario(d)}</td>
                        {conAuditoria && (
                          <td className="col-auditoria" onClick={(e) => e.stopPropagation()}>
                            <AuditoriaBoton auditoria={d.auditoria} conFinalizacion />
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
            <div key={selectedId} className="detail-panel" data-tutorial="sec-detalle">
              <CerrarDetalle />
              <div className="detail-head">
                <div>
                  <h3>
                    {selected.categoria === CATEGORIA_STOCK
                      ? "Descarte de stock"
                      : `Descarte · ${formatGalpon(selected)}`}
                  </h3>
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
                  Datos del descarte
                </div>
                <div className="detail-row">
                  <span>Categoría</span>
                  <span>
                    {categoriaSel && <i className={`fa-solid ${categoriaSel.icono}`}></i>}{" "}
                    {selected.categoria_display}
                  </span>
                </div>
                {selected.categoria === CATEGORIA_GALPON && (
                  <div className="detail-row">
                    <span>Galpón</span>
                    <span>{formatGalpon(selected)}</span>
                  </div>
                )}
                <div className="detail-row">
                  <span>Fecha y hora</span>
                  <span>{formatFecha(selected.fecha)}</span>
                </div>
                <div className="detail-row">
                  <span>Estado</span>
                  <span>{selected.estado_display}</span>
                </div>
                <div className="detail-row">
                  <span>Cargado por</span>
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
                      <th>Tipo</th>
                      <th>Ítem</th>
                      <th style={{ textAlign: "right" }}>Cantidad</th>
                      <th>Motivo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(selected.lineas ?? []).map((l) => (
                      <tr key={l.id_linea_descarte}>
                        <td>{etiquetaDeTipo(l.tipo)}</td>
                        <td>{nombreDeLinea(l)}</td>
                        <td style={{ textAlign: "right" }}>{cantidadDeLinea(l)}</td>
                        <td>{l.motivo}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                <div style={{ marginTop: 12, fontSize: 13, color: "var(--gray-500)" }}>
                  <i className="fa-solid fa-circle-info"></i> {notaDeEfecto(selected)}
                </div>
              </div>

              {/* Acciones: un descarte finalizado ya hizo efecto, por eso queda de
                  solo lectura y no se puede eliminar. */}
              {selected.estado === ESTADO_PENDIENTE && puedeEscribir ? (
                <div className="detail-actions" style={{ flexWrap: "wrap" }} data-tutorial="sec-acciones">
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
                selected.estado === ESTADO_FINALIZADO && (
                  <div className="detail-actions" style={{ color: "var(--gray-500)", fontSize: 13 }}>
                    <i className="fa-solid fa-lock"></i> Descarte finalizado. No se puede
                    editar ni eliminar.
                  </div>
                )
              )}
            </div>
          )}
        </div>
      )}

      {modalMode === "create" && (
        <DescarteFormModal
          galpones={galpones}
          materiasPrimas={materiasPrimas}
          productos={productos}
          onClose={() => setModalMode(null)}
          onSubmit={handleSaved}
        />
      )}
      {modalMode === "edit" && selected && (
        <DescarteFormModal
          galpones={galpones}
          materiasPrimas={materiasPrimas}
          productos={productos}
          initialData={selected}
          onClose={() => setModalMode(null)}
          onSubmit={handleSaved}
        />
      )}
    </div>
  );
}
