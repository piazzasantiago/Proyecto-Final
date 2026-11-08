import { useLayoutEffect, useEffect, useRef, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import CampoPassword from "../components/CampoPassword";
import LogoAvigest from "../components/LogoAvigest";
import { useAuth } from "../context/AuthContext";
import { activarFondo } from "../utils/fondo";

// Número de versión que se muestra al pie del login.
const VERSION = "0.1";

// Pantalla de login (CU01), con el mismo diseño del mockup aprobado.
export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { usuario, cargando, iniciarSesion } = useAuth();

  const [nombreUsuario, setNombreUsuario] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [verRecupero, setVerRecupero] = useState(false);
  const [tiembla, setTiembla] = useState(false); // sacudida corta de la tarjeta cuando hay error
  const [saliendo, setSaliendo] = useState(false); // la tarjeta se va antes de entrar a la app
  const campoUsuario = useRef(null);

  // El fondo del login sigue la hora del día, igual que el de la aplicación.
  useLayoutEffect(() => activarFondo(), []);

  // Foco en el usuario al abrir, pero solo con mouse: en un celular abriría el teclado de golpe
  // y taparía la pantalla antes de que la persona la vea.
  useEffect(() => {
    if (cargando || usuario) return;
    if (window.matchMedia("(hover: hover) and (pointer: fine)").matches) campoUsuario.current?.focus();
  }, [cargando, usuario]);

  // A dónde ir después de entrar: si venía de una ruta protegida, vuelve ahí.
  const destino = location.state?.from?.pathname || "/app/dashboard";

  if (cargando) {
    return (
      <div className="auth-loading">
        <span className="spinner" />
        Cargando…
      </div>
    );
  }

  // Si ya hay sesión activa no tiene sentido mostrar el login.
  // (Mientras se envía o la tarjeta se está yendo se espera, para que la salida se vea completa.)
  if (usuario && !enviando && !saliendo) return <Navigate to={destino} replace />;

  async function handleSubmit(e) {
    e.preventDefault(); // evita que el navegador recargue la página
    setError("");
    setEnviando(true);
    try {
      await iniciarSesion(nombreUsuario, password);
      // La tarjeta se desvanece hacia arriba y recién ahí se entra. Con "reducir movimiento" no se espera.
      if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        setSaliendo(true);
        await new Promise((r) => setTimeout(r, 420));
      }
      navigate(destino, { replace: true });
    } catch (err) {
      setError(err.message);
      setTiembla(true);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className={`screen active${saliendo ? " login-saliendo" : ""}`} id="screen-login">
      <div className="login-bg">
        <div className="bg-circle bg-c1"></div>
        <div className="bg-circle bg-c2"></div>
        <div className="bg-circle bg-c3"></div>
        <div className="bg-circle bg-c4"></div>
        <div className="bg-circle bg-c5"></div>
        <div className="bg-circle bg-c6"></div>
      </div>

      <div className="login-panel">
        <div className="login-brand">
          <LogoAvigest />
        </div>
        <h1>Gestión integral de tu producción avícola.</h1>
        <p>Centralizá el registro de galpones, lotes, producción diaria y materias primas en un solo lugar, con información confiable para tomar mejores decisiones.</p>
      </div>

      <div className="login-form-wrap">
        <form
          className={`login-form${tiembla ? " tiembla" : ""}`}
          onSubmit={handleSubmit}
          onAnimationEnd={(e) => { if (e.animationName === "login-tiembla") setTiembla(false); }}
        >
          <h2>Iniciar sesión</h2>
          <div className="sub">Ingresá tus credenciales para acceder al sistema.</div>

          {error && (
            <div className="alert alert-error" role="alert">
              <i className="fa-solid fa-circle-exclamation"></i>
              <span>{error}</span>
            </div>
          )}

          <div className="field">
            <label htmlFor="usuario">Usuario o email</label>
            <div className="input-wrap">
              <i className="fa-regular fa-user"></i>
              <input
                id="usuario"
                type="text"
                placeholder="operario@granja.com"
                autoComplete="username"
                ref={campoUsuario}
                value={nombreUsuario}
                onChange={(e) => setNombreUsuario(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="field">
            <CampoPassword
              id="password"
              label="Contraseña"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              icono="fa-lock"
              autoComplete="current-password"
              required
            />
          </div>

          <div className="row-between">
            <a
              className="link"
              href="#"
              onClick={(e) => { e.preventDefault(); setVerRecupero(true); }}
            >
              ¿Olvidaste tu contraseña?
            </a>
          </div>

          <button className="btn-primary" type="submit" disabled={enviando}>
            {enviando ? <><span className="btn-spinner" aria-hidden="true" /> Ingresando…</> : <>Ingresar <i className="fa-solid fa-arrow-right"></i></>}
          </button>
        </form>
      </div>

      <footer className="login-pie">
        <span>AviGest · v{VERSION}</span>
        <span>Desarrollado por Santiago Piazza &amp; Antonio Vargas</span>
      </footer>

      {/* El sistema no envía mails de recupero: el usuario le pide al
          administrador que le restablezca la contraseña. */}
      {verRecupero && (
        <div className="modal-overlay active" onClick={() => setVerRecupero(false)}>
          <div className="modal-card modal-card-sm" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Recuperar contraseña</h3>
              <button className="modal-close" onClick={() => setVerRecupero(false)}>
                <i className="fa-solid fa-xmark"></i>
              </button>
            </div>
            <div className="modal-body">
              <div className="aviso">
                <div className="aviso-icon"><i className="fa-solid fa-circle-info"></i></div>
                <p>Pida ayuda a algún administrador para restablecer la contraseña.</p>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-green" onClick={() => setVerRecupero(false)}>
                Entendido
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
