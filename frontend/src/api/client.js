const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const TOKEN_KEY = "avigest_token";

// --- Manejo del token JWT ---------------------------------------------------
// El token se guarda en localStorage para que la sesión sobreviva a un F5.

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

// --- Petición genérica ------------------------------------------------------

async function request(path, options = {}) {
  const { auth = true, ...rest } = options;

  const headers = { "Content-Type": "application/json", ...(rest.headers || {}) };

  // Todas las peticiones llevan el token salvo que se indique auth: false
  // (el login todavía no tiene token que enviar).
  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  let res;
  try {
    res = await fetch(`${API_URL}${path}`, { ...rest, headers });
  } catch {
    // fetch solo falla así si no hubo respuesta: backend caído o sin red.
    const error = new Error("No se pudo conectar con el servidor. ¿Está corriendo el backend?");
    error.status = 0;
    throw error;
  }

  if (!res.ok) {
    let detail;
    try {
      detail = await res.json();
    } catch {
      detail = { detail: res.statusText };
    }

    // 401 = token vencido o inválido. Se descarta para no quedar en un estado
    // donde la app cree que hay sesión pero el backend la rechaza.
    if (res.status === 401) clearToken();

    const error = new Error(mensajeDeError(detail, res.status));
    error.status = res.status;
    error.detail = detail;
    throw error;
  }

  if (res.status === 204) return null;
  return res.json();
}

/**
 * Traduce el cuerpo de error de DRF a un mensaje legible.
 *
 * DRF devuelve dos formas distintas:
 *   - Errores generales:    { "detail": "texto" }
 *   - Errores de validación: { "campo": ["mensaje"], "otro": ["mensaje"] }
 */
function mensajeDeError(detail, status) {
  if (!detail) return "No se pudo completar la operación.";

  if (typeof detail.detail === "string") return detail.detail;

  const campos = Object.entries(detail)
    .map(([campo, errores]) => {
      const texto = Array.isArray(errores) ? errores.join(" ") : String(errores);
      return campo === "non_field_errors" ? texto : `${campo}: ${texto}`;
    })
    .join(" · ");

  if (campos) return campos;
  if (status >= 500) return "Error del servidor. Intentá de nuevo en un momento.";
  return "No se pudo completar la operación.";
}

export default request;
