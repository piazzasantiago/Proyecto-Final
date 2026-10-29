import { useEffect, useState } from "react";

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

/**
 * Botón «ojito» del panel de detalle: abre una ventana con quién y cuándo
 * creó, editó y finalizó el registro (F-23).
 *
 * `auditoria` es el campo que manda el backend; solo llega para Administrador
 * y Consulta, así que para el resto el botón no aparece. `conFinalizacion`
 * es true en los módulos cuyos registros se finalizan (compras, entradas,
 * salidas, recolecciones, descartes y lotes).
 */
export default function AuditoriaBoton({ auditoria, conFinalizacion = false }) {
  const [abierto, setAbierto] = useState(false);

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
        title="Ver auditoría"
        aria-label="Ver auditoría"
        onClick={() => setAbierto(true)}
      >
        <i className="fa-solid fa-eye"></i>
      </button>
      {abierto && (
        <div
          className="modal-overlay active"
          onClick={(e) => e.target === e.currentTarget && setAbierto(false)}
        >
          <div className="modal-card modal-card-sm" role="dialog" aria-label="Auditoría">
            <div className="modal-header">
              <h3>Auditoría</h3>
              <button className="modal-close" onClick={() => setAbierto(false)}>
                <i className="fa-solid fa-xmark"></i>
              </button>
            </div>
            <div className="modal-body">
              <Evento titulo="Creado" evento={auditoria.creado} vacio="Sin registro" />
              <Evento titulo="Última edición" evento={auditoria.editado} vacio="Sin ediciones" />
              {conFinalizacion && (
                <Evento titulo="Finalizado" evento={auditoria.finalizado} vacio="Todavía no finalizó" />
              )}
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
