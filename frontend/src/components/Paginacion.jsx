import { useState } from "react";

/** Opciones de "filas por página" que ofrece la barra. */
export const TAMANOS_PAGINA = [10, 16, 25, 50];

/**
 * Tamaño de página elegido por el usuario, recordado en este navegador.
 * Devuelve [tamano, setTamano]. Si no hay nada guardado (o no es una opción
 * válida) usa `porDefecto`.
 */
export function useTamanoPagina(clave, porDefecto = 16) {
  const almacenado = `avigest.filasPorPagina.${clave}`;
  const [tamano, setTamano] = useState(() => {
    try {
      const guardado = Number(window.localStorage.getItem(almacenado));
      return TAMANOS_PAGINA.includes(guardado) ? guardado : porDefecto;
    } catch {
      return porDefecto;
    }
  });

  function cambiar(nuevo) {
    setTamano(nuevo);
    try {
      window.localStorage.setItem(almacenado, String(nuevo));
    } catch {
      /* sin almacenamiento: la elección vale solo para esta visita */
    }
  }

  return [tamano, cambiar];
}

/**
 * Barra de paginación reutilizable para listados paginados por el backend.
 *
 * Props:
 *   page              página actual (empieza en 1)
 *   count             cantidad total de registros (el `count` que devuelve DRF)
 *   pageSize          registros por página (debe coincidir con el `page_size` pedido)
 *   onChange          recibe el número de página a la que ir
 *   onPageSizeChange  (opcional) recibe el nuevo tamaño; si se pasa, se muestra
 *                     el selector de "Filas por página"
 *
 * No se muestra si todo entra en la página más chica.
 */
export default function Paginacion({ page, count, pageSize, onChange, onPageSizeChange }) {
  const totalPaginas = Math.max(1, Math.ceil(count / pageSize));
  const minimo = onPageSizeChange ? Math.min(...TAMANOS_PAGINA) : pageSize;
  if (count <= minimo) return null;

  const desde = (page - 1) * pageSize + 1;
  const hasta = Math.min(page * pageSize, count);

  return (
    <div className="paginacion">
      <span className="paginacion-info">
        Mostrando {desde.toLocaleString("es-AR")}–{hasta.toLocaleString("es-AR")} de{" "}
        {count.toLocaleString("es-AR")}
      </span>
      <div className="paginacion-controles">
        {onPageSizeChange && (
          <label className="paginacion-tamano">
            Filas por página
            <select
              value={pageSize}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
            >
              {TAMANOS_PAGINA.map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
        )}
        <button
          className="btn btn-outline"
          onClick={() => onChange(page - 1)}
          disabled={page <= 1}
          aria-label="Página anterior"
        >
          <i className="fa-solid fa-chevron-left"></i> Anterior
        </button>
        <span className="paginacion-pagina">
          Página {page} de {totalPaginas}
        </span>
        <button
          className="btn btn-outline"
          onClick={() => onChange(page + 1)}
          disabled={page >= totalPaginas}
          aria-label="Página siguiente"
        >
          Siguiente <i className="fa-solid fa-chevron-right"></i>
        </button>
      </div>
    </div>
  );
}
