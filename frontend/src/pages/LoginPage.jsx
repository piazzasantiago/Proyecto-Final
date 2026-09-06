import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

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

  // A dónde ir después de entrar: si venía de una ruta protegida, vuelve ahí.
  const destino = location.state?.from?.pathname || "/app/galpones";

  if (cargando) {
    return (
      <div className="auth-loading">
        <span className="spinner" />
        Cargando…
      </div>
    );
  }

  // Si ya hay sesión activa no tiene sentido mostrar el login.
  if (usuario) return <Navigate to={destino} replace />;

  async function handleSubmit(e) {
    e.preventDefault(); // evita que el navegador recargue la página
    setError("");
    setEnviando(true);
    try {
      await iniciarSesion(nombreUsuario, password);
      navigate(destino, { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="screen active" id="screen-login">
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
          <div className="logo-mark"><i className="fa-solid fa-egg"></i></div>
          <span>AvíGest</span>
        </div>
        <h1>Gestión integral de tu producción avícola.</h1>
        <p>Centralizá el registro de galpones, lotes, producción diaria y materias primas en un solo lugar, con información confiable para tomar mejores decisiones.</p>
      </div>

      <div className="login-form-wrap">
        <form className="login-form" onSubmit={handleSubmit}>
          <h2>Iniciar sesión</h2>
          <div className="sub">Ingresá tus credenciales para acceder al sistema.</div>

          {error && (
            <div className="alert alert-error">
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
                value={nombreUsuario}
                onChange={(e) => setNombreUsuario(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="field">
            <label htmlFor="password">Contraseña</label>
            <div className="input-wrap">
              <i className="fa-solid fa-lock"></i>
              <input
                id="password"
                type="password"
                placeholder="••••••••"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
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
            {enviando ? "Ingresando…" : <>Ingresar <i className="fa-solid fa-arrow-right"></i></>}
          </button>

          <div className="login-footnote">Sistema de Gestión Avícola · v0.1 — módulos Galpones y Usuarios funcionales</div>
        </form>
      </div>

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
