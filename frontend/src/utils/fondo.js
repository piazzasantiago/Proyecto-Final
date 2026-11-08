/**
 * Fondo del sistema según la hora del día: pone data-momento (amanecer, dia, atardecer o noche) en <html>
 * y los colores salen del CSS (variables --fondo-a..d en index.css). Se revisa cada pocos minutos, así
 * que si la página queda abierta el fondo cambia solo, con un fundido lento.
 */
export function momentoDelDia(fecha = new Date()) {
  const h = fecha.getHours();
  if (h >= 5 && h < 9) return "amanecer";
  if (h >= 9 && h < 17) return "dia";
  if (h >= 17 && h < 20) return "atardecer";
  return "noche";
}

/** Activa el fondo por momento del día; devuelve la función que lo desactiva. */
export function activarFondo() {
  const raiz = document.documentElement;
  const poner = () => { raiz.dataset.momento = momentoDelDia(); };
  poner();
  const reloj = setInterval(poner, 5 * 60 * 1000);
  return () => {
    clearInterval(reloj);
    delete raiz.dataset.momento;
  };
}
