import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { clearToken, getToken, setToken } from "../api/client";
import * as authApi from "../api/auth";

const AuthContext = createContext(null);

/**
 * Contexto de sesión.
 *
 * Un contexto de React es un valor disponible para todos los componentes de
 * adentro, sin pasarlo por props en cada nivel. Acá vive quién inició sesión
 * y las funciones para entrar y salir.
 *
 * Es el equivalente en el frontend de permissions.py: el único lugar donde se
 * resuelve "quién es el usuario y qué rol tiene".
 */
export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null);
  // `cargando` evita el parpadeo inicial: mientras se valida el token guardado
  // todavía no se sabe si mostrar el login o la aplicación.
  const [cargando, setCargando] = useState(true);

  // Al abrir la aplicación: si hay un token guardado, se valida contra la API.
  // No alcanza con que exista, porque puede estar vencido o el usuario pudo
  // haber sido dado de baja desde que inició sesión.
  useEffect(() => {
    async function restaurarSesion() {
      if (!getToken()) {
        setCargando(false);
        return;
      }
      try {
        setUsuario(await authApi.getMe());
      } catch {
        clearToken();
      } finally {
        setCargando(false);
      }
    }
    restaurarSesion();
  }, []);

  const iniciarSesion = useCallback(async (nombreUsuario, password) => {
    const data = await authApi.login(nombreUsuario, password);
    setToken(data.access);
    // El login ya devuelve el usuario, así que no hace falta pedir /me/.
    setUsuario(data.usuario);
    return data.usuario;
  }, []);

  const cerrarSesion = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // Si el token ya venció el logout falla, pero la sesión se cierra igual.
    }
    clearToken();
    setUsuario(null);
  }, []);

  const value = {
    usuario,
    cargando,
    iniciarSesion,
    cerrarSesion,
    esAdministrador: usuario?.rol === "A",
    esOperario: usuario?.rol === "O",
    esConsulta: usuario?.rol === "C",
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** Hook para consumir el contexto desde cualquier componente. */
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  }
  return context;
}
