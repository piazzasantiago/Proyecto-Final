import request from "./client";

/** CU70 — Buscar proveedores (search, estado, ordering). */
export function listProveedores(params = {}) {
  const query = new URLSearchParams(params).toString();
  return request(`/api/proveedores/${query ? `?${query}` : ""}`);
}

export function getProveedor(id) {
  return request(`/api/proveedores/${id}/`);
}

/** CU71 — Nuevo proveedor */
export function createProveedor(data) {
  return request(`/api/proveedores/`, { method: "POST", body: JSON.stringify(data) });
}

/** CU72 — Modificar proveedor */
export function updateProveedor(id, data) {
  return request(`/api/proveedores/${id}/`, { method: "PATCH", body: JSON.stringify(data) });
}

/** CU73 — Borrar proveedor */
export function deleteProveedor(id) {
  return request(`/api/proveedores/${id}/`, { method: "DELETE" });
}

/** CU74 — Dar de alta proveedor */
export function altaProveedor(id) {
  return request(`/api/proveedores/${id}/alta/`, { method: "POST" });
}

/** CU75 — Dar de baja proveedor */
export function bajaProveedor(id) {
  return request(`/api/proveedores/${id}/baja/`, { method: "POST" });
}

/** Proveedores con nombre igual o parecido (ignora mayúsculas y tildes). */
export function buscarSimilares(nombre, excluirId) {
  const params = new URLSearchParams({ nombre });
  if (excluirId) params.set("excluir", excluirId);
  return request(`/api/proveedores/similares/?${params.toString()}`);
}
