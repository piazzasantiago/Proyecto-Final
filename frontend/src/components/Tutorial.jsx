import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

const MARGEN = 8; // aire alrededor del elemento resaltado
const ESPACIO = 14; // separación entre el elemento y la tarjeta
const BORDE = 12; // distancia mínima de la tarjeta al borde de la ventana
const ESPERA_MAX = 4000; // cuánto se espera a que aparezca el elemento antes de saltar el paso
const CELULAR = "(max-width: 1100px)";
const PANTALLA_CHICA = "(max-width: 700px)";

const buscar = (objetivo) => document.querySelector(`[data-tutorial="${objetivo}"]`);
const sinMovimiento = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const limitar = (v, min, max) => Math.max(min, Math.min(v, max));

/**
 * Calcula dónde poner la tarjeta: al lado del elemento resaltado si entra,
 * y si no, en el borde de la pantalla. Sin elemento, queda centrada.
 */
function ubicar(rect, ancho, alto, lados) {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  if (!rect) return { top: (vh - alto) / 2, left: (vw - ancho) / 2 };

  if (window.matchMedia(PANTALLA_CHICA).matches) {
    const arriba = rect.top + rect.height / 2 > vh / 2;
    return { top: arriba ? BORDE : vh - alto - BORDE, left: (vw - ancho) / 2 };
  }

  const centroX = limitar(rect.left + rect.width / 2 - ancho / 2, BORDE, vw - ancho - BORDE);
  const centroY = limitar(rect.top + rect.height / 2 - alto / 2, BORDE, vh - alto - BORDE);
  const opciones = {
    derecha: { top: centroY, left: rect.right + MARGEN + ESPACIO, cabe: rect.right + MARGEN + ESPACIO + ancho <= vw - BORDE },
    izquierda: { top: centroY, left: rect.left - MARGEN - ESPACIO - ancho, cabe: rect.left - MARGEN - ESPACIO - ancho >= BORDE },
    abajo: { top: rect.bottom + MARGEN + ESPACIO, left: centroX, cabe: rect.bottom + MARGEN + ESPACIO + alto <= vh - BORDE },
    arriba: { top: rect.top - MARGEN - ESPACIO - alto, left: centroX, cabe: rect.top - MARGEN - ESPACIO - alto >= BORDE },
  };
  for (const lado of lados) {
    if (opciones[lado].cabe) return opciones[lado];
  }
  // Ningún lado entra (elemento muy grande): la tarjeta va abajo, sobre el elemento.
  return { top: vh - alto - BORDE, left: centroX };
}

/**
 * Tutorial guiado: oscurece la pantalla, resalta un elemento por vez y explica para qué sirve.
 *
 * Se puede omitir en cualquier momento (botón, Esc o tocar "Omitir"), y se recorre con los
 * botones o con las flechas del teclado.
 *
 *   pasos      lista de pasos (config/tutorial.js)
 *   onCerrar   se llama al terminar o al omitir
 *   abrirMenu  abre o cierra el menú lateral (en tablet el menú es un panel que se desliza)
 *   abrirHoja  abre la hoja «Más» o «Mi cuenta» del celular ("mas", "cuenta") o la cierra (null)
 *
 * En celular (hasta 700 px) no hay menú lateral: cada paso puede traer `movil` con otro objetivo,
 * otra hoja abierta y otro texto (ver config/tutorial.js).
 */
