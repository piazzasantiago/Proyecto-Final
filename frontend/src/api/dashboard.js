import request from "./client";

/**
 * Resumen del panel principal: indicadores del día, producción de la última
 * semana, stock de productos y alertas recientes, todo en una sola petición.
 */
export function getResumenDashboard() {
  return request(`/api/dashboard/resumen/`);
}

/** Alertas de los lotes. Admite ?estado=P|R, ?id_lote= y ?id_galpon=. */
export function listAlertas(params = {}) {
  const query = new URLSearchParams(params).toString();
  return request(`/api/alertas/${query ? `?${query}` : ""}`);
}
