import { Navigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

/**
 * Restringe una ruta a determinados roles.
 *
 * Hace falta además de ocultar el enlace en el menú, porque ocultar un enlace
 * no impide llegar a la ruta escribiendo la URL, ni evita que quede visible una
 * pantalla ya abierta al cambiar de usuario.
 *
 * Sigue siendo comodidad visual: la seguridad real está en el backend, que
 * responde 403 ante cualquier operación no autorizada.
 */
export default function RequireRol({ roles, children }) {
  const { usuario } = useAuth();

  if (!usuario) return <Navigate to="/login" replace />;

  if (!roles.includes(usuario.rol)) {
    return <Navigate to="/app/dashboard" replace />;
  }

  return children;
}
