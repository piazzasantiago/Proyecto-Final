import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

/**
 * Atajos del panel principal.
 *
 * Desde el panel se llega a una sección de dos maneras:
 *
 * - Con el estado { alta: true } ("Nueva recolección", "Registrar descarte",
 *   "Nueva compra"): la sección abre sola el formulario de alta.
 * - Con el estado { filtros: { estado: "P", ... } } (las tarjetas de
 *   pendientes, las de indicadores y las alertas): la sección abre con esos
 *   filtros ya puestos.
 *
 * `abrirAlta` es la función que abre el formulario (null si la sección no
 * tiene ese atajo) y `filtros` indica, para cada clave que puede venir en el
 * estado, la función que la aplica. Lo que la sección no conoce se ignora.
 *
 * El atajo se aplica durante el primer render, no en un efecto. Puesto en un
 * efecto, el efecto que trae los datos ya había salido a buscar la lista sin
 * filtrar: quedaban dos pedidos en vuelo y, si el de la lista completa volvía
 * último, la pantalla terminaba mostrando todos los registros con el filtro
 * puesto. Aplicándolo durante el render, React vuelve a renderizar con el
 * filtro antes de correr ningún efecto, así que el pedido sale una sola vez y
 * ya filtrado. Es seguro porque las funciones que se llaman son estados de la
 * misma sección que usa el hook.
 *
 * Limpiar el estado sí va en un efecto, porque no se puede navegar durante el
 * render. Se limpia apenas se usa: si no, volver con el botón «atrás» del
 * navegador o refrescar la página repetiría el atajo.
 */
export default function useAtajoAlta(abrirAlta, filtros = {}) {
  const location = useLocation();
  const navigate = useNavigate();
  const atajo = location.state;
  const [aplicado, setAplicado] = useState(null);

  if (atajo && atajo !== aplicado && (atajo.alta || atajo.filtros)) {
    setAplicado(atajo);
    if (atajo.alta && abrirAlta) abrirAlta();
    Object.entries(atajo.filtros ?? {}).forEach(([clave, valor]) => filtros[clave]?.(valor));
  }

  useEffect(() => {
    if (location.state) {
      navigate(location.pathname, { replace: true, state: null });
    }
  }, [location.state, location.pathname, navigate]);
}
