import { useEffect, useState } from "react";
import { buscarSimilares } from "../api/proveedores";

const emptyForm = { nombre: "", cuit: "", email: "", telefono: "", direccion: "" };

export default function ProveedorFormModal({ initialData, onClose, onSubmit }) {
  const isEdit = Boolean(initialData);

  const [form, setForm] = useState(
    initialData
      ? {
          nombre: initialData.nombre,
          cuit: initialData.cuit_formateado || initialData.cuit || "",
          email: initialData.email || "",
          telefono: initialData.telefono || "",
          direccion: initialData.direccion || "",
        }
      : emptyForm
  );

  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const [similares, setSimilares] = useState([]);

  // Avisa mientras se escribe si ya existe un nombre igual o parecido.
  // El backend vuelve a validarlo al guardar.
  useEffect(() => {
    const nombre = form.nombre.trim();
    if (!nombre) {
      setSimilares([]);
      return undefined;
    }
    let cancelado = false;
    const t = setTimeout(async () => {
      try {
        const data = await buscarSimilares(nombre, initialData?.id_proveedor);
        if (!cancelado) setSimilares(Array.isArray(data) ? data : []);
      } catch {
        if (!cancelado) setSimilares([]);
      }
    }, 300);
    return () => {
      cancelado = true;
      clearTimeout(t);
    };
  }, [form.nombre, initialData]);

  const duplicado = similares.find((s) => s.exacta);
  const parecidos = similares.filter((s) => !s.exacta);

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setErrors({});
    try {
      await onSubmit(form);
    } catch (err) {
      if (err.detail && typeof err.detail === "object") {
        setErrors(err.detail);
      } else {
        setErrors({ non_field_errors: ["No se pudo guardar el proveedor."] });
      }
    } finally {
      setSaving(false);
    }
  }

  // Mensajes de validación del navegador en español.
  const validacion = {
    onInvalid: (e) => {
      const v = e.target.validity;
      let msg = "";
      if (v.valueMissing) msg = "Completá este campo.";
      else if (v.typeMismatch) msg = "Ingresá un email válido, por ejemplo nombre@dominio.com.";
      else if (v.tooLong) msg = `Máximo ${e.target.maxLength} caracteres.`;
      e.target.setCustomValidity(msg);
    },
    onInput: (e) => e.target.setCustomValidity(""),
  };

  const fieldError = (campo) =>
    errors[campo] && (
      <span className="form-error">
        {Array.isArray(errors[campo]) ? errors[campo].join(" ") : String(errors[campo])}
      </span>
    );

  return (
    <div className="modal-overlay active" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-card">
        <div className="modal-header">
          <h3>{isEdit ? "Editar proveedor" : "Nuevo proveedor"}</h3>
          <button className="modal-close" onClick={onClose}>
            <i className="fa-solid fa-xmark"></i>
          </button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {errors.non_field_errors && (
              <div className="banner banner-error">{errors.non_field_errors.join(" ")}</div>
            )}
            <div className="form-row">
              <div className="form-group full">
                <label>Nombre o razón social</label>
                <input
                  name="nombre"
                  value={form.nombre}
                  onChange={handleChange}
                  {...validacion}
                  required
                  maxLength={100}
                  placeholder="Ej: Agro Sur S.R.L."
                />
                {duplicado && (
                  <span className="form-error">
                    Ya existe "{duplicado.nombre}"{duplicado.estado === "I" ? " (dado de baja)" : ""}. No se puede repetir el nombre.
                  </span>
                )}
                {!duplicado && parecidos.length > 0 && (
                  <span className="form-hint">
                    Ojo, ya existe algo parecido: {parecidos.map((p) => `"${p.nombre}"`).join(", ")}.
                  </span>
                )}
                {fieldError("nombre")}
              </div>

              <div className="form-group half">
                <label>CUIT</label>
                <input
                  name="cuit"
                  value={form.cuit}
                  onChange={handleChange}
                  {...validacion}
                  maxLength={20}
                  placeholder="20-12345678-6 (opcional)"
                />
                {fieldError("cuit")}
              </div>

              <div className="form-group half">
                <label>Teléfono</label>
                <input
                  name="telefono"
                  value={form.telefono}
                  onChange={handleChange}
                  {...validacion}
                  required
                  maxLength={45}
                  placeholder="381-455-0102"
                />
                <span className="form-hint">Con característica, por ejemplo 381-455-0102.</span>
                {fieldError("telefono")}
              </div>

              <div className="form-group full">
                <label>Email</label>
                <input
                  type="email"
                  name="email"
                  value={form.email}
                  onChange={handleChange}
                  {...validacion}
                  required
                  maxLength={150}
                  placeholder="ventas@proveedor.com"
                />
                {fieldError("email")}
              </div>

              <div className="form-group full">
                <label>Dirección</label>
                <input
                  name="direccion"
                  value={form.direccion}
                  onChange={handleChange}
                  {...validacion}
                  maxLength={150}
                  placeholder="Calle, número, localidad (opcional)"
                />
                {fieldError("direccion")}
              </div>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-outline" onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-green" disabled={saving}>
              <i className="fa-solid fa-check"></i>{" "}
              {saving ? "Guardando..." : isEdit ? "Guardar cambios" : "Crear proveedor"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
