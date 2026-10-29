import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

/** Fecha y hora local (dd/mm/aaaa hh:mm). */
function formatFechaHora(iso) {
  if (!iso) return "";
  const f = new Date(iso);
  if (Number.isNaN(f.getTime())) return "";
  return f.toLocaleString("es-AR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function Evento({ titulo, evento, vacio }) {
  const fecha = formatFechaHora(evento?.fecha);
  const por = evento?.por;
  return (
    <div className="auditoria-fila">
      <div className="auditoria-titulo">{titulo}</div>
      {fecha || por ? (
        <>
          <div className="auditoria-quien">
            {por ? `${por.nombre} (${por.usuario})` : "Sistema"}
          </div>
          {fecha && <div className="auditoria-cuando">{fecha}</div>}
        </>
      ) : (
        <div className="auditoria-vacio">{vacio}</div>
      )}
    </div>
  );
}

const ANCHO_TARJETA = 290;

/** Contenido compartido por la tarjeta al pasar el cursor y por la ventana. */
function Eventos({ auditoria, conFinalizacion }) {
  return (
    <>
      <Evento titulo="Creado" evento={auditoria.creado} vacio="Sin registro" />
      <Evento titulo="Última edición" evento={auditoria.editado} vacio="Sin ediciones" />
      {conFinalizacion && (
        <Evento titulo="Finalizado" evento={auditoria.finalizado} vacio="Todavía no finalizó" />
      )}
    </>
  );
}

/**
 * Botón «ojito» del panel de detalle: abre la ventana «Historial» con quién y cuándo
 * creó, editó y finalizó el registro (F-23).
 *
 * `auditoria` es el campo que manda el backend; solo llega para Administrador
 * y Consulta, así que para el resto el botón no aparece. `conFinalizacion`
 * es true en los módulos cuyos registros se finalizan (compras, entradas,
 * salidas, recolecciones, descartes y lotes).
 *
 * Al pasar el cursor (o enfocar el botón con el teclado) aparece una tarjeta con el
 * mismo contenido; el clic abre la ventana, que también sirve en pantallas táctiles.
 */
export default function AuditoriaBoton({ auditoria, conFinalizacion = false }) {
  const [abierto, setAbierto] = useState(false);
  const [tarjeta, setTarjeta] = useState(null); // { left, top } de la tarjeta al pasar el cursor
  const botonRef = useRef(null);
  const temporizador = useRef(null);

  function mostrarTarjeta() {
    clearTimeout(temporizador.current);
    temporizador.current = setTimeout(() => {
      const caja = botonRef.current?.getBoundingClientRect();
      if (!caja) return;
      const alto = conFinalizacion ? 220 : 160; // estimado, para decidir si va arriba o abajo
      const left = Math.min(Math.max(caja.right - ANCHO_TARJETA, 8), window.innerWidth - ANCHO_TARJETA - 8);
      const abajo = caja.bottom + 8 + alto <= window.innerHeight;
      setTarjeta({ left, ...(abajo ? { top: caja.bottom + 8 } : { bottom: window.innerHeight - caja.top + 8 }) });
    }, 150);
  }

  function ocultarTarjeta() {
    clearTimeout(temporizador.current);
    setTarjeta(null);
  }

  useEffect(() => () => clearTimeout(temporizador.current), []);

  useEffect(() => {
    if (!abierto) return undefined;
    const alTeclear = (e) => e.key === "Escape" && setAbierto(false);
    window.addEventListener("keydown", alTeclear);
    return () => window.removeEventListener("keydown", alTeclear);
  }, [abierto]);

  if (!auditoria) return null;

  return (
    <>
      <button
        type="button"
        className="icon-btn auditoria-btn"
        title="Ver historial"
        aria-label="Ver historial"
        ref={botonRef}
        onClick={() => {
          ocultarTarjeta();
          setAbierto(true);
        }}
        onMouseEnter={mostrarTarjeta}
        onMouseLeave={ocultarTarjeta}
        onFocus={mostrarTarjeta}
        onBlur={ocultarTarjeta}
      >
        <i className="fa-solid fa-eye"></i>
      </button>
      {tarjeta &&
        !abierto &&
        createPortal(
          <div className="auditoria-pop" role="tooltip" style={{ ...tarjeta, width: ANCHO_TARJETA }}>
            <Eventos auditoria={auditoria} conFinalizacion={conFinalizacion} />
          </div>,
          document.body
        )}
      {abierto && (
        <div
          className="modal-overlay active"
          onClick={(e) => e.target === e.currentTarget && setAbierto(false)}
        >
          <div className="modal-card modal-card-sm" role="dialog" aria-label="Historial">
            <div className="modal-header">
              <h3>Historial</h3>
              <button className="modal-close" onClick={() => setAbierto(false)}>
                <i className="fa-solid fa-xmark"></i>
              </button>
            </div>
            <div className="modal-body">
              <Eventos auditoria={auditoria} conFinalizacion={conFinalizacion} />
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-outline" onClick={() => setAbierto(false)}>
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
