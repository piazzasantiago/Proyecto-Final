import request from "./client";

export function listRecolecciones(params = {}) {
  const query = new URLSearchParams(params).toString();
  return request(`/api/recolecciones/${query ? `?${query}` : ""}`);
}

export function getRecoleccion(id) {
  return request(`/api/recolecciones/${id}/`);
}

export function createRecoleccion(data) {
  return request(`/api/recolecciones/`, { method: "POST", body: JSON.stringify(data) });
}

export function updateRecoleccion(id, data) {
  return request(`/api/recolecciones/${id}/`, { method: "PATCH", body: JSON.stringify(data) });
}

export function deleteRecoleccion(id) {
  return request(`/api/recolecciones/${id}/`, { method: "DELETE" });
}

export function finalizarRecoleccion(id) {
  return request(`/api/recolecciones/${id}/finalizar/`, { method: "POST" });
}