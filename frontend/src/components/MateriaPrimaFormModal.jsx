import { useState } from "react";

const emptyForm = {
  materia_prima: "",
  descripcion: "",
  unidad: "kg",
  stock_minimo: "0",
  stock_inicial: "0",
};

export default function MateriaPrimaFormModal({ initialData, onClose, onSubmit }) {
  const isEdit = Boolean(initialData);

  const [form, setForm] = useState(
    initialData
      ? {
          materia_prima: initialData.materia_prima,
          descripcion: initialData.descripcion || "",
          unidad: initialData.unidad || "kg",
          stock_minimo: String(initialData.stock_minimo ?? 0),
          stock_inicial: String(initialData.stock_inicial ?? 0),
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
        stock_minimo: Number(form.stock_minimo) || 0,
        stock_inicial: Number(form.stock_inicial) || 0,
      });
    } catch (err) {
      if (err.detail && typeof err.detail === "object") {
        setErrors(err.detail);
      } else {
        setErrors({ non_field_errors: ["No se pudo guardar la materia prima."] });
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay active" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-card">
        <div className="modal-header">
          <h3>{isEdit ? "Editar materia prima" : "Nueva materia prima"}</h3>
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
                <label>Nombre de la materia prima</label>
                <input
                  name="materia_prima"
                  value={form.materia_prima}
                  onChange={handleChange}
                  required
                  maxLength={80}
                  placeholder="Ej: Balanceado postura"
                />
                {errors.materia_prima && (
                  <span className="form-error">{errors.materia_prima.join(" ")}</span>
                )}
              </div>

              <div className="form-group full">
                <label>Descripción</label>
                <textarea
                  name="descripcion"
                  value={form.descripcion}
                  onChange={handleChange}
                  placeholder="Notas sobre la materia prima (opcional)"
                />
              </div>

              <div className="form-group half">
                <label>Unidad de medida</label>
                <select name="unidad" value={form.unidad} onChange={handleChange}>
                  <option value="kg">kg</option>
                  <option value="g">g</option>
                  <option value="L">L</option>
                  <option value="mL">mL</option>
                  <option value="unid.">unid.</option>
                  <option value="bolsa">bolsa</option>
                  <option value="saco">saco</option>
                </select>
                {errors.unidad && (
                  <span className="form-error">{errors.unidad.join(" ")}</span>
                )}
              </div>

              <div className="form-group half">
                <label>Stock mínimo</label>
                <input
                  type="number"
                  name="stock_minimo"
                  value={form.stock_minimo}
                  onChange={handleChange}
                  min={0}
                  step={0.01}
                  placeholder="0"
                />
                {errors.stock_minimo && (
                  <span className="form-error">{errors.stock_minimo.join(" ")}</span>
                )}
                <span className="form-hint">
                  Cantidad mínima recomendada en stock.
                </span>
              </div>

              <div className="form-group full">
                <label>Stock inicial / ajuste</label>
                <input
                  type="number"
                  name="stock_inicial"
                  value={form.stock_inicial}
                  onChange={handleChange}
                  min={0}
                  step={0.01}
                  placeholder="0"
                />
                {errors.stock_inicial && (
                  <span className="form-error">{errors.stock_inicial.join(" ")}</span>
                )}
                <span className="form-hint">
                  Stock de partida. El stock actual sumará además las compras y restará los descartes.
                </span>
              </div>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-outline" onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-green" disabled={saving}>
              <i className="fa-solid fa-check"></i>{" "}
              {saving ? "Guardando..." : isEdit ? "Guardar cambios" : "Crear materia prima"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
