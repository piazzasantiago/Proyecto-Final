/**
 * Recorre todas las páginas de un listado paginado de DRF y devuelve los
 * resultados juntos.
 *
 * Los listados del backend vienen paginados (16 por página). Esto es para los
 * desplegables y catálogos que necesitan TODOS los registros (galpones, lotes,
 * productos, etc.) y no una sola página. Las tablas y tarjetas usan, en cambio,
 * paginación del servidor con el componente <Paginacion />.
 */
export async function traerTodas(listFn, params = {}) {
  const resultados = [];
  for (let page = 1; page <= 50; page++) {
    const data = await listFn({ ...params, page, page_size: 100 });
    if (Array.isArray(data)) return data;
    resultados.push(...data.results);
    if (!data.next) break;
  }
  return resultados;
}
