import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";

/**
 * Atajos del panel principal.
 *
 * "Nueva recolección", "Registrar descarte" y "Nueva compra" navegan a su
 * sección con el estado { alta: true }; al llegar, la sección abre sola el
 * formulario de alta.
 *
 * El estado se limpia apenas se usa: si no, volver con el botón «atrás» del
 * navegador o refrescar la página abriría el formulario de nuevo.
 */
export default function useAtajoAlta(abrirAlta) {
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    if (!location.state?.alta) return;
    navigate(location.pathname, { replace: true, state: null });
    abrirAlta();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.state]);
}
