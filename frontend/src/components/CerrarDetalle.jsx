import { cerrarDetalleMovil } from "../utils/movil";

/**
 * Encabezado de la hoja de detalle en pantallas chicas: el asa para arrastrar (solo decorativa) y
 * el botón para cerrar. En pantalla ancha no se muestra (ver index.css).
 */
export default function CerrarDetalle() {
  return (
    <div className="detalle-cerrar">
      <span className="detalle-asa" aria-hidden="true"></span>
      <button type="button" className="detalle-x" onClick={cerrarDetalleMovil} aria-label="Cerrar el detalle">
        <i className="fa-solid fa-xmark"></i>
      </button>
    </div>
  );
}
