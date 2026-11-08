import { NavLink, useLocation } from "react-router-dom";

import { MENU } from "../config/menu";

// Accesos fijos de la barra inferior del celular (los de uso diario). El resto está en "Más".
const FIJOS = ["/app/dashboard", "/app/galpones", "/app/lotes", "/app/recoleccion"];
const NOMBRES = { "/app/dashboard": "Inicio", "/app/galpones": "Galpones", "/app/lotes": "Lotes", "/app/recoleccion": "Recolección" };

/**
 * Barra de navegación inferior (solo celular, ver index.css): al alcance del pulgar. Muestra los
 * cuatro accesos de uso diario y "Más", que abre el menú completo. Respeta los roles del menú.
 */
export default function BarraInferior({ rol, onMas }) {
  const { pathname } = useLocation();
  const items = MENU.flatMap((g) => g.items).filter((i) => FIJOS.includes(i.to) && i.roles.includes(rol));
  const enFijos = items.some((i) => pathname.startsWith(i.to));

  return (
    <nav className="barra-inferior" aria-label="Navegación principal" data-tutorial="barra-inferior">
      {items.map((item) => (
        <NavLink key={item.to} to={item.to} className={({ isActive }) => `bi-item${isActive ? " activo" : ""}`}>
          <i className={`fa-solid ${item.icono}`}></i>
          <span>{NOMBRES[item.to]}</span>
        </NavLink>
      ))}
      <button type="button" className={`bi-item${enFijos ? "" : " activo"}`} onClick={onMas} data-tutorial="boton-mas">
        <i className="fa-solid fa-ellipsis"></i>
        <span>Más</span>
      </button>
    </nav>
  );
}
