import { useState } from "react";
import { createSalida, updateSalida } from "../api/salidas";
import Combobox from "./Combobox";

// Debe coincidir con el max_length de `observaciones` en el serializer.
const OBSERVACIONES_MAX = 500;

function emptyLinea() {
  return { id_producto: "", cantidad: "" };
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
    return { fecha: "", observaciones: "", lineas: [emptyLinea()] };
  }
  return {
    fecha: initialData.fecha ? initialData.fecha.slice(0, 16) : "",
    observaciones: initialData.observaciones ?? "",
    lineas: initialData.lineas?.length
      ? initialData.lineas.map((l) => ({
          id_producto: l.id_producto ?? "",
          cantidad: l.cantidad ?? "",
        }))
      : [emptyLinea()],
  };
}

const estiloCampo = {
  width: "100%",
  padding: "6px 8px",
  border: "1.5px solid var(--gray-300)",
  borderRadius: 7,
  fontSize: 14,
  fontFamily: "inherit",
};

/** Une los mensajes de error de un campo (DRF los devuelve como lista). */
function texto(err) {
  if (!err) return "";
  return Array.isArray(err) ? err.join(" ") : String(err);
}

function formatNumero(valor) {
  const n = Number(valor);
  return Number.isNaN(n) ? "—" : n.toLocaleString("es-AR", { maximumFractionDigits: 0 });
}

