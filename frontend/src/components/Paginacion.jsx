/**
 * Barra de paginación reutilizable para listados paginados por el backend.
 *
 * Props:
 *   page      página actual (empieza en 1)
 *   count     cantidad total de registros (el `count` que devuelve DRF)
 *   pageSize  registros por página (debe coincidir con el `page_size` pedido)
 *   onChange  recibe el número de página a la que ir
 *
 * No se muestra si todo entra en una sola página.
 */
export default function Paginacion({ page, count, pageSize, onChange }) {
  const totalPaginas = Math.max(1, Math.ceil(count / pageSize));
  if (count <= pageSize) return null;

  const desde = (page - 1) * pageSize + 1;
  const hasta = Math.min(page * pageSize, count);

  return (
    <div className="paginacion">
      <span className="paginacion-info">
        Mostrando {desde.toLocaleString("es-AR")}–{hasta.toLocaleString("es-AR")} de{" "}
        {count.toLocaleString("es-AR")}
      </span>
      <div className="paginacion-controles">
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
