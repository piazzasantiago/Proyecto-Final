import { useCallback, useEffect, useMemo, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { MENU } from "../config/menu";
import { marcarTutorialVisto, pasosParaRol, tutorialVisto } from "../config/tutorial";
import { marcarSeccionVista, pasosSeccion, seccionesVistas } from "../config/tutorialSecciones";
import MarcaSidebar from "../components/MarcaSidebar";
import LogoAvigest from "../components/LogoAvigest";
import BarraInferior from "../components/BarraInferior";
import HojaMenu from "../components/HojaMenu";
import Tutorial from "../components/Tutorial";
import { TutorialContext } from "../components/TutorialContext";
import useTema from "../components/useTema";
import { useAuth } from "../context/AuthContext";
import { activarMovil, cerrarDetalleMovil } from "../utils/movil";

const navItemClass = ({ isActive }) => `sb-item${isActive ? " active" : ""}`;

/** "Producción" -> "produccion": identifica cada grupo del menú para el tutorial. */
const idGrupo = (nombre) => nombre.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");

/** Iniciales para el avatar: "Juan Pérez" -> "JP". */
function iniciales(usuario) {
  if (!usuario) return "?";
  return `${usuario.nombre?.[0] ?? ""}${usuario.apellido?.[0] ?? ""}`.toUpperCase();
}

export default function AppLayout() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { usuario, cerrarSesion } = useAuth();
  const { esOscuro, alternar } = useTema();
  // Controla el sidebar como panel deslizante en tablet/celular.
  const [sidebarOpen, setSidebarOpen] = useState(false);
  // Tutorial guiado: el general arranca solo la primera vez que el usuario entra y se repite con un
  // botón del menú; cada sección tiene el suyo, con el botón "?" de su encabezado.
  // `guia` es null (nada abierto), "general" o el id de una sección.
  const [guia, setGuia] = useState(null);
  const [hojaMenu, setHojaMenu] = useState(null); // celular: "mas" | "cuenta" | null
  const [vistas, setVistas] = useState(() => seccionesVistas(usuario));
  const [marcaLista, setMarcaLista] = useState(false);
  const avisarMarcaLista = useCallback(() => setMarcaLista(true), []);

  useEffect(() => {
    if (!marcaLista || !usuario || tutorialVisto(usuario)) return undefined;
    const t = setTimeout(() => setGuia("general"), 400);
    return () => clearTimeout(t);
  }, [marcaLista, usuario]);

  // Pantallas chicas: el detalle como hoja desde abajo y títulos en las tablas (utils/movil.js).
  useEffect(() => activarMovil(), []);
  useEffect(() => { cerrarDetalleMovil(); setHojaMenu(null); }, [pathname]);
  useEffect(() => {
    if (!hojaMenu) return undefined;
    const alTeclear = (e) => e.key === "Escape" && setHojaMenu(null);
    document.addEventListener("keydown", alTeclear);
    return () => document.removeEventListener("keydown", alTeclear);
  }, [hojaMenu]);

  const cerrarTutorial = useCallback(() => {
    if (guia === "general") {
      marcarTutorialVisto(usuario);
    } else if (guia) {
      marcarSeccionVista(usuario, guia);
      setVistas(seccionesVistas(usuario));
    }
    setGuia(null);
  }, [guia, usuario]);

  const contextoTutorial = useMemo(
    () => ({
      iniciarSeccion: (id) => setGuia(id),
      seccionVista: (id) => vistas.includes(id),
    }),
    [vistas],
  );

  async function handleLogout() {
    await cerrarSesion();
    navigate("/login", { replace: true });
  }

  const rol = usuario?.rol;

  return (
    <TutorialContext.Provider value={contextoTutorial}>
    <div className="screen active" id="screen-app">
      <button
        type="button"
        className="mobile-topbar-toggle"
        aria-label="Abrir menú"
        onClick={() => setSidebarOpen(true)}
      >
        <i className="fa-solid fa-bars"></i>
      </button>

      <button type="button" className="topbar-avatar" aria-label="Mi cuenta" onClick={() => setHojaMenu("cuenta")}>{iniciales(usuario)}</button>

      <div className="topbar-vidrio" aria-hidden="true"><span className="topbar-titulo"></span><LogoAvigest compacto /></div>

      <div className="detalle-velo" onClick={cerrarDetalleMovil} aria-hidden="true"></div>

      {sidebarOpen && (
        <div
          className="sidebar-overlay"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        ></div>
      )}

      <div className={`sidebar${sidebarOpen ? " open" : ""}`} data-tutorial="menu">
        <div className="sb-brand">
          <MarcaSidebar onLista={avisarMarcaLista} />
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
              <div key={grupo.grupo} data-tutorial={`menu-${idGrupo(grupo.grupo)}`}>
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
            data-tutorial="btn-tutorial"
            onClick={() => setGuia("general")}
          >
            <i className="fa-solid fa-circle-question"></i> Ver tutorial
          </button>
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

      <BarraInferior rol={rol} onMas={() => setHojaMenu("mas")} />

      {hojaMenu && (
        <HojaMenu
          modo={hojaMenu}
          rol={rol}
          usuario={usuario}
          iniciales={iniciales(usuario)}
          esOscuro={esOscuro}
          onTema={alternar}
          onTutorial={() => { setHojaMenu(null); setGuia("general"); }}
          onSalir={handleLogout}
          onCerrar={() => setHojaMenu(null)}
        />
      )}

      {guia && (
        <Tutorial
          key={guia}
          pasos={guia === "general" ? pasosParaRol(rol) : pasosSeccion(guia, rol)}
          onCerrar={cerrarTutorial}
          abrirMenu={setSidebarOpen}
        />
      )}
    </div>
    </TutorialContext.Provider>
  );
}
