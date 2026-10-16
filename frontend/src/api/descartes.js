import request from "./client";

export function listDescartes(params = {}) {
  const query = new URLSearchParams(params).toString();
  return request(`/api/descartes/${query ? `?${query}` : ""}`);
}

export function getDescarte(id) {
  return request(`/api/descartes/${id}/`);
}

export function createDescarte(data) {
  return request(`/api/descartes/`, { method: "POST", body: JSON.stringify(data) });
}

export function updateDescarte(id, data) {
  return request(`/api/descartes/${id}/`, { method: "PATCH", body: JSON.stringify(data) });
}

export function deleteDescarte(id) {
  return request(`/api/descartes/${id}/`, { method: "DELETE" });
}

/** CU19 — Finalizar descarte (queda de solo lectura; descuenta gallinas del lote) */
export function finalizarDescarte(id) {
  return request(`/api/descartes/${id}/finalizar/`, { method: "POST" });
}
