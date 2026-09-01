import { useState } from "react";

const emptyForm = {
  galpon: "",
  latitud: "",
  longitud: "",
  superficie: "",
  capacidad: "",
  estado: "A",
  descripcion: "",
};

export default function GalponFormModal({ initialData, onClose, onSubmit }) {
  const isEdit = Boolean(initialData);
  const [form, setForm] = useState(
    initialData
      ? {
          galpon: initialData.galpon,
          latitud: initialData.latitud,
          longitud: initialData.longitud,
          superficie: initialData.superficie,
          capacidad: initialData.capacidad,
          estado: initialData.estado,
          descripcion: initialData.descripcion || "",
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
      await onSubmit({
        ...form,
        latitud: form.latitud,
        longitud: form.longitud,
        superficie: form.superficie,
        capacidad: parseInt(form.capacidad, 10),
      });
    } catch (err) {
      if (err.detail && typeof err.detail === "object") {
        setErrors(err.detail);
      } else {
        setErrors({ non_field_errors: ["No se pudo guardar el galpón."] });
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay active" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-card">
        <div className="modal-header">
          <h3>{isEdit ? "Editar galpón" : "Nuevo galpón"}</h3>
          <button className="modal-close" onClick={onClose}><i className="fa-solid fa-xmark"></i></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {errors.non_field_errors && (
              <div className="banner banner-error">{errors.non_field_errors.join(" ")}</div>
            )}
            <div className="form-row">
              <div className="form-group full">
                <label>Nombre del galpón</label>
                <input name="galpon" value={form.galpon} onChange={handleChange} required maxLength={80} placeholder="Ej: Galpón Norte" />
                {errors.galpon && <span className="form-error">{errors.galpon.join(" ")}</span>}
              </div>
              <div className="form-group">
                <label>Latitud</label>
                <input name="latitud" type="number" step="any" value={form.latitud} onChange={handleChange} required placeholder="-26.808300" />
                {errors.latitud && <span className="form-error">{errors.latitud.join(" ")}</span>}
              </div>
              <div className="form-group">
                <label>Longitud</label>
                <input name="longitud" type="number" step="any" value={form.longitud} onChange={handleChange} required placeholder="-65.217600" />
                {errors.longitud && <span className="form-error">{errors.longitud.join(" ")}</span>}
              </div>
              <div className="form-group">
                <label>Superficie (m²)</label>
                <input name="superficie" type="number" step="any" value={form.superficie} onChange={handleChange} required placeholder="800" />
                {errors.superficie && <span className="form-error">{errors.superficie.join(" ")}</span>}
              </div>
              <div className="form-group">
                <label>Capacidad (aves)</label>
                <input name="capacidad" type="number" step="1" value={form.capacidad} onChange={handleChange} required placeholder="2500" />
                {errors.capacidad && <span className="form-error">{errors.capacidad.join(" ")}</span>}
              </div>
              <div className="form-group full">
                <label>Estado</label>
                <select name="estado" value={form.estado} onChange={handleChange}>
                  <option value="A">Activo</option>
                  <option value="I">Inactivo</option>
                </select>
              </div>
              <div className="form-group full">
                <label>Descripción</label>
                <textarea name="descripcion" value={form.descripcion} onChange={handleChange} placeholder="Notas sobre el galpón (orientación, equipamiento, etc.)" />
              </div>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-outline" onClick={onClose}>Cancelar</button>
            <button type="submit" className="btn btn-green" disabled={saving}>
              <i className="fa-solid fa-check"></i> {saving ? "Guardando..." : isEdit ? "Guardar cambios" : "Crear galpón"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
