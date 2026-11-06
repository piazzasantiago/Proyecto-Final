import request from "./client";

/** CU01 - Iniciar Sesión. Devuelve { access, refresh, usuario }. */
export function login(usuario, password) {
  return request("/api/auth/login/", {
    method: "POST",
    body: JSON.stringify({ usuario, password }),
    auth: false, // todavía no hay token que enviar
  });
}

/** Datos del usuario dueño del token. */
export function getMe() {
  return request("/api/auth/me/");
}

/** CU02 - Cerrar Sesión. */
export function logout() {
  return request("/api/auth/logout/", { method: "POST" });
}
