import { useState } from "react";

import CampoPassword from "./CampoPassword";

const emptyForm = {
  nombre: "",
  apellido: "",
  usuario: "",
  email: "",
  dni: "",
  rol: "O",
  password: "",
};

/**
 * Formulario de alta (CU04) y modificación (CU05) de usuario.
 *
 * La contraseña solo se pide al crear. Para cambiarla después está el
 * restablecimiento, que es una operación aparte.
 */
export default function UsuarioFormModal({ initialData, onClose, onSubmit }) {
  const isEdit = Boolean(initialData);

  const [form, setForm] = useState(
    initialData
      ? {
          nombre: initialData.nombre,
          apellido: initialData.apellido,
          usuario: initialData.usuario,
          email: initialData.email,
          dni: initialData.dni,
          rol: initialData.rol,
          password: "",
        }
      : emptyForm
  );
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setErrors({});
    try {
      const datos = {
        nombre: form.nombre.trim(),
        apellido: form.apellido.trim(),
        usuario: form.usuario.trim(),
        email: form.email.trim().toLowerCase(),
        dni: form.dni.trim(),
        rol: form.rol,
      };
      // La contraseña solo se envía al crear.
      if (!isEdit) datos.password = form.password;

      await onSubmit(datos);
    } catch (err) {
      // El backend ya valida todo (duplicados, formato, longitud): se muestran
      // sus mensajes tal cual, para no tener dos juegos de reglas que puedan
      // quedar desincronizados.
      if (err.detail && typeof err.detail === "object") {
        setErrors(err.detail);
      } else {
        setErrors({ non_field_errors: ["No se pudo guardar el usuario."] });
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay active" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-card">
        <div className="modal-header">
          <h3>{isEdit ? "Editar usuario" : "Nuevo usuario"}</h3>
          <button className="modal-close" onClick={onClose}><i className="fa-solid fa-xmark"></i></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {errors.non_field_errors && (
              <div className="banner banner-error">{errors.non_field_errors.join(" ")}</div>
            )}
            {errors.detail && <div className="banner banner-error">{errors.detail}</div>}

            <div className="form-row">
              <div className="form-group">
                <label>Nombre</label>
                <input name="nombre" value={form.nombre} onChange={handleChange} required maxLength={100} placeholder="Ej: Carlos" />
                {errors.nombre && <span className="form-error">{errors.nombre.join(" ")}</span>}
              </div>
              <div className="form-group">
                <label>Apellido</label>
                <input name="apellido" value={form.apellido} onChange={handleChange} required maxLength={100} placeholder="Ej: Gómez" />
                {errors.apellido && <span className="form-error">{errors.apellido.join(" ")}</span>}
              </div>
              <div className="form-group">
                <label>Nombre de usuario</label>
                <input name="usuario" value={form.usuario} onChange={handleChange} required maxLength={100} placeholder="Ej: cgomez" />
                {errors.usuario && <span className="form-error">{errors.usuario.join(" ")}</span>}
              </div>
              <div className="form-group">
                <label>DNI</label>
                <input name="dni" value={form.dni} onChange={handleChange} required maxLength={15} placeholder="32145870" />
                {errors.dni && <span className="form-error">{errors.dni.join(" ")}</span>}
              </div>
              <div className="form-group full">
                <label>Email</label>
                <input name="email" type="email" value={form.email} onChange={handleChange} required maxLength={150} placeholder="carlos.gomez@granja.com" />
                {errors.email && <span className="form-error">{errors.email.join(" ")}</span>}
              </div>
              <div className="form-group full">
                <label>Rol</label>
                <select name="rol" value={form.rol} onChange={handleChange}>
                  <option value="A">Administrador</option>
                  <option value="O">Operario</option>
                  <option value="C">Consulta</option>
                </select>
                {errors.rol && <span className="form-error">{errors.rol.join(" ")}</span>}
              </div>

              {!isEdit && (
                <div className="form-group full">
                  <CampoPassword
                    label="Contraseña inicial"
                    name="password"
                    value={form.password}
                    onChange={handleChange}
                    placeholder="Mínimo 8 caracteres"
                    autoComplete="new-password"
                    required
                    minLength={8}
                    maxLength={128}
                    error={errors.password?.join(" ")}
                    hint="Comunicásela al usuario para que pueda ingresar por primera vez."
                  />
                </div>
              )}

              {isEdit && (
                <div className="form-group full">
                  <span className="form-hint">
                    Para cambiar la contraseña usá el botón "Restablecer contraseña" del panel
                    de detalle.
                  </span>
                </div>
              )}
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-outline" onClick={onClose}>Cancelar</button>
            <button type="submit" className="btn btn-green" disabled={saving}>
              <i className="fa-solid fa-check"></i>{" "}
              {saving ? "Guardando..." : isEdit ? "Guardar cambios" : "Crear usuario"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
