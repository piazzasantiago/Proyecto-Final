import { useEffect, useMemo, useState } from "react";

import {
  altaUsuario,
  bajaUsuario,
  createUsuario,
  deleteUsuario,
  listUsuarios,
  restablecerPassword,
  updateUsuario,
} from "../api/usuarios";
import CampoPassword from "../components/CampoPassword";
import UsuarioFormModal from "../components/UsuarioFormModal";
import { useAuth } from "../context/AuthContext";
import { useDialogo } from "../components/Dialogo";
import Paginacion, { useTamanoPagina } from "../components/Paginacion";
import AuditoriaBoton from "../components/AuditoriaBoton";
import { EsqueletoTarjetas } from "../components/Esqueleto";

import AyudaSeccion from "../components/AyudaSeccion";
// Clase del badge según el rol, para diferenciarlos de un vistazo.
const BADGE_ROL = { A: "badge-gold", O: "badge-green", C: "badge-gray" };

function iniciales(u) {
  return `${u.nombre?.[0] ?? ""}${u.apellido?.[0] ?? ""}`.toUpperCase();
}

/**
 * Gestión de Usuarios (CU03 a CU08). Pantalla exclusiva del Administrador.
 */
export default function UsuariosPage() {
  const { confirmar, avisar } = useDialogo();
  const { usuario: usuarioActual } = useAuth();

  const [usuarios, setUsuarios] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useTamanoPagina("usuarios", 16);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [aviso, setAviso] = useState(null);
  // Error de una acción sobre el usuario seleccionado (borrar, dar de baja...):
  // se muestra en el panel de detalle y no oculta el listado.
  const [actionError, setActionError] = useState(null);

  const [search, setSearch] = useState("");
  const [rolFilter, setRolFilter] = useState("");
  const [estadoFilter, setEstadoFilter] = useState("");

  const [modalMode, setModalMode] = useState(null); // null | "create" | "edit"
  const [modalPassword, setModalPassword] = useState(null); // usuario a restablecer
  const [passwordNueva, setPasswordNueva] = useState("");
  const [trabajando, setTrabajando] = useState(false);

  async function fetchUsuarios() {
    setLoading(true);
    setError(null);
    try {
      const data = await listUsuarios({
        page,
        page_size: pageSize,
        search: search || undefined,
        rol: rolFilter || undefined,
        estado: estadoFilter || undefined,
      });
      // DRF pagina: los registros vienen en `results`.
      const lista = data.results ?? data;
      setUsuarios(lista);
      setCount(data.count ?? lista.length);
      setSelectedId((actual) =>
        lista.some((u) => u.id_usuario === actual) ? actual : (lista[0]?.id_usuario ?? null)
      );
    } catch (err) {
      if (err.status === 404 && page > 1) {
        // La página quedó vacía (se eliminó el último registro de la última página).
        setPage(page - 1);
        return;
      }
      setError(err.message);
      setUsuarios([]);
    } finally {
      setLoading(false);
    }
  }

  // Debounce: espera 350 ms desde la última tecla antes de llamar a la API,
  // para no disparar una búsqueda por cada letra escrita.
  useEffect(() => {
    const t = setTimeout(fetchUsuarios, 350);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, rolFilter, estadoFilter, page, pageSize]);

  /** Cambia un filtro: vuelve a la primera página. */
  function cambiarFiltro(setter) {
    return (valor) => {
      setter(valor);
      setPage(1);
    };
  }

  const selected = useMemo(
    () => usuarios.find((u) => u.id_usuario === selectedId) ?? null,
    [usuarios, selectedId]
  );

  const esYoMismo = selected?.id_usuario === usuarioActual?.id_usuario;

  function mostrarAviso(texto) {
    setAviso(texto);
    setTimeout(() => setAviso(null), 6000);
  }

  /** Ejecuta una acción sobre la API y refresca la lista. */
  async function ejecutar(accion, textoOk) {
    setTrabajando(true);
    setActionError(null);
    try {
      await accion();
      await fetchUsuarios();
      if (textoOk) mostrarAviso(textoOk);
    } catch (err) {
      // Sin red (status 0) o 409 con el motivo explicado por el backend.
      setActionError(err.status === 0 ? "No se pudo conectar con el servidor." : err.message);
    } finally {
      setTrabajando(false);
    }
  }

  async function handleCreate(data) {
    const creado = await createUsuario(data);
    setModalMode(null);
    if (page !== 1) {
      // El alta puede quedar en la primera página: se vuelve a ella (el efecto recarga).
      setSelectedId(creado.id_usuario);
      mostrarAviso(`Usuario ${creado.nombre_completo} creado correctamente.`);
      setPage(1);
      return;
    }
    await fetchUsuarios();
    setSelectedId(creado.id_usuario);
    mostrarAviso(`Usuario ${creado.nombre_completo} creado correctamente.`);
  }

  async function handleUpdate(data) {
    const actualizado = await updateUsuario(selected.id_usuario, data);
    setModalMode(null);
    await fetchUsuarios();
    setSelectedId(actualizado.id_usuario);
    mostrarAviso("Cambios guardados.");
  }

  async function handleDelete() {
    if (!selected) return;
    if (!(await confirmar({ titulo: "Eliminar usuario", mensaje: `¿Eliminar al usuario "${selected.nombre_completo}"? Esta acción no se puede deshacer.`, confirmarTexto: "Eliminar", peligro: true }))) return;
    const id = selected.id_usuario;
    // El usuario queda seleccionado: si el backend rechaza el borrado (409), el
    // cartel se muestra en su panel. Si se elimina, la recarga elige otro.
    ejecutar(() => deleteUsuario(id), "Usuario eliminado.");
  }

  return (
    <div className="page active" id="page-usuarios">
      <div className="page-header">
        <div>
          <div className="page-titulo"><h1>Usuarios</h1><AyudaSeccion seccion="usuarios" /></div>
          <div className="desc">Administración de usuarios y permisos de acceso al sistema.</div>
        </div>
        <button className="btn btn-green" data-tutorial="sec-nuevo" onClick={() => setModalMode("create")}>
          <i className="fa-solid fa-plus"></i> Nuevo usuario
        </button>
      </div>

      <div className="toolbar" data-tutorial="sec-filtros">
        <div className="search-box">
          <i className="fa-solid fa-magnifying-glass"></i>
          <input
            type="text"
            placeholder="Buscar por nombre, usuario o email..."
            value={search}
            onChange={(e) => cambiarFiltro(setSearch)(e.target.value)}
          />
        </div>
        <select className="select-filter" value={rolFilter} onChange={(e) => cambiarFiltro(setRolFilter)(e.target.value)}>
          <option value="">Rol: Todos</option>
          <option value="A">Administrador</option>
          <option value="O">Operario</option>
          <option value="C">Consulta</option>
        </select>
        <select className="select-filter" value={estadoFilter} onChange={(e) => cambiarFiltro(setEstadoFilter)(e.target.value)}>
          <option value="">Estado: Todos</option>
          <option value="A">Activo</option>
          <option value="I">Inactivo</option>
        </select>
      </div>

      {error && <div className="banner banner-error">{error}</div>}
      {aviso && <div className="banner banner-ok">{aviso}</div>}
      {loading && <EsqueletoTarjetas texto="Cargando usuarios..." />}

      {!loading && !error && (
        <div className="page-body-split">
          <div className="card-column">
            <div className="card-grid" data-tutorial="sec-lista">
              {usuarios.length === 0 && (
                <div className="empty-state">
                  No hay usuarios que coincidan con la búsqueda.
                </div>
              )}
              {usuarios.map((u) => (
                <div
                  key={u.id_usuario}
                  data-tutorial-fila=""
                  className={`usuario-card ${u.id_usuario === selectedId ? "card-selected" : ""}`}
                  onClick={() => { setSelectedId(u.id_usuario); setActionError(null); }}
                >
                  <div className="uc-avatar">{iniciales(u)}</div>
                  <div className="uc-nombre">{u.nombre_completo}</div>
                  <div className="uc-usuario">{u.usuario}</div>
                  <div className="uc-badges">
                    <span className={`badge ${BADGE_ROL[u.rol] ?? ""}`}>{u.rol_display}</span>
                    <span className={`badge ${u.estado === "A" ? "badge-green" : "badge-red"}`}>
                      {u.estado_display}
                    </span>
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
            <div className="detail-panel" data-tutorial="sec-detalle">
              <div className="detail-head">
                <div className="uc-head-user">
                  <div className="uc-avatar uc-avatar-sm">{iniciales(selected)}</div>
                  <div>
                    <h3>{selected.nombre_completo}</h3>
                    <div className="sub">{selected.usuario}</div>
                  </div>
                </div>
                <span className={`badge ${BADGE_ROL[selected.rol] ?? ""}`}>{selected.rol_display}</span>
                <AuditoriaBoton auditoria={selected.auditoria} />
              </div>

              <div className="detail-body">
                <div className="detail-sec-title" style={{ marginTop: 0 }}>Datos del usuario</div>
                <div className="detail-row"><span>Email</span><span>{selected.email}</span></div>
                <div className="detail-row"><span>DNI</span><span>{selected.dni}</span></div>
                <div className="detail-row"><span>Rol</span><span>{selected.rol_display}</span></div>
                <div className="detail-row"><span>Estado</span><span>{selected.estado_display}</span></div>

                {esYoMismo && (
                  <div className="alert alert-info" style={{ marginTop: 16 }}>
                    <i className="fa-solid fa-circle-info"></i>
                    <span>Este es tu propio usuario: no podés darte de baja ni eliminarte.</span>
                  </div>
                )}
              </div>

              {actionError && (
                <div className="banner banner-error" style={{ margin: "0 20px 0" }}>
                  <i className="fa-solid fa-triangle-exclamation" style={{ marginRight: 6 }}></i>
                  {actionError}
                </div>
              )}
              <div className="detail-actions" data-tutorial="sec-acciones">
                <button className="btn btn-outline" disabled={trabajando} onClick={() => setModalMode("edit")}>
                  <i className="fa-solid fa-pen"></i> Editar
                </button>
                {selected.estado === "A" ? (
                  <button
                    className="btn btn-outline"
                    disabled={trabajando || esYoMismo}
                    onClick={() => ejecutar(() => bajaUsuario(selected.id_usuario), "Usuario dado de baja.")}
                  >
                    <i className="fa-solid fa-ban"></i> Dar de baja
                  </button>
                ) : (
                  <button
                    className="btn btn-green"
                    disabled={trabajando}
                    onClick={() => ejecutar(() => altaUsuario(selected.id_usuario), "Usuario dado de alta.")}
                  >
                    <i className="fa-solid fa-check"></i> Dar de alta
                  </button>
                )}
              </div>

              <div className="detail-actions detail-actions-sec" data-tutorial="sec-acciones2">
                <button
                  className="btn btn-outline"
                  disabled={trabajando}
                  onClick={() => { setPasswordNueva(""); setModalPassword(selected); }}
                >
                  <i className="fa-solid fa-key"></i> Restablecer contraseña
                </button>
                <button
                  className="btn btn-outline btn-danger-ghost"
                  disabled={trabajando || esYoMismo}
                  onClick={handleDelete}
                >
                  <i className="fa-solid fa-trash"></i> Eliminar
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {modalMode === "create" && (
        <UsuarioFormModal onClose={() => setModalMode(null)} onSubmit={handleCreate} />
      )}
      {modalMode === "edit" && selected && (
        <UsuarioFormModal
          initialData={selected}
          onClose={() => setModalMode(null)}
          onSubmit={handleUpdate}
        />
      )}

      {/* Restablecimiento de contraseña por parte del Administrador. */}
      {modalPassword && (
        <div className="modal-overlay active" onClick={() => setModalPassword(null)}>
          <div className="modal-card modal-card-sm" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Restablecer contraseña</h3>
              <button className="modal-close" onClick={() => setModalPassword(null)}>
                <i className="fa-solid fa-xmark"></i>
              </button>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: 14.5, lineHeight: 1.6, color: "var(--gray-700)", marginBottom: 14 }}>
                Vas a asignarle una contraseña provisoria a <b>{modalPassword.nombre_completo}</b>.
                Comunicásela para que pueda ingresar y cambiarla.
              </p>
              <div className="form-group full">
                {/* Arranca visible: el administrador necesita leer la
                    contraseña para poder comunicársela al usuario. */}
                <CampoPassword
                  label="Contraseña provisoria"
                  value={passwordNueva}
                  onChange={(e) => setPasswordNueva(e.target.value)}
                  placeholder="Mínimo 8 caracteres"
                  autoComplete="new-password"
                  minLength={8}
                  maxLength={128}
                  visiblePorDefecto
                />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-outline" onClick={() => setModalPassword(null)}>Cancelar</button>
              <button
                className="btn btn-green"
                disabled={trabajando || passwordNueva.length < 8}
                onClick={() => {
                  const u = modalPassword;
                  setModalPassword(null);
                  ejecutar(
                    () => restablecerPassword(u.id_usuario, passwordNueva),
                    `Contraseña de ${u.nombre_completo} restablecida.`
                  );
                }}
              >
                Restablecer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
