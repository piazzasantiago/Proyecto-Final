import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";

/**
 * Atajos del panel principal.
 *
 * Desde el panel se puede llegar a una sección de dos maneras:
 *
 * - Con el estado { alta: true } ("Nueva recolección", "Registrar descarte",
 *   "Nueva compra"): la sección abre sola el formulario de alta.
 * - Con el estado { filtros: { estado: "P", ... } } (las tarjetas de pendientes
 *   y de indicadores): la sección abre con esos filtros ya puestos.
 *
 * `abrirAlta` es la función que abre el formulario (puede ser null si la
 * sección no tiene atajo de alta) y `filtros` indica, para cada clave que
 * puede venir en el estado, la función que la aplica. Lo que la sección no
 * conoce se ignora.
 *
 * El estado se limpia apenas se usa: si no, volver con el botón «atrás» del
 * navegador o refrescar la página repetiría el atajo.
 */
export default function useAtajoAlta(abrirAlta, filtros = {}) {
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const atajo = location.state;
    if (!atajo?.alta && !atajo?.filtros) return;
    navigate(location.pathname, { replace: true, state: null });
    if (atajo.alta && abrirAlta) abrirAlta();
    Object.entries(atajo.filtros ?? {}).forEach(([clave, valor]) => filtros[clave]?.(valor));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.state]);
}
