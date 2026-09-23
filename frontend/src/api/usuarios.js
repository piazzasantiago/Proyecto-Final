import request from "./client";

/** CU03 - Buscar Usuario. Acepta ?search=, ?rol=, ?estado=, ?page= */
export function listUsuarios(params = {}) {
  const limpios = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "")
  );
  const query = new URLSearchParams(limpios).toString();
  return request(`/api/usuarios/${query ? `?${query}` : ""}`);
}

/** CU04 - Nuevo Usuario */
export function createUsuario(data) {
  return request("/api/usuarios/", { method: "POST", body: JSON.stringify(data) });
}

/** CU05 - Modificar Usuario */
export function updateUsuario(id, data) {
  return request(`/api/usuarios/${id}/`, { method: "PATCH", body: JSON.stringify(data) });
}

/** CU06 - Borrar Usuario */
export function deleteUsuario(id) {
  return request(`/api/usuarios/${id}/`, { method: "DELETE" });
}

/** CU07 - Dar de Alta Usuario */
export function altaUsuario(id) {
  return request(`/api/usuarios/${id}/alta/`, { method: "POST" });
}

/** CU08 - Dar de Baja Usuario */
export function bajaUsuario(id) {
  return request(`/api/usuarios/${id}/baja/`, { method: "POST" });
}

/** Lista solo los operarios activos (para asignarlos a galpones) */
export function listOperarios() {
  return listUsuarios({ rol: "O", estado: "A" });
}

/** Restablecer la contraseña de un usuario (solo Administrador) */
export function restablecerPassword(id, passwordNueva) {
  return request(`/api/usuarios/${id}/restablecer-password/`, {
    method: "POST",
    body: JSON.stringify({ password_nueva: passwordNueva }),
  });
}
