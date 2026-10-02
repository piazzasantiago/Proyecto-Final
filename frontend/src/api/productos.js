import request from "./client";

export function listProductos(params = {}) {
  const query = new URLSearchParams(params).toString();
  return request(`/api/productos/${query ? `?${query}` : ""}`);
}

export function getProducto(id) {
  return request(`/api/productos/${id}/`);
}

export function createProducto(data) {
  return request(`/api/productos/`, { method: "POST", body: JSON.stringify(data) });
}

export function updateProducto(id, data) {
  return request(`/api/productos/${id}/`, { method: "PATCH", body: JSON.stringify(data) });
}

export function deleteProducto(id) {
  return request(`/api/productos/${id}/`, { method: "DELETE" });
}

/** CU51 — Activar Producto */
export function activarProducto(id) {
  return request(`/api/productos/${id}/activar/`, { method: "POST" });
}

/** CU54 — Desactivar Producto */
export function desactivarProducto(id) {
  return request(`/api/productos/${id}/desactivar/`, { method: "POST" });
}
