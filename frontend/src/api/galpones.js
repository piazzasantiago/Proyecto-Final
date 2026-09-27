import request from "./client";

export function listGalpones(params = {}) {
  const query = new URLSearchParams(params).toString();
  return request(`/api/galpones/${query ? `?${query}` : ""}`);
}

export function getGalpon(id) {
  return request(`/api/galpones/${id}/`);
}

export function createGalpon(data) {
  return request(`/api/galpones/`, { method: "POST", body: JSON.stringify(data) });
}

export function updateGalpon(id, data) {
  return request(`/api/galpones/${id}/`, { method: "PATCH", body: JSON.stringify(data) });
}

export function deleteGalpon(id) {
  return request(`/api/galpones/${id}/`, { method: "DELETE" });
}

/** CU13 — Dar de Alta Galpón */
export function altaGalpon(id) {
  return request(`/api/galpones/${id}/alta/`, { method: "POST" });
}

/** CU14 — Dar de Baja Galpón */
export function bajaGalpon(id) {
  return request(`/api/galpones/${id}/baja/`, { method: "POST" });
}
