import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

const navItemClass = ({ isActive }) => `sb-item${isActive ? " active" : ""}`;

/** Iniciales para el avatar: "Juan Pérez" -> "JP". */
function iniciales(usuario) {
  if (!usuario) return "?";
  return `${usuario.nombre?.[0] ?? ""}${usuario.apellido?.[0] ?? ""}`.toUpperCase();
}

export default function AppLayout() {
  const navigate = useNavigate();
  const { usuario, cerrarSesion, esAdministrador } = useAuth();

  async function handleLogout() {
    await cerrarSesion();
    navigate("/login", { replace: true });
  }

  return (
    <div className="screen active" id="screen-app">
      <div className="sidebar">
        <div className="sb-brand">
          <div className="logo-mark"><i className="fa-solid fa-egg"></i></div>
          <span>AvíGest</span>
        </div>

        <div className="sb-section-label">Principal</div>
        <NavLink to="/app/dashboard" className={navItemClass}>
          <i className="fa-solid fa-gauge-high"></i> Dashboard
        </NavLink>

        <div className="sb-section-label">Producción</div>
        <NavLink to="/app/galpones" className={navItemClass}>
          <i className="fa-solid fa-warehouse"></i> Galpones
        </NavLink>
        <NavLink to="/app/lotes" className={navItemClass}>
          <i className="fa-solid fa-kiwi-bird"></i> Lotes de Gallinas
        </NavLink>
        <NavLink to="/app/recoleccion" className={navItemClass}>
          <i className="fa-solid fa-egg"></i> Recolección diaria
        </NavLink>
        <NavLink to="/app/descartes" className={navItemClass}>
          <i className="fa-solid fa-trash-can"></i> Descartes
        </NavLink>
        <NavLink to="/app/salidas" className={navItemClass}>
          <i className="fa-solid fa-truck-ramp-box"></i> Salidas
        </NavLink>

        <div className="sb-section-label">Insumos</div>
        <NavLink to="/app/entradas" className={navItemClass}>
          <i className="fa-solid fa-dolly"></i> Entradas
        </NavLink>
        <NavLink to="/app/materias-primas" className={navItemClass}>
          <i className="fa-solid fa-boxes-stacked"></i> Materias Primas
        </NavLink>
        <NavLink to="/app/compras" className={navItemClass}>
          <i className="fa-solid fa-cart-shopping"></i> Compras
        </NavLink>
        <NavLink to="/app/proveedores" className={navItemClass}>
          <i className="fa-solid fa-truck"></i> Proveedores
        </NavLink>

        <div className="sb-section-label">Gestión</div>
        <NavLink to="/app/informes" className={navItemClass}>
          <i className="fa-solid fa-chart-simple"></i> Informes
        </NavLink>
        {/* La gestión de usuarios es exclusiva del Administrador.
            Ocultar el enlace es solo comodidad visual: el backend responde
            403 igual si alguien intentara entrar por otra vía. */}
        {esAdministrador && (
          <NavLink to="/app/usuarios" className={navItemClass}>
            <i className="fa-solid fa-users"></i> Usuarios
          </NavLink>
        )}

        <div className="sb-footer">
          <div className="sb-user">
            <div className="sb-avatar">{iniciales(usuario)}</div>
            <div className="sb-user-info">
              <b>{usuario?.nombre_completo}</b>
              <span>{usuario?.rol_display}</span>
            </div>
          </div>
          <div className="sb-logout" onClick={handleLogout}>
            <i className="fa-solid fa-right-from-bracket"></i> Cerrar sesión
          </div>
        </div>
      </div>

      <div className="main">
        <Outlet />
      </div>
    </div>
  );
}
