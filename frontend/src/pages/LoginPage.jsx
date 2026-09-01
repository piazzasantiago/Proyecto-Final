import { useNavigate } from "react-router-dom";

// Pantalla de login visual, idéntica al mockup aprobado por el tutor.
// No hay autenticación real todavía: "Ingresar" navega directo al panel.
export default function LoginPage() {
  const navigate = useNavigate();

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
        <div className="login-form">
          <h2>Iniciar sesión</h2>
          <div className="sub">Ingresá tus credenciales para acceder al sistema.</div>

          <div className="field">
            <label>Usuario o email</label>
            <div className="input-wrap">
              <i className="fa-regular fa-user"></i>
              <input type="text" placeholder="operario@granja.com" />
            </div>
          </div>
          <div className="field">
            <label>Contraseña</label>
            <div className="input-wrap">
              <i className="fa-solid fa-lock"></i>
              <input type="password" placeholder="••••••••" />
            </div>
          </div>
          <div className="row-between">
            <a className="link" href="#" onClick={(e) => e.preventDefault()}>¿Olvidaste tu contraseña?</a>
          </div>
          <button className="btn-primary" onClick={() => navigate("/app/dashboard")}>
            Ingresar <i className="fa-solid fa-arrow-right"></i>
          </button>

          <div className="login-footnote">Sistema de Gestión Avícola · v0.1 — módulo Galpones funcional, resto en desarrollo</div>
        </div>
      </div>
    </div>
  );
}
