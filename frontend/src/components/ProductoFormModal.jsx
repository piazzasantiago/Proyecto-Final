import { useState } from "react";

const emptyForm = {
  producto: "",
  descripcion: "",
};

export default function ProductoFormModal({ initialData, onClose, onSubmit }) {
  const isEdit = Boolean(initialData);

  const [form, setForm] = useState(
    initialData
      ? {
          producto: initialData.producto,
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
      await onSubmit(form);
    } catch (err) {
      if (err.detail && typeof err.detail === "object") {
        setErrors(err.detail);
      } else {
        setErrors({ non_field_errors: ["No se pudo guardar el producto."] });
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay active" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-card">
        <div className="modal-header">
          <h3>{isEdit ? "Editar producto" : "Nuevo producto"}</h3>
          <button className="modal-close" onClick={onClose}><i className="fa-solid fa-xmark"></i></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {errors.non_field_errors && (
              <div className="banner banner-error">{errors.non_field_errors.join(" ")}</div>
            )}
            <div className="form-row">
              <div className="form-group full">
                <label>Nombre del producto</label>
                <input
                  name="producto"
                  value={form.producto}
                  onChange={handleChange}
                  required
                  maxLength={80}
                  placeholder="Ej: Huevo Nº1 (grande)"
                />
                {errors.producto && <span className="form-error">{errors.producto.join(" ")}</span>}
              </div>
              <div className="form-group full">
                <label>Descripción</label>
                <textarea
                  name="descripcion"
                  value={form.descripcion}
                  onChange={handleChange}
                  placeholder="Notas sobre el producto (opcional)"
                />
              </div>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-outline" onClick={onClose}>Cancelar</button>
            <button type="submit" className="btn btn-green" disabled={saving}>
              <i className="fa-solid fa-check"></i> {saving ? "Guardando..." : isEdit ? "Guardar cambios" : "Crear producto"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
