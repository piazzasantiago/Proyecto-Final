import { useCallback, useState } from "react";

const CLAVE = "avigest-tema";

/**
 * Tema claro u oscuro.
 *
 * El tema vive en el atributo data-theme de <html>, que es lo que leen los
 * estilos (index.css). El script de index.html lo pone antes de que cargue la
 * aplicación, para que la pantalla no parpadee en claro al abrir en oscuro.
 *
 * Se elige, en este orden: lo que el usuario guardó con el botón, o si no, la
 * preferencia del sistema operativo. El almacenamiento del navegador puede
 * fallar (modo privado, datos bloqueados), así que siempre va con try/catch y
 * la pantalla funciona igual sin él.
 */
export function leerTemaGuardado() {
  try {
    const guardado = localStorage.getItem(CLAVE);
    if (guardado === "dark" || guardado === "light") return guardado;
  } catch {
    // sin almacenamiento: se usa la preferencia del sistema
  }
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export default function useTema() {
  const [tema, setTemaEstado] = useState(
    () => document.documentElement.getAttribute("data-theme") || leerTemaGuardado()
  );

  const alternar = useCallback(() => {
    const nuevo = tema === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", nuevo);
    try {
      localStorage.setItem(CLAVE, nuevo);
    } catch {
      // no se pudo guardar: el cambio rige hasta recargar
    }
    setTemaEstado(nuevo);
  }, [tema]);

  return { tema, esOscuro: tema === "dark", alternar };
}
