import request from "./client";

export function listLotes(params = {}) {
  const query = new URLSearchParams(params).toString();
  return request(`/api/lotes/${query ? `?${query}` : ""}`);
}

export function getLote(id) {
  return request(`/api/lotes/${id}/`);
}

export function createLote(data) {
  return request(`/api/lotes/`, { method: "POST", body: JSON.stringify(data) });
}

export function updateLote(id, data) {
  return request(`/api/lotes/${id}/`, { method: "PATCH", body: JSON.stringify(data) });
}

export function deleteLote(id) {
  return request(`/api/lotes/${id}/`, { method: "DELETE" });
}

/** CU46 — Iniciar Producción (Transición → Producción) */
export function iniciarProduccion(id) {
  return request(`/api/lotes/${id}/iniciar-produccion/`, { method: "POST" });
}

/** CU48 — Vaciado sanitario (→ Finalizado) */
export function vaciarLote(id) {
  return request(`/api/lotes/${id}/vaciar/`, { method: "POST" });
}
