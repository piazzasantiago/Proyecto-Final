import request from "./client";

export function listSalidas(params = {}) {
  const query = new URLSearchParams(params).toString();
  return request(`/api/salidas/${query ? `?${query}` : ""}`);
}

export function getSalida(id) {
  return request(`/api/salidas/${id}/`);
}

export function createSalida(data) {
  return request(`/api/salidas/`, { method: "POST", body: JSON.stringify(data) });
}

export function updateSalida(id, data) {
  return request(`/api/salidas/${id}/`, { method: "PATCH", body: JSON.stringify(data) });
}

export function deleteSalida(id) {
  return request(`/api/salidas/${id}/`, { method: "DELETE" });
}

/** Finalizar salida (queda de solo lectura; descuenta el stock de cada producto) */
export function finalizarSalida(id) {
  return request(`/api/salidas/${id}/finalizar/`, { method: "POST" });
}
