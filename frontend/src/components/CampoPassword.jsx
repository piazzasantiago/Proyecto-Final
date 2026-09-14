import { useId, useState } from "react";

/**
 * Campo de contraseña con botón para mostrar u ocultar el texto.
 *
 * Se usa en tres lugares: el login, el alta de usuario y el restablecimiento
 * de contraseña. Está extraído en un componente para no repetir la lógica del
 * ojo ni sus detalles de accesibilidad.
 *
 * Props:
 *   icono          nombre del ícono de Font Awesome a la izquierda (opcional).
 *                  El login muestra un candado; los modales no llevan ícono.
 *   visiblePorDefecto  arranca con el texto a la vista. Se usa al restablecer
 *                  una contraseña, donde el administrador necesita leerla para
 *                  comunicársela al usuario.
 */
export default function CampoPassword({
  id,
  label,
  value,
  onChange,
  name,
  placeholder = "••••••••",
  autoComplete = "current-password",
  required = false,
  minLength,
  maxLength,
  icono = null,
  visiblePorDefecto = false,
  hint = null,
  error = null,
}) {
  const generado = useId();
  const inputId = id ?? generado;
  const [visible, setVisible] = useState(visiblePorDefecto);

  return (
    <>
      {label && <label htmlFor={inputId}>{label}</label>}

      <div className={`password-wrap${icono ? " tiene-icono" : ""}`}>
        {icono && <i className={`fa-solid ${icono}`}></i>}

        <input
          id={inputId}
          name={name}
          type={visible ? "text" : "password"}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          autoComplete={autoComplete}
          required={required}
          minLength={minLength}
          maxLength={maxLength}
        />

        {/* type="button" evita que el clic envíe el formulario.
            tabIndex={-1} lo saltea al tabular: el orden natural es
            contraseña -> botón de guardar. */}
        <button
          type="button"
          className="input-toggle"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? "Ocultar contraseña" : "Mostrar contraseña"}
          title={visible ? "Ocultar contraseña" : "Mostrar contraseña"}
          tabIndex={-1}
        >
          <i className={visible ? "fa-regular fa-eye-slash" : "fa-regular fa-eye"}></i>
        </button>
      </div>

      {error && <span className="form-error">{error}</span>}
      {hint && <span className="form-hint">{hint}</span>}
    </>
  );
}
