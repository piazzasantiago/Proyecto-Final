import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { MENU } from "../config/menu";
import { useAuth } from "../context/AuthContext";

const navItemClass = ({ isActive }) => `sb-item${isActive ? " active" : ""}`;

/** Iniciales para el avatar: "Juan Pérez" -> "JP". */
function iniciales(usuario) {
  if (!usuario) return "?";
  return `${usuario.nombre?.[0] ?? ""}${usuario.apellido?.[0] ?? ""}`.toUpperCase();
}

export default function AppLayout() {
  const navigate = useNavigate();
  const { usuario, cerrarSesion } = useAuth();

  async function handleLogout() {
    await cerrarSesion();
    navigate("/login", { replace: true });
  }

  const rol = usuario?.rol;

  return (
    <div className="screen active" id="screen-app">
      <div className="sidebar">
        <div className="sb-brand">
          <div className="logo-mark"><i className="fa-solid fa-egg"></i></div>
          <span>AvíGest</span>
        </div>

        <div className="sb-nav">
          {MENU.map((grupo) => {
            // Solo las secciones habilitadas para el rol del usuario actual.
            const visibles = grupo.items.filter((item) => item.roles.includes(rol));
            if (visibles.length === 0) return null;

            return (
              <div key={grupo.grupo}>
                <div className="sb-section-label">{grupo.grupo}</div>
                {visibles.map((item) => (
                  <NavLink key={item.to} to={item.to} className={navItemClass}>
                    <i className={`fa-solid ${item.icono}`}></i> {item.texto}
                  </NavLink>
                ))}
              </div>
            );
          })}
        </div>

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
