import request from "./client";

export function listMateriasPrimas(params = {}) {
  const query = new URLSearchParams(params).toString();
  return request(`/api/materias-primas/${query ? `?${query}` : ""}`);
}

export function getMateriaPrima(id) {
  return request(`/api/materias-primas/${id}/`);
}

export function createMateriaPrima(data) {
  return request(`/api/materias-primas/`, { method: "POST", body: JSON.stringify(data) });
}

export function updateMateriaPrima(id, data) {
  return request(`/api/materias-primas/${id}/`, { method: "PATCH", body: JSON.stringify(data) });
}

export function deleteMateriaPrima(id) {
  return request(`/api/materias-primas/${id}/`, { method: "DELETE" });
}

/** CU59 — Dar de Alta (activar) Materia Prima */
export function activarMateriaPrima(id) {
  return request(`/api/materias-primas/${id}/activar/`, { method: "POST" });
}

/** CU60 — Dar de Baja (desactivar) Materia Prima */
export function desactivarMateriaPrima(id) {
  return request(`/api/materias-primas/${id}/desactivar/`, { method: "POST" });
}

/** Materias primas con nombre igual o parecido (ignora mayúsculas y tildes). */
export function buscarSimilares(nombre, excluirId) {
  const params = new URLSearchParams({ nombre });
  if (excluirId) params.set("excluir", excluirId);
  return request(`/api/materias-primas/similares/?${params.toString()}`);
}