export default function SalidaFormModal({ productos = [], initialData, onClose, onSubmit }) {
  const isEdit = Boolean(initialData);
  const [form, setForm] = useState(() => initForm(initialData));
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);

  function handleChange(e) {
    const { name, value } = e.target;
    e.target.setCustomValidity("");
    setForm((f) => ({ ...f, [name]: value }));
  }

  function handleLineaChange(index, e) {
    const { name, value } = e.target;
    e.target.setCustomValidity("");
    setForm((f) => ({
      ...f,
      lineas: f.lineas.map((l, i) => (i === index ? { ...l, [name]: value } : l)),
    }));
  }

  function addLinea() {
    setForm((f) => ({ ...f, lineas: [...f.lineas, emptyLinea()] }));
  }

  function removeLinea(index) {
    setForm((f) => ({ ...f, lineas: f.lineas.filter((_, i) => i !== index) }));
  }

  // Mensajes de validación nativos en español.
  function handleFechaInvalid(e) {
    const v = e.target.validity;
    e.target.setCustomValidity(
      v.valueMissing
        ? "Debe ingresar la fecha y hora de la salida"
        : v.rangeOverflow
        ? "La fecha y hora de la salida no puede ser futura"
        : "La fecha y hora no es válida. Completá día, mes, año, hora y minutos."
    );
  }

  function handleProductoInvalid(e) {
    e.target.setCustomValidity("Debe seleccionar un producto");
  }

  function handleCantidadInvalid(e, disponible) {
    const v = e.target.validity;
    e.target.setCustomValidity(
      v.valueMissing
        ? "Debe ingresar la cantidad"
        : v.rangeOverflow
        ? `La cantidad supera el stock disponible (${formatNumero(disponible)})`
        : "La cantidad debe ser un número entero mayor que 0"
    );
  }

  function productoDe(linea) {
    const id = Number(linea.id_producto);
    return id ? productos.find((p) => p.id_producto === id) ?? null : null;
  }

  // Opciones de producto: solo los activos. En edición se conservan los que ya
  // tenía la salida aunque se hayan desactivado después.
  function opciones() {
    const lista = productos
      .filter((p) => p.estado === "A")
      .map((p) => ({
        id: p.id_producto,
        label: `${p.producto} · stock ${formatNumero(p.stock_actual)}`,
      }));
    (initialData?.lineas ?? []).forEach((l) => {
      if (!lista.some((o) => o.id === l.id_producto)) {
        lista.push({ id: l.id_producto, label: `${l.producto_nombre} (inactivo)` });
      }
    });
    return lista;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setErrors({});
    try {
      const payload = {
        fecha: form.fecha,
        observaciones: form.observaciones,
        lineas: form.lineas.map((l) => ({
          id_producto: Number(l.id_producto),
          cantidad: Number(l.cantidad),
        })),
      };

      const result = isEdit
        ? await updateSalida(initialData.id_salida, payload)
        : await createSalida(payload);
      await onSubmit(result);
    } catch (err) {
      if (err.detail && typeof err.detail === "object") {
        setErrors(err.detail);
      } else {
        setErrors({ non_field_errors: [err.message || "No se pudo guardar la salida."] });
      }
    } finally {
      setSaving(false);
    }
  }

  // Errores de una línea: DRF devuelve una lista con un objeto (o {}) por línea.
  function erroresDeLinea(index) {
    return Array.isArray(errors.lineas) && typeof errors.lineas[index] === "object"
      ? errors.lineas[index] ?? {}
      : {};
  }

  return (
    <div
      className="modal-overlay active"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="modal-card" style={{ maxWidth: 760 }}>
        <div className="modal-header">
          <h3>{isEdit ? "Editar salida" : "Nueva salida"}</h3>
          <button className="modal-close" onClick={onClose}>
            <i className="fa-solid fa-xmark"></i>
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {errors.non_field_errors && (
              <div className="banner banner-error">{texto(errors.non_field_errors)}</div>
            )}
            {errors.detail && <div className="banner banner-error">{texto(errors.detail)}</div>}

            {/* ---- Cabecera ---- */}
            <div className="form-row">
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
                {errors.fecha && <span className="form-error">{texto(errors.fecha)}</span>}
              </div>

              <div className="form-group full">
                <label>Observaciones</label>
                <textarea
                  name="observaciones"
                  value={form.observaciones}
                  onChange={handleChange}
                  maxLength={OBSERVACIONES_MAX}
                  placeholder="Destino, comprador u otras notas sobre la salida (opcional)"
                />
                <span className="form-hint">
                  {form.observaciones.length}/{OBSERVACIONES_MAX} caracteres
                </span>
                {errors.observaciones && (
                  <span className="form-error">{texto(errors.observaciones)}</span>
                )}
              </div>
            </div>

            {/* ---- Líneas ---- */}
            <div className="form-lines-title">
              <span>Productos que salen de la granja</span>
            </div>

            {typeof errors.lineas === "string" && (
              <div className="banner banner-error">{errors.lineas}</div>
            )}
            {Array.isArray(errors.lineas) && typeof errors.lineas[0] === "string" && (
              <div className="banner banner-error">{errors.lineas.join(" ")}</div>
            )}

            <div style={{ overflowX: "auto" }}>
              <table className="plan-table" style={{ minWidth: 520 }}>
                <thead>
                  <tr>
                    <th>Producto <span className="req">*</span></th>
                    <th style={{ width: 150 }}>Cantidad <span className="req">*</span></th>
                    <th style={{ width: 40 }}></th>
                  </tr>
                </thead>
                <tbody>
                  {form.lineas.map((linea, index) => {
                    const errLinea = erroresDeLinea(index);
                    const producto = productoDe(linea);
                    const disponible = producto ? producto.stock_actual : null;
                    return (
                      <tr key={index}>
                        <td>
                          <Combobox
                            compact
                            name="id_producto"
                            value={linea.id_producto}
                            onChange={(e) => handleLineaChange(index, e)}
                            onInvalid={handleProductoInvalid}
                            required
                            placeholder="Seleccioná..."
                            options={opciones().map((o) => ({ value: o.id, label: o.label }))}
                          />
                          {(errLinea.id_producto || errLinea.non_field_errors) && (
                            <span className="form-error">
                              {texto(errLinea.id_producto ?? errLinea.non_field_errors)}
                            </span>
                          )}
                        </td>
                        <td>
                          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                            <input
                              name="cantidad"
                              type="number"
                              step="1"
                              min="1"
                              max={disponible != null ? disponible : undefined}
                              value={linea.cantidad}
                              onChange={(e) => handleLineaChange(index, e)}
                              onInvalid={(e) => handleCantidadInvalid(e, disponible)}
                              required
                              placeholder="0"
                              style={estiloCampo}
                            />
                            <span style={{ fontSize: 13, color: "var(--gray-500)" }}>uds.</span>
                          </div>
                          {errLinea.cantidad && (
                            <span className="form-error">{texto(errLinea.cantidad)}</span>
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
                    );
                  })}
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
              {saving ? "Guardando..." : isEdit ? "Guardar cambios" : "Crear salida"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
