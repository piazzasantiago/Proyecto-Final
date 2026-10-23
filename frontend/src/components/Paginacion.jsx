import { useState } from "react";

/** Opciones de "elementos por página" que ofrece la barra. */
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
 * Números de página a mostrar, con "…" para los tramos omitidos. Siempre
 * incluye la primera, la última y las vecinas de la actual:
 * El ancho es constante (9 elementos) para que la barra no "salte" al cambiar
 * de página:
 *   total 5             -> 1 2 3 4 5
 *   total 20, actual 1  -> 1 2 3 4 5 6 7 … 20
 *   total 20, actual 9  -> 1 … 7 8 9 10 11 … 20
 *   total 20, actual 20 -> 1 … 14 15 16 17 18 19 20
 */
export function numerosDePagina(actual, total, vecinas = 2) {
  const visibles = vecinas * 2 + 5; // primera, última, actual, vecinas y 2 "…"
  if (total <= visibles) return Array.from({ length: total }, (_, i) => i + 1);

  // Ventana de números alrededor de la actual, sin salirse de 2..total-1;
  // pegada al borde cuando la actual está cerca del principio o del final.
  const largo = vecinas * 2 + 3;
  let desde = Math.max(2, actual - vecinas);
  let hasta = Math.min(total - 1, actual + vecinas);
  if (actual <= vecinas + 2) {
    desde = 2;
    hasta = largo;
  } else if (actual >= total - vecinas - 1) {
    hasta = total - 1;
    desde = total - largo + 1;
  }
  const paginas = [1];
  if (desde > 2) paginas.push("…");
  for (let n = desde; n <= hasta; n++) paginas.push(n);
  if (hasta < total - 1) paginas.push("…");
  paginas.push(total);
  return paginas;
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
 *                     el selector de "Elementos por página"
 *
 * Se muestra siempre que haya registros, aunque haya una sola página: en ese caso
 * el único número queda activo y Anterior / Siguiente deshabilitados. Cambiar los
 * elementos por página no altera lo que se ve si todo sigue entrando en una página.
 */
export default function Paginacion({ page, count, pageSize, onChange, onPageSizeChange }) {
  const totalPaginas = Math.max(1, Math.ceil(count / pageSize));
  if (count === 0) return null;

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
            Elementos por página
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
        <nav className="paginacion-numeros" aria-label="Páginas">
          {numerosDePagina(page, totalPaginas).map((n, i) =>
            n === "…" ? (
              <span key={`gap-${i}`} className="paginacion-puntos">
                …
              </span>
            ) : (
              <button
                key={n}
                className={`paginacion-numero ${n === page ? "activo" : ""}`}
                onClick={() => n !== page && onChange(n)}
                aria-label={`Página ${n}`}
                aria-current={n === page ? "page" : undefined}
              >
                {n}
              </button>
            )
          )}
        </nav>
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
