import request, { getToken } from "./client";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

function query(params = {}) {
  const limpios = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== "" && v !== null && v !== undefined)
  );
  const q = new URLSearchParams(limpios).toString();
  return q ? `?${q}` : "";
}

/**
 * Informes (CU85 a CU89). `ruta` es una de: produccion, lotes, materias-primas,
 * descartes, indicadores.
 */
export function getInforme(ruta, params = {}) {
  return request(`/api/informes/${ruta}/${query(params)}`);
}

/**
 * Descarga el informe como archivo (formato "xlsx" o "pdf"). Va con fetch
 * porque la descarga necesita el token JWT en el encabezado.
 */
export async function descargarInforme(ruta, params, formato) {
  let res;
  try {
    res = await fetch(`${API_URL}/api/informes/${ruta}/${query({ ...params, formato })}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
  } catch {
    throw new Error("No se pudo conectar con el servidor. ¿Está corriendo el backend?");
  }
  if (!res.ok) {
    let mensaje = "No se pudo generar el archivo.";
    try {
      const cuerpo = await res.json();
      mensaje = cuerpo.detail || Object.values(cuerpo).flat().join(" ") || mensaje;
    } catch {
      /* respuesta sin cuerpo JSON */
    }
    throw new Error(mensaje);
  }
  const nombre =
    /filename="([^"]+)"/.exec(res.headers.get("Content-Disposition") || "")?.[1] || `informe.${formato}`;
  const url = URL.createObjectURL(await res.blob());
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombre;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  URL.revokeObjectURL(url);
}
