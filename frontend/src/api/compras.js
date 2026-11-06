import request from "./client";

/** Buscar compras (search por Nº de comprobante, categoria, estado, id_proveedor, fecha_desde, fecha_hasta). */
export function listCompras(params = {}) {
  const query = new URLSearchParams(params).toString();
  return request(`/api/compras/${query ? `?${query}` : ""}`);
}

export function getCompra(id) {
  return request(`/api/compras/${id}/`);
}

export function createCompra(data) {
  return request(`/api/compras/`, { method: "POST", body: JSON.stringify(data) });
}

export function updateCompra(id, data) {
  return request(`/api/compras/${id}/`, { method: "PATCH", body: JSON.stringify(data) });
}

export function deleteCompra(id) {
  return request(`/api/compras/${id}/`, { method: "DELETE" });
}

/** Número de comprobante con el que se guardaría la próxima compra (estimación). */
export function getProximoComprobante() {
  return request(`/api/compras/proximo-comprobante/`);
}

/** Finalizar compra (queda de solo lectura; suma stock o deja lotes por asignar) */
export function finalizarCompra(id) {
  return request(`/api/compras/${id}/finalizar/`, { method: "POST" });
}

/** Lotes comprados (compras finalizadas) que todavía no se asignaron a un galpón. */
export function listLotesPendientes() {
  return request(`/api/compras/lotes-pendientes/`);
}
