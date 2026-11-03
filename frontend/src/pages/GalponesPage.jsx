import { useEffect, useState, useMemo } from "react";
import { listGalpones, createGalpon, updateGalpon, deleteGalpon, altaGalpon, bajaGalpon, getExistenciasGalpon } from "../api/galpones";
import GalponFormModal from "../components/GalponFormModal";
import { useAuth } from "../context/AuthContext";
import { useDialogo } from "../components/Dialogo";
import Paginacion, { useTamanoPagina } from "../components/Paginacion";
import AuditoriaBoton from "../components/AuditoriaBoton";
import { EsqueletoTarjetas } from "../components/Esqueleto";
import AyudaSeccion from "../components/AyudaSeccion";

// El modelo solo tiene idGalpon (PK numérica) y galpon (nombre); "G-01"
// es puramente una etiqueta visual derivada del id real, no un campo aparte.
function formatCodigo(id) {
  return `G-${String(id).padStart(2, "0")}`;
}

function formatCantidad(valor) {
  const n = Number(valor);
  return Number.isNaN(n) ? "—" : n.toLocaleString("es-AR", { maximumFractionDigits: 2 });
}

function formatFechaCorta(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("es-AR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export default function GalponesPage() {
  const { confirmar, avisar } = useDialogo();
  const { esAdministrador, esOperario } = useAuth();

  const [galpones, setGalpones] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useTamanoPagina("galpones", 16);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [actionError, setActionError] = useState(null);
  // Por defecto, los operarios ven solo sus galpones activos; el resto de
  // los roles arranca sin filtro (ve todos, activos e inactivos).
  const [estadoFilter, setEstadoFilter] = useState(esOperario ? "A" : "");
  const [modalMode, setModalMode] = useState(null); // null | "create" | "edit"
  // Existencia estimada de materias primas del galpón seleccionado (null = cargando).
  const [existencias, setExistencias] = useState(null);
  const [existenciasError, setExistenciasError] = useState(false);

  async function fetchGalpones() {
    setLoading(true);
    setError(null);
    try {
      const params = { page, page_size: pageSize };
      if (search) params.search = search;
      if (estadoFilter) params.estado = estadoFilter;
      const data = await listGalpones(params);
      const lista = data.results ?? data;
      setGalpones(lista);
      setCount(data.count ?? lista.length);
      // Si el elemento seleccionado no está en esta página, se muestra el primero.
      setSelectedId((actual) =>
        lista.some((x) => x.id_galpon === actual) ? actual : (lista[0]?.id_galpon ?? null)
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
    fetchGalpones();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, estadoFilter, page, pageSize]);

  useEffect(() => {
    if (!selectedId) {
      setExistencias([]);
      return;
    }
    let cancelado = false;
    setExistencias(null);
    setExistenciasError(false);
    getExistenciasGalpon(selectedId)
      .then((d) => {
        if (!cancelado) setExistencias(d);
      })
      .catch(() => {
        if (!cancelado) {
          setExistencias([]);
          setExistenciasError(true);
        }
      });
    return () => {
      cancelado = true;
    };
  }, [selectedId]);

  /** Cambia un filtro: vuelve a la primera página. */
  function cambiarFiltro(setter) {
    return (valor) => {
      setter(valor);
      setPage(1);
    };
  }

  const selected = useMemo(
    () => galpones.find((g) => g.id_galpon === selectedId) || null,
    [galpones, selectedId]
  );

  async function handleCreate(data) {
    const created = await createGalpon(data);
    setModalMode(null);
    if (page !== 1) {
      // El alta puede quedar en la primera página: se vuelve a ella (el efecto recarga).
      setSelectedId(created.id_galpon);
      setPage(1);
      return;
    }
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
    if (!(await confirmar({ titulo: "Eliminar galpón", mensaje: `¿Eliminar el galpón "${selected.galpon}"? Esta acción no se puede deshacer.`, confirmarTexto: "Eliminar", peligro: true }))) return;
    setActionError(null);
    try {
      await deleteGalpon(selected.id_galpon);
      setSelectedId(null);
      await fetchGalpones();
    } catch (err) {
      // err.status === 0 → sin red; con 409 el backend explica qué registros lo impiden.
      if (err.status === 0) {
        setActionError("No se pudo conectar con el servidor.");
      } else {
        setActionError(err.message || "No se pudo eliminar el galpón.");
      }
    }
  }

  async function handleBaja() {
    if (!selected) return;
    setActionError(null);
    try {
      await bajaGalpon(selected.id_galpon);
      await fetchGalpones();
    } catch (err) {
      setActionError(err.message);
    }
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
          <div className="page-titulo"><h1>Galpones</h1><AyudaSeccion seccion="galpones" /></div>
          <div className="desc">Administrá las instalaciones donde se alojan los lotes de gallinas ponedoras.</div>
        </div>
        {esAdministrador && (
          <button className="btn btn-green" data-tutorial="sec-nuevo" onClick={() => setModalMode("create")}>
            <i className="fa-solid fa-plus"></i> Nuevo galpón
          </button>
        )}
      </div>

      <div className="toolbar" data-tutorial="sec-filtros">
        <div className="search-box">
          <i className="fa-solid fa-magnifying-glass"></i>
          <input
            type="text"
            placeholder="Buscar por nombre o descripción..."
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
      {loading && <EsqueletoTarjetas texto="Cargando galpones..." />}

      {!loading && !error && (
        <div className="page-body-split">
          <div className="card-column">
            <div className="card-grid" data-tutorial="sec-lista">
              {galpones.length === 0 && (
                <div className="empty-state">
                  {esAdministrador
                    ? 'No hay galpones registrados todavía. Creá el primero con "Nuevo galpón".'
                    : "No tenés galpones asignados."}
                </div>
              )}
              {galpones.map((g) => (
                <div
                  data-tutorial-fila=""
                  key={g.id_galpon}
                  className={`galpon-card ${g.id_galpon === selectedId ? "card-selected" : ""}`}
                  onClick={() => { setSelectedId(g.id_galpon); setActionError(null); }}
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
              <div className="detail-head">
                <div>
                  <h3>{formatCodigo(selected.id_galpon)} · {selected.galpon}</h3>
                </div>
                <span className={`badge ${selected.estado === "A" ? "badge-green" : "badge-red"}`}>
                  {selected.estado_display}
                </span>
                <AuditoriaBoton auditoria={selected.auditoria} />
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

                {/* Materias primas en el galpón (estimadas) */}
                <div className="detail-sec-title">Materias primas en el galpón</div>
                {existencias === null ? (
                  <div className="form-hint" style={{ marginBottom: 10 }}>Cargando...</div>
                ) : existenciasError ? (
                  <div className="form-hint" style={{ marginBottom: 10 }}>
                    No se pudo cargar la existencia de materias primas.
                  </div>
                ) : existencias.length === 0 ? (
                  <div className="form-hint" style={{ marginBottom: 10 }}>
                    Este galpón todavía no recibió materias primas.
                  </div>
                ) : (
                  <>
                    <div>
                      {existencias.map((e) => (
                        <div
                          key={e.id_materia_prima}
                          style={{ padding: "8px 0", borderBottom: "1px dashed var(--gray-200)" }}
                        >
                          <div
                            style={{
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "baseline",
                              gap: 12,
                            }}
                          >
                            <span style={{ fontWeight: 500 }}>{e.materia_prima}</span>
                            <span style={{ fontWeight: 700, whiteSpace: "nowrap" }}>
                              {formatCantidad(e.existencia_estimada)} {e.unidad}
                            </span>
                          </div>
                          <div style={{ fontSize: 12, color: "var(--gray-500)", marginTop: 2 }}>
                            Último ingreso: {formatCantidad(e.ultimo_ingreso)} {e.unidad} ·{" "}
                            {formatFechaCorta(e.ultimo_ingreso_fecha)}
                            {Number(e.descartado_desde_entonces) > 0 &&
                              ` · Descartado desde entonces: ${formatCantidad(
                                e.descartado_desde_entonces
                              )} ${e.unidad}`}
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="form-hint" style={{ marginTop: 6 }}>
                      <i className="fa-solid fa-circle-info"></i> Estimada, como máximo: último
                      ingreso finalizado menos los descartes del galpón posteriores. Supone que la
                      carga anterior ya se consumió y no descuenta el consumo diario de las
                      gallinas.
                    </div>
                  </>
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
