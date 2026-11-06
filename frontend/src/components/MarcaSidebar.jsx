import { useEffect, useRef, useState } from "react";

import LogoAvigest from "./LogoAvigest";

export const CLAVE_BIENVENIDA = "avigest-bienvenida";
const MS_BIENVENIDA = 2600;

/** True solo la primera vez que se entra al sistema tras iniciar sesión (no al recargar la página). */
function corresponde() {
  try {
    if (sessionStorage.getItem(CLAVE_BIENVENIDA) === "pendiente") {
      sessionStorage.setItem(CLAVE_BIENVENIDA, "vista");
      return true;
    }
  } catch {
    // Sin sessionStorage: se muestra el logo directo.
  }
  return false;
}

/**
 * Encabezado del menú lateral. Tras iniciar sesión muestra "¡Bienvenido!" unos
 * segundos en el lugar del logo; el saludo se borra de derecha a izquierda y después
 * el logo aparece de derecha a izquierda (nunca se ven los dos a la vez). Ambas
 * capas ocupan el mismo espacio, así que el menú no se mueve.
 */
export default function MarcaSidebar({ onLista }) {
  // Una fase a la vez, sin que se superpongan: saludo -> saliendo -> entrando -> fin
  const [fase, setFase] = useState(() => (corresponde() ? "saludo" : "fin"));

  useEffect(() => {
    const siguiente = { saludo: ["saliendo", MS_BIENVENIDA], saliendo: ["entrando", 450], entrando: ["fin", 550] }[fase];
    if (!siguiente) return undefined;
    const t = setTimeout(() => setFase(siguiente[0]), siguiente[1]);
    return () => clearTimeout(t);
  }, [fase]);

  // Avisa cuando el saludo ya terminó (o no hubo), para que el tutorial no se pise con él.
  const avisar = useRef(onLista);
  avisar.current = onLista;
  useEffect(() => {
    if (fase === "fin") avisar.current?.();
  }, [fase]);

  return (
    <div className={`sb-marca fase-${fase}`}>
      <div className="sb-marca-logo" aria-hidden={fase !== "fin"}>
        <LogoAvigest compacto />
      </div>
      {(fase === "saludo" || fase === "saliendo") && (
        <div className="sb-marca-saludo" role="status">¡Bienvenido!</div>
      )}
    </div>
  );
}
