import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { clearToken, getToken, setToken } from "../api/client";
import * as authApi from "../api/auth";

const AuthContext = createContext(null);

// Cierre de sesión por inactividad: pasados 10 minutos sin tocar nada, se cierra sola.
// La última actividad se guarda en localStorage para que valga entre pestañas: si hay
// movimiento en una, la otra no se cierra.
const INACTIVIDAD_MS = 10 * 60 * 1000;
const CLAVE_ACTIVIDAD = "avigest-actividad";
const CLAVE_TOKEN = "avigest_token";
const EVENTOS_ACTIVIDAD = ["pointerdown", "pointermove", "keydown", "wheel", "scroll", "touchstart"];

function ultimaActividad() {
  try {
    return Number(localStorage.getItem(CLAVE_ACTIVIDAD)) || 0;
  } catch {
    return 0;
  }
}

function marcarActividad() {
  try {
    localStorage.setItem(CLAVE_ACTIVIDAD, String(Date.now()));
  } catch {
    // Sin localStorage no se puede compartir entre pestañas; se sigue con el contador de esta.
  }
}

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
  // Verdadero cuando la sesión se cerró sola por inactividad: el login lo avisa.
  const [cerradaPorInactividad, setCerradaPorInactividad] = useState(false);

  // Al abrir la aplicación: si hay un token guardado, se valida contra la API.
  // No alcanza con que exista, porque puede estar vencido o el usuario pudo
  // haber sido dado de baja desde que inició sesión.
  useEffect(() => {
    async function restaurarSesion() {
      if (!getToken()) {
        setCargando(false);
        return;
      }
      // Si la última actividad fue hace más de 10 minutos (por ejemplo, la compu estuvo suspendida
      // o la pestaña cerrada), no se retoma la sesión.
      const ultima = ultimaActividad();
      if (ultima && Date.now() - ultima > INACTIVIDAD_MS) {
        clearToken();
        setCerradaPorInactividad(true);
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
    marcarActividad();
    setCerradaPorInactividad(false);
    // El login ya devuelve el usuario, así que no hace falta pedir /me/.
    setUsuario(data.usuario);
    try {
      // Hace que el menú lateral muestre "¡Bienvenido!" una vez en esta sesión.
      sessionStorage.setItem("avigest-bienvenida", "pendiente");
    } catch {
      // Sin sessionStorage simplemente no hay saludo.
    }
    return data.usuario;
  }, []);

  const cerrarSesion = useCallback(async (motivo) => {
    try {
      await authApi.logout();
    } catch {
      // Si el token ya venció el logout falla, pero la sesión se cierra igual.
    }
    clearToken();
    setCerradaPorInactividad(motivo === "inactividad");
    setUsuario(null);
  }, []);

  // Mientras hay sesión: cualquier actividad renueva el plazo, y si pasan 10 minutos sin ninguna
  // se cierra. El chequeo corre cada 15 s y también al volver a la pestaña (los temporizadores
  // de una pestaña en segundo plano se frenan).
  useEffect(() => {
    if (!usuario) return undefined;
    marcarActividad();
    let ultimaMarca = Date.now();
    const alActividad = () => {
      const ahora = Date.now();
      // Se escribe como mucho cada 5 s: pointermove y scroll disparan decenas de eventos por segundo.
      if (ahora - ultimaMarca > 5000) {
        ultimaMarca = ahora;
        marcarActividad();
      }
    };
    const revisar = () => {
      if (Date.now() - ultimaActividad() > INACTIVIDAD_MS) cerrarSesion("inactividad");
    };
    // Si en otra pestaña se cerró la sesión, esta también.
    const alCambiarAlmacenamiento = (e) => {
      if (e.key === CLAVE_TOKEN && e.newValue === null) setUsuario(null);
    };
    EVENTOS_ACTIVIDAD.forEach((ev) => window.addEventListener(ev, alActividad, { passive: true, capture: true }));
    document.addEventListener("visibilitychange", revisar);
    window.addEventListener("storage", alCambiarAlmacenamiento);
    const intervalo = setInterval(revisar, 15000);
    return () => {
      EVENTOS_ACTIVIDAD.forEach((ev) => window.removeEventListener(ev, alActividad, { capture: true }));
      document.removeEventListener("visibilitychange", revisar);
      window.removeEventListener("storage", alCambiarAlmacenamiento);
      clearInterval(intervalo);
    };
  }, [usuario, cerrarSesion]);

  const value = {
    usuario,
    cargando,
    cerradaPorInactividad,
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
