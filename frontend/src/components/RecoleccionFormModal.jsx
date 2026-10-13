import { useState } from "react";
import { createRecoleccion, updateRecoleccion } from "../api/recolecciones";

function emptyLinea() {
  return { id_producto_id: "", cantidad: "" };
}

// Fecha y hora actuales en horario local, con el formato que espera el input
// datetime-local (AAAA-MM-DDTHH:mm). Se usa como máximo permitido.
function ahoraLocal() {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

function initForm(initialData) {
  if (!initialData) {
    return {
      id_galpon_id: "",
      fecha: "",
      observaciones: "",
      lineas: [emptyLinea()],
    };
  }
  return {
    id_galpon_id: initialData.galpon?.id_galpon ?? "",
    fecha: initialData.fecha ? initialData.fecha.slice(0, 16) : "",
    observaciones: initialData.observaciones ?? "",
    lineas: initialData.lineas?.length
      ? initialData.lineas.map((l) => ({
          id_producto_id: l.producto?.id_producto ?? "",
          cantidad: l.cantidad ?? "",
        }))
      : [emptyLinea()],
  };
}

export default function RecoleccionFormModal({
  galpones = [],
  productos = [],
  initialData,
  onClose,
  onSubmit,
}) {
  const isEdit = Boolean(initialData);
  const [form, setForm] = useState(() => initForm(initialData));
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);

  function handleChange(e) {
    const { name, value } = e.target;
    e.target.setCustomValidity("");
    setForm((f) => ({ ...f, [name]: value }));
  }

  // Mensajes de validación nativos en español (el navegador los muestra en
  // inglés por defecto).
  function handleFechaInvalid(e) {
    const v = e.target.validity;
    e.target.setCustomValidity(
      v.valueMissing
        ? "Debe ingresar la fecha y hora de la recolección"
        : v.rangeOverflow
        ? "La fecha y hora de la recolección no puede ser futura"
        : "La fecha y hora no es válida. Completá día, mes, año, hora y minutos."
    );
  }

  function handleLineaChange(index, e) {
    const { name, value } = e.target;
    setForm((f) => {
      const lineas = f.lineas.map((l, i) =>
        i === index ? { ...l, [name]: value } : l
      );
      return { ...f, lineas };
    });
  }

  function addLinea() {
    setForm((f) => ({ ...f, lineas: [...f.lineas, emptyLinea()] }));
  }

  function removeLinea(index) {
    setForm((f) => ({
      ...f,
      lineas: f.lineas.filter((_, i) => i !== index),
    }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setErrors({});
    try {
      const payload = {
        id_galpon_id: Number(form.id_galpon_id),
        fecha: form.fecha,
        observaciones: form.observaciones,
        lineas: form.lineas.map((l) => ({
          id_producto_id: Number(l.id_producto_id),
          cantidad: Number(l.cantidad),
        })),
      };

      let result;
      if (isEdit) {
        result = await updateRecoleccion(initialData.id_recoleccion, payload);
      } else {
        result = await createRecoleccion(payload);
      }
      await onSubmit(result);
    } catch (err) {
      if (err.detail && typeof err.detail === "object") {
        setErrors(err.detail);
      } else {
        setErrors({ non_field_errors: [err.message || "No se pudo guardar la recolección."] });
      }
    } finally {
      setSaving(false);
    }
  }

  // Productos activos + el que ya estaba elegido en edición (por si fue desactivado)
  function productosDisponibles(lineaActual) {
    const idActual = Number(lineaActual.id_producto_id);
    return productos.filter(
      (p) => p.estado === "A" || p.id_producto === idActual
    );
  }

  return (
    <div
      className="modal-overlay active"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="modal-card" style={{ maxWidth: 640 }}>
        <div className="modal-header">
          <h3>{isEdit ? "Editar recolección" : "Nueva recolección"}</h3>
          <button className="modal-close" onClick={onClose}>
            <i className="fa-solid fa-xmark"></i>
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {errors.non_field_errors && (
              <div className="banner banner-error">
                {errors.non_field_errors.join(" ")}
              </div>
            )}

            {/* ---- Cabecera ---- */}
            <div className="form-row">
              <div className="form-group full">
                <label>Galpón</label>
                <select
                  name="id_galpon_id"
                  value={form.id_galpon_id}
                  onChange={handleChange}
                  required
                  disabled={isEdit}
                >
                  <option value="">Seleccioná un galpón activo...</option>
                  {galpones.map((g) => (
                    <option key={g.id_galpon} value={g.id_galpon}>
                      G-{String(g.id_galpon).padStart(2, "0")} · {g.galpon}
                    </option>
                  ))}
                </select>
                {errors.id_galpon_id && (
                  <span className="form-error">
                    {Array.isArray(errors.id_galpon_id)
                      ? errors.id_galpon_id.join(" ")
                      : errors.id_galpon_id}
                  </span>
                )}
                {isEdit && (
                  <span className="form-hint">
                    El galpón no se puede cambiar después de crear la recolección.
                  </span>
                )}
              </div>

              <div className="form-group full">
                <label>Fecha y hora</label>
                <input
                  name="fecha"
                  type="datetime-local"
                  value={form.fecha}
                  onChange={handleChange}
                  onInvalid={handleFechaInvalid}
                  max={ahoraLocal()}
                  required
                />
                {errors.fecha && (
                  <span className="form-error">{errors.fecha.join(" ")}</span>
                )}
              </div>

              <div className="form-group full">
                <label>Observaciones</label>
                <textarea
                  name="observaciones"
                  value={form.observaciones}
                  onChange={handleChange}
                  placeholder="Notas sobre la recolección (opcional)"
                />
                {errors.observaciones && (
                  <span className="form-error">
                    {errors.observaciones.join(" ")}
                  </span>
                )}
              </div>
            </div>

            {/* ---- Líneas ---- */}
            <div className="form-lines-title">
              <span>Productos recolectados</span>
            </div>

            {errors.lineas && typeof errors.lineas === "string" && (
              <div className="banner banner-error">{errors.lineas}</div>
            )}

            <div style={{ overflowX: "auto" }}>
              <table className="plan-table" style={{ minWidth: 400 }}>
                <thead>
                  <tr>
                    <th>Producto</th>
                    <th style={{ width: 110 }}>Cantidad</th>
                    <th style={{ width: 40 }}></th>
                  </tr>
                </thead>
                <tbody>
                  {form.lineas.map((linea, index) => (
                    <tr key={index}>
                      <td>
                        <select
                          name="id_producto_id"
                          value={linea.id_producto_id}
                          onChange={(e) => handleLineaChange(index, e)}
                          required
                          style={{
                            width: "100%",
                            padding: "6px 8px",
                            border: "1.5px solid var(--gray-300)",
                            borderRadius: 7,
                            fontSize: 14,
                            fontFamily: "inherit",
                          }}
                        >
                          <option value="">Seleccioná...</option>
                          {productosDisponibles(linea).map((p) => (
                            <option key={p.id_producto} value={p.id_producto}>
                              {p.producto}
                            </option>
                          ))}
                        </select>
                        {errors.lineas?.[index]?.id_producto_id && (
                          <span className="form-error">
                            {errors.lineas[index].id_producto_id.join(" ")}
                          </span>
                        )}
                      </td>
                      <td>
                        <input
                          name="cantidad"
                          type="number"
                          step="1"
                          min="1"
                          value={linea.cantidad}
                          onChange={(e) => handleLineaChange(index, e)}
                          required
                          placeholder="0"
                          style={{
                            width: "100%",
                            padding: "6px 8px",
                            border: "1.5px solid var(--gray-300)",
                            borderRadius: 7,
                            fontSize: 14,
                            fontFamily: "inherit",
                          }}
                        />
                        {errors.lineas?.[index]?.cantidad && (
                          <span className="form-error">
                            {errors.lineas[index].cantidad.join(" ")}
                          </span>
                        )}
                      </td>
                      <td style={{ textAlign: "center" }}>
                        {form.lineas.length > 1 && (
                          <button
                            type="button"
                            className="btn btn-outline"
                            style={{ padding: "4px 8px", fontSize: 13 }}
                            onClick={() => removeLinea(index)}
                            title="Quitar línea"
                          >
                            <i className="fa-solid fa-trash"></i>
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <button
              type="button"
              className="btn btn-outline"
              style={{ marginTop: 8, fontSize: 13 }}
              onClick={addLinea}
            >
              <i className="fa-solid fa-plus"></i> Agregar producto
            </button>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-outline" onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-green" disabled={saving}>
              <i className="fa-solid fa-check"></i>{" "}
              {saving
                ? "Guardando..."
                : isEdit
                ? "Guardar cambios"
                : "Crear recolección"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}