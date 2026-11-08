import { useRef } from "react";
import { NavLink } from "react-router-dom";

import { MENU } from "../config/menu";

// Los accesos que ya están en la barra inferior no se repiten en la hoja «Más».
const idGrupo = (nombre) => nombre.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
const EN_BARRA = ["/app/dashboard", "/app/galpones", "/app/lotes", "/app/recoleccion"];

/**
 * Hoja que sube desde abajo en el celular (reemplaza al menú lateral en pantallas chicas):
 *   - modo "mas":    el resto de las secciones, en una grilla de íconos agrupada.
 *   - modo "cuenta": datos del usuario, modo oscuro, tutorial y cerrar sesión.
 * Se cierra con la X, tocando afuera, arrastrándola hacia abajo o con Escape (lo maneja el padre).
 */
export default function HojaMenu({ modo, rol, usuario, iniciales, esOscuro, onTema, onTutorial, onSalir, onCerrar }) {
  const arrastre = useRef(null);
  const hoja = useRef(null);

  const grupos = MENU.map((g) => ({ ...g, items: g.items.filter((i) => !EN_BARRA.includes(i.to) && i.roles.includes(rol)) })).filter(
    (g) => g.items.length > 0
  );

  // Arrastrar hacia abajo desde el asa: sigue al dedo y, al soltar, cierra si fue lejos o rápido.
  function abajo(e) {
    arrastre.current = { y0: e.clientY, t0: performance.now(), dy: 0, id: e.pointerId };
    e.currentTarget.setPointerCapture(e.pointerId);
    hoja.current.style.transition = "none";
  }
  function mover(e) {
    const a = arrastre.current;
    if (!a) return;
    a.dy = Math.max(e.clientY - a.y0, 0);
    hoja.current.style.transform = `translateY(${a.dy}px)`;
  }
  function soltar() {
    const a = arrastre.current;
    arrastre.current = null;
    if (!a) return;
    const v = a.dy / Math.max(performance.now() - a.t0, 1); // px/ms
    if (a.dy > 110 || v > 0.7) {
      hoja.current.style.transition = "transform .25s ease-in";
      hoja.current.style.transform = "translateY(100%)";
      setTimeout(onCerrar, 220);
    } else {
      hoja.current.style.transition = "transform .45s var(--resorte)";
      hoja.current.style.transform = "";
    }
  }

  return (
    <>
      <div className="hoja-menu-velo" onClick={onCerrar} aria-hidden="true"></div>
      <div className="hoja-menu" ref={hoja} role="dialog" aria-label={modo === "mas" ? "Más secciones" : "Mi cuenta"}>
        <div className="hoja-menu-asa" onPointerDown={abajo} onPointerMove={mover} onPointerUp={soltar} onPointerCancel={soltar}>
          <span></span>
        </div>

        {modo === "mas" ? (
          <div className="hoja-menu-cuerpo">
            {grupos.map((g) => (
              <section key={g.grupo} data-tutorial={`hoja-${idGrupo(g.grupo)}`}>
                <h4>{g.grupo}</h4>
                <div className="hoja-grilla">
                  {g.items.map((item) => (
                    <NavLink key={item.to} to={item.to} className="hoja-tile" onClick={onCerrar}>
                      <i className={`fa-solid ${item.icono}`}></i>
                      <span>{item.texto}</span>
                    </NavLink>
                  ))}
                </div>
              </section>
            ))}
          </div>
        ) : (
          <div className="hoja-menu-cuerpo">
            <div className="hoja-cuenta">
              <div className="sb-avatar">{iniciales}</div>
              <div>
                <b>{usuario?.nombre_completo}</b>
                <span>{usuario?.rol_display}</span>
              </div>
            </div>
            <div className="hoja-acciones">
              <button type="button" onClick={onTema} aria-pressed={esOscuro}>
                <i className={`fa-solid ${esOscuro ? "fa-sun" : "fa-moon"}`}></i> {esOscuro ? "Modo claro" : "Modo oscuro"}
              </button>
              <button type="button" onClick={onTutorial} data-tutorial="hoja-tutorial">
                <i className="fa-solid fa-circle-question"></i> Ver tutorial
              </button>
              <button type="button" className="peligro" onClick={onSalir}>
                <i className="fa-solid fa-right-from-bracket"></i> Cerrar sesión
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
