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

// Clase del badge según el rol, para diferenciarlos de un vistazo.
const BADGE_ROL = { A: "badge-gold", O: "badge-green", C: "badge-gray" };

function iniciales(u) {
  return `${u.nombre?.[0] ?? ""}${u.apellido?.[0] ?? ""}`.toUpperCase();
}

/**
 * Gestión de Usuarios (CU03 a CU08). Pantalla exclusiva del Administrador.
 */
export default function UsuariosPage() {
  const { usuario: usuarioActual } = useAuth();

  const [usuarios, setUsuarios] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [aviso, setAviso] = useState(null);

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
        search: search || undefined,
        rol: rolFilter || undefined,
        estado: estadoFilter || undefined,
      });
      // DRF pagina: los registros vienen en `results`.
      setUsuarios(data.results ?? data);
    } catch (err) {
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
  }, [search, rolFilter, estadoFilter]);

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
    setError(null);
    try {
      await accion();
      await fetchUsuarios();
      if (textoOk) mostrarAviso(textoOk);
    } catch (err) {
      setError(err.message);
    } finally {
      setTrabajando(false);
    }
  }

  async function handleCreate(data) {
    const creado = await createUsuario(data);
    setModalMode(null);
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

  function handleDelete() {
    if (!selected) return;
    if (!confirm(`¿Eliminar al usuario "${selected.nombre_completo}"? Esta acción no se puede deshacer.`)) return;
    const id = selected.id_usuario;
    setSelectedId(null);
    ejecutar(() => deleteUsuario(id), "Usuario eliminado.");
  }

  return (
    <div className="page active" id="page-usuarios">
      <div className="page-header">
        <div>
          <h1>Usuarios</h1>
          <div className="desc">Administración de usuarios y permisos de acceso al sistema.</div>
        </div>
        <button className="btn btn-green" onClick={() => setModalMode("create")}>
          <i className="fa-solid fa-plus"></i> Nuevo usuario
        </button>
      </div>

      <div className="toolbar">
        <div className="search-box">
          <i className="fa-solid fa-magnifying-glass"></i>
          <input
            type="text"
            placeholder="Buscar por nombre, usuario o email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select className="select-filter" value={rolFilter} onChange={(e) => setRolFilter(e.target.value)}>
          <option value="">Rol: Todos</option>
          <option value="A">Administrador</option>
          <option value="O">Operario</option>
          <option value="C">Consulta</option>
        </select>
        <select className="select-filter" value={estadoFilter} onChange={(e) => setEstadoFilter(e.target.value)}>
          <option value="">Estado: Todos</option>
          <option value="A">Activo</option>
          <option value="I">Inactivo</option>
        </select>
      </div>

      {error && <div className="banner banner-error">{error}</div>}
      {aviso && <div className="banner banner-ok">{aviso}</div>}
      {loading && <div className="banner banner-loading">Cargando usuarios...</div>}

      {!loading && !error && (
        <div className="page-body-split">
          <div className="card-grid">
            {usuarios.length === 0 && (
              <div className="empty-state">
                No hay usuarios que coincidan con la búsqueda.
              </div>
            )}
            {usuarios.map((u) => (
              <div
                key={u.id_usuario}
                className={`usuario-card ${u.id_usuario === selectedId ? "card-selected" : ""}`}
                onClick={() => setSelectedId(u.id_usuario)}
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

          {selected && (
            <div className="detail-panel">
              <div className="detail-head">
                <div className="uc-head-user">
                  <div className="uc-avatar uc-avatar-sm">{iniciales(selected)}</div>
                  <div>
                    <h3>{selected.nombre_completo}</h3>
                    <div className="sub">{selected.usuario}</div>
                  </div>
                </div>
                <span className={`badge ${BADGE_ROL[selected.rol] ?? ""}`}>{selected.rol_display}</span>
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

              <div className="detail-actions">
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

              <div className="detail-actions detail-actions-sec">
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
