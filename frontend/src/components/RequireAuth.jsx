import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

/**
 * Envuelve las rutas que exigen sesión iniciada.
 *
 * IMPORTANTE: esto es solo comodidad visual. La seguridad real está en el
 * backend, que valida el token en cada petición y responde 401 o 403. Un
 * usuario podría saltear esta pantalla y la API lo rechazaría igual.
 */
export default function RequireAuth({ children }) {
  const { usuario, cargando } = useAuth();
  const location = useLocation();

  // Mientras se valida el token guardado no se decide nada, para evitar que
  // la pantalla de login aparezca por un instante y desaparezca.
  if (cargando) {
    return (
      <div className="auth-loading">
        <span className="spinner" />
        Cargando sesión…
      </div>
    );
  }

  if (!usuario) {
    // `state` recuerda a dónde quería ir, para volver ahí después del login.
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return children;
}
