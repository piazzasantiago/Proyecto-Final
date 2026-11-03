import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { MENU } from "../config/menu";
import useTema from "../components/useTema";
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
  const { esOscuro, alternar } = useTema();
  // Controla el sidebar como panel deslizante en tablet/celular.
  const [sidebarOpen, setSidebarOpen] = useState(false);

  async function handleLogout() {
    await cerrarSesion();
    navigate("/login", { replace: true });
  }

  const rol = usuario?.rol;

  return (
    <div className="screen active" id="screen-app">
      <button
        type="button"
        className="mobile-topbar-toggle"
        aria-label="Abrir menú"
        onClick={() => setSidebarOpen(true)}
      >
        <i className="fa-solid fa-bars"></i>
      </button>

      {sidebarOpen && (
        <div
          className="sidebar-overlay"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        ></div>
      )}

      <div className={`sidebar${sidebarOpen ? " open" : ""}`}>
        <div className="sb-brand">
          <div className="logo-mark"><i className="fa-solid fa-egg"></i></div>
          <span>AvíGest</span>
          <button
            type="button"
            className="sidebar-close"
            aria-label="Cerrar menú"
            onClick={() => setSidebarOpen(false)}
          >
            <i className="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div className="sb-nav" onClick={() => setSidebarOpen(false)}>
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
          <button
            type="button"
            className="sb-tema"
            onClick={alternar}
            aria-pressed={esOscuro}
            title={esOscuro ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
          >
            <i className={`fa-solid ${esOscuro ? "fa-sun" : "fa-moon"}`}></i>
            {esOscuro ? "Modo claro" : "Modo oscuro"}
          </button>
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
