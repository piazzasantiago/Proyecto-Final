import request from "./client";

export function listEntradas(params = {}) {
  const query = new URLSearchParams(params).toString();
  return request(`/api/entradas/${query ? `?${query}` : ""}`);
}

export function getEntrada(id) {
  return request(`/api/entradas/${id}/`);
}

export function createEntrada(data) {
  return request(`/api/entradas/`, { method: "POST", body: JSON.stringify(data) });
}

export function updateEntrada(id, data) {
  return request(`/api/entradas/${id}/`, { method: "PATCH", body: JSON.stringify(data) });
}

export function deleteEntrada(id) {
  return request(`/api/entradas/${id}/`, { method: "DELETE" });
}

/** CU37 — Finalizar entrada (queda de solo lectura; descuenta el stock de cada materia prima) */
export function finalizarEntrada(id) {
  return request(`/api/entradas/${id}/finalizar/`, { method: "POST" });
}