export default function Tutorial({ pasos: todos, onCerrar, abrirMenu, abrirHoja = () => {} }) {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [indice, setIndice] = useState(0);
  const [elemento, setElemento] = useState(null);
  const [rect, setRect] = useState(null);
  const [pos, setPos] = useState(null);
  const tarjetaRef = useRef(null);
  const siguienteRef = useRef(null);
  const direccion = useRef(1); // hacia dónde se iba al llegar al paso: si hay que saltarlo, sigue igual
  const chico = window.matchMedia(PANTALLA_CHICA).matches;
  // Los pasos "soloMovil" (botón Más, perfil) no existen en pantallas grandes.
  const pasos = useMemo(() => todos.filter((p) => !p.soloMovil || chico), [todos, chico]);
  const base = pasos[indice];
  // Misma referencia mientras no cambie el paso: otros efectos dependen de ella.
  const paso = useMemo(
    () => (chico && base.movil ? { ...base, ...base.movil, texto: base.movil.texto || base.texto } : base),
    [chico, base],
  );
  const esUltimo = indice === pasos.length - 1;

  const cerrar = useCallback(() => {
    abrirMenu(false);
    abrirHoja(null);
    onCerrar();
  }, [abrirMenu, abrirHoja, onCerrar]);

  const ir = useCallback(
    (delta) => {
      direccion.current = delta;
      const destino = indice + delta;
      if (destino < 0) return;
      if (destino >= pasos.length) {
        cerrar();
        return;
      }
      setElemento(null); // la marca anterior queda hasta encontrar la nueva, así se desliza de una a otra
      setIndice(destino);
    },
    [indice, pasos.length, cerrar],
  );

  // Al entrar a un paso: ir a su pantalla, abrir o cerrar el menú y esperar el elemento.
  useEffect(() => {
    if (paso.ruta && pathname !== paso.ruta) navigate(paso.ruta);
    const enCelular = window.matchMedia(PANTALLA_CHICA).matches;
    abrirMenu(Boolean(paso.menu) && !enCelular && window.matchMedia(CELULAR).matches);
    abrirHoja(enCelular ? paso.hoja ?? null : null);
    if (!paso.objetivo) {
      setRect(null);
      return undefined;
    }

    const inicio = Date.now();
    let abierto = false;
    let abiertoEn = 0;
    const espera = setInterval(() => {
      const el = buscar(paso.objetivo);
      if (!el && paso.abrir && abierto && Date.now() - abiertoEn > 1200) {
        // Se tocó el primer registro y el elemento no apareció (p. ej. una compra ya finalizada no tiene
        // acciones): se salta el paso sin esperar el tiempo máximo.
        clearInterval(espera);
        ir(direccion.current);
        return;
      }
      if (!el && paso.abrir && !abierto) {
        // El elemento aparece al elegir un registro: se toca el primero de la lista.
        abierto = true;
        abiertoEn = Date.now();
        const fila = document.querySelector("[data-tutorial-fila]");
        if (fila) fila.click();
        else {
          clearInterval(espera);
          ir(direccion.current); // lista vacía: no hay nada para mostrar
        }
        return;
      }
      if (el) {
        clearInterval(espera);
        el.scrollIntoView({ block: "center", inline: "nearest", behavior: sinMovimiento() ? "auto" : "smooth" });
        setElemento(el);
      } else if (Date.now() - inicio > ESPERA_MAX) {
        clearInterval(espera);
        ir(direccion.current); // el elemento no está (p. ej. sin datos): se salta el paso
      }
    }, 100);
    return () => clearInterval(espera);
    // El efecto es por paso; navigate, pathname e ir cambian en cada render y no deben reiniciarlo.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [indice]);

  // Sigue al elemento cuadro a cuadro: acompaña el desplazamiento, el cambio de tamaño y el menú que se desliza.
  useLayoutEffect(() => {
    if (!elemento) return undefined;
    let cuadro = 0;
    let ultimo = "";
    const medir = () => {
      const r = elemento.getBoundingClientRect();
      const clave = `${r.top.toFixed(1)}|${r.left.toFixed(1)}|${r.width.toFixed(1)}|${r.height.toFixed(1)}`;
      if (clave !== ultimo) {
        ultimo = clave;
        setRect({ top: r.top, left: r.left, width: r.width, height: r.height, right: r.right, bottom: r.bottom });
      }
      cuadro = requestAnimationFrame(medir);
    };
    medir();
    return () => cancelAnimationFrame(cuadro);
  }, [elemento]);

  // Posición de la tarjeta, con su tamaño real.
  useLayoutEffect(() => {
    const tarjeta = tarjetaRef.current;
    if (!tarjeta) return;
    if (paso.objetivo && (!elemento || !rect)) return; // todavía no se encontró el elemento
    const { width, height } = tarjeta.getBoundingClientRect();
    setPos(ubicar(paso.objetivo ? rect : null, width, height, paso.lado ?? ["abajo", "arriba", "derecha", "izquierda"]));
  }, [rect, elemento, indice, paso]);

  // Foco en el botón principal y teclado: Esc omite, flechas navegan, Tab no sale de la tarjeta.
  useEffect(() => {
    siguienteRef.current?.focus();
  }, [indice]);

  useEffect(() => {
    const teclas = (e) => {
      if (e.key === "Escape") cerrar();
      else if (e.key === "ArrowRight") ir(1);
      else if (e.key === "ArrowLeft") ir(-1);
      else if (e.key === "Tab") {
        const botones = tarjetaRef.current?.querySelectorAll("button");
        if (!botones?.length) return;
        const primero = botones[0];
        const final = botones[botones.length - 1];
        if (e.shiftKey && document.activeElement === primero) {
          e.preventDefault();
          final.focus();
        } else if (!e.shiftKey && document.activeElement === final) {
          e.preventDefault();
          primero.focus();
        }
      }
    };
    // Mientras dura la guía no se desplaza la página con la rueda ni con el dedo.
    const quieto = (e) => e.preventDefault();
    window.addEventListener("keydown", teclas);
    window.addEventListener("wheel", quieto, { passive: false });
    window.addEventListener("touchmove", quieto, { passive: false });
    return () => {
      window.removeEventListener("keydown", teclas);
      window.removeEventListener("wheel", quieto);
      window.removeEventListener("touchmove", quieto);
    };
  }, [cerrar, ir]);

  const conFoco = Boolean(paso.objetivo && rect);
  const cargando = Boolean(paso.objetivo && !elemento);

  return (
    <>
      <div className={`tut-velo${conFoco ? "" : " sin-foco"}`} aria-hidden="true" />
      {conFoco && (
        <div
          className="tut-foco"
          aria-hidden="true"
          style={{
            top: rect.top - MARGEN,
            left: rect.left - MARGEN,
            width: rect.width + MARGEN * 2,
            height: rect.height + MARGEN * 2,
          }}
        />
      )}
      <div
        ref={tarjetaRef}
        className="tut-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="tut-titulo"
        aria-describedby="tut-texto"
        style={pos && !cargando ? { top: pos.top, left: pos.left } : { top: 0, left: 0, opacity: 0, pointerEvents: "none" }}
      >
        <div className="tut-barra" aria-hidden="true">
          <span style={{ width: `${((indice + 1) / pasos.length) * 100}%` }} />
        </div>
        <h3 id="tut-titulo">{paso.titulo}</h3>
        <p id="tut-texto">{paso.texto}</p>
        <div className="tut-acciones">
          {!esUltimo && (
            <button type="button" className="tut-omitir" onClick={cerrar}>
              Omitir
            </button>
          )}
          <span className="tut-espacio" />
          {indice > 0 && (
            <button type="button" className="btn btn-outline" onClick={() => ir(-1)}>
              Anterior
            </button>
          )}
          <button type="button" className="btn btn-green" ref={siguienteRef} onClick={() => ir(1)}>
            {esUltimo ? "Finalizar" : "Siguiente"}
          </button>
        </div>
      </div>
    </>
  );
}
