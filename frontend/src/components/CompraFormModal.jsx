import { useState } from "react";
import { createCompra, updateCompra } from "../api/compras";

// Debe coincidir con el max_length de `observaciones` en el serializer.
const OBSERVACIONES_MAX = 500;
const CATEGORIA_MATERIAS = "M";
const CATEGORIA_LOTES = "L";

function emptyLinea() {
  return { id_materia_prima: "", cantidad: "", precio_unitario: "" };
}

// Fecha local de hoy (AAAA-MM-DD): máximo permitido en el input de fecha.
function hoyLocal() {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 10);
}

function initForm(initialData) {
  if (!initialData) {
    return {
      categoria: CATEGORIA_MATERIAS,
      id_proveedor: "",
      tipo: "C",
      nro_factura: "",
      fecha: "",
      observaciones: "",
      lineas: [emptyLinea()],
    };
  }
  return {
    categoria: initialData.categoria,
    id_proveedor: initialData.proveedor?.id_proveedor ?? initialData.id_proveedor ?? "",
    tipo: initialData.tipo ?? "C",
    nro_factura: initialData.nro_factura ?? "",
    fecha: initialData.fecha ?? "",
    observaciones: initialData.observaciones ?? "",
    lineas: initialData.lineas?.length
      ? initialData.lineas.map((l) => ({
          id_materia_prima: l.id_materia_prima ?? "",
          cantidad: l.cantidad ?? "",
          precio_unitario: l.precio_unitario ?? "",
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

function formatPrecio(valor) {
  const n = Number(valor);
  return Number.isNaN(n)
    ? "—"
    : n.toLocaleString("es-AR", { style: "currency", currency: "ARS", minimumFractionDigits: 2 });
}

export default function CompraFormModal({
  proveedores = [],
  materiasPrimas = [],
  initialData,
  onClose,
  onSubmit,
}) {
  const isEdit = Boolean(initialData);
  const [form, setForm] = useState(() => initForm(initialData));
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);

  const esDeLotes = form.categoria === CATEGORIA_LOTES;

  function handleChange(e) {
    const { name, value } = e.target;
    e.target.setCustomValidity("");
    setForm((f) => ({ ...f, [name]: value }));
  }

  // Al cambiar de categoría (solo al crear) las líneas empiezan de nuevo.
  function handleCategoria(e) {
    const categoria = e.target.value;
    setForm((f) => ({ ...f, categoria, lineas: [emptyLinea()] }));
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
        ? "Debe ingresar la fecha de la compra"
        : v.rangeOverflow
        ? "La fecha de la compra no puede ser futura"
        : "La fecha no es válida. Completá día, mes y año."
    );
  }

  function handleRequerido(mensaje) {
    return (e) => e.target.setCustomValidity(mensaje);
  }

  function handleCantidadInvalid(e) {
    const v = e.target.validity;
    e.target.setCustomValidity(
      v.valueMissing
        ? esDeLotes
          ? "Debe ingresar la cantidad de aves"
          : "Debe ingresar la cantidad"
        : esDeLotes
        ? "La cantidad de aves debe ser un número entero mayor que 0"
        : "La cantidad debe ser un número mayor que 0, con hasta 2 decimales"
    );
  }

  function handlePrecioInvalid(e) {
    const v = e.target.validity;
    e.target.setCustomValidity(
      v.valueMissing
        ? "Debe ingresar el precio unitario"
        : "El precio debe ser un número mayor que 0, con hasta 2 decimales"
    );
  }

  // Opciones de proveedor y materia prima: solo activos, pero en edición se
  // conservan los que ya tenía la compra aunque se hayan dado de baja después.
  function opcionesProveedor() {
    const lista = proveedores
      .filter((p) => p.estado === "A" || p.id_proveedor === Number(form.id_proveedor))
      .map((p) => ({ id: p.id_proveedor, label: p.nombre }));
    if (isEdit && !lista.some((o) => o.id === Number(form.id_proveedor))) {
      lista.push({
        id: Number(form.id_proveedor),
        label: initialData.proveedor?.nombre ?? "Proveedor",
      });
    }
    return lista;
  }

  function opcionesMateria() {
    const lista = materiasPrimas.map((m) => ({
      id: m.id_materia_prima,
      label: `${m.materia_prima} (${m.unidad})`,
    }));
    (initialData?.lineas ?? []).forEach((l) => {
      if (l.id_materia_prima && !lista.some((o) => o.id === l.id_materia_prima)) {
        lista.push({ id: l.id_materia_prima, label: `${l.materia_prima_nombre} (inactiva)` });
      }
    });
    return lista;
  }

  function unidadDe(linea) {
    const id = Number(linea.id_materia_prima);
    return id ? materiasPrimas.find((m) => m.id_materia_prima === id)?.unidad ?? "" : "";
  }

  function subtotalDe(linea) {
    const total = Number(linea.cantidad) * Number(linea.precio_unitario);
    return Number.isNaN(total) ? 0 : total;
  }

  const total = form.lineas.reduce((acc, l) => acc + subtotalDe(l), 0);

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setErrors({});
    try {
      const payload = {
        id_proveedor: Number(form.id_proveedor),
        tipo: form.tipo,
        nro_factura: form.nro_factura.trim(),
        fecha: form.fecha,
        observaciones: form.observaciones,
        lineas: form.lineas.map((l) => ({
          ...(esDeLotes ? {} : { id_materia_prima: Number(l.id_materia_prima) }),
          cantidad: String(l.cantidad),
          precio_unitario: String(l.precio_unitario),
        })),
      };
      if (!isEdit) payload.categoria = form.categoria;

      const result = isEdit
        ? await updateCompra(initialData.id_compra, payload)
        : await createCompra(payload);
      await onSubmit(result);
    } catch (err) {
      if (err.detail && typeof err.detail === "object") {
        setErrors(err.detail);
      } else {
        setErrors({ non_field_errors: [err.message || "No se pudo guardar la compra."] });
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
      <div className="modal-card" style={{ maxWidth: 860 }}>
        <div className="modal-header">
          <h3>{isEdit ? "Editar compra" : "Nueva compra"}</h3>
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
              <div className="form-group">
                <label>Categoría</label>
                <select
                  name="categoria"
                  value={form.categoria}
                  onChange={handleCategoria}
                  disabled={isEdit}
                >
                  <option value={CATEGORIA_MATERIAS}>Materias primas</option>
                  <option value={CATEGORIA_LOTES}>Lotes de gallinas</option>
                </select>
                {errors.categoria && <span className="form-error">{texto(errors.categoria)}</span>}
                {isEdit && (
                  <span className="form-hint">
                    La categoría no se puede cambiar después de crear la compra.
                  </span>
                )}
              </div>

              <div className="form-group">
                <label>Proveedor</label>
                <select
                  name="id_proveedor"
                  value={form.id_proveedor}
                  onChange={handleChange}
                  onInvalid={handleRequerido("Debe seleccionar un proveedor")}
                  required
                >
                  <option value="">Seleccioná un proveedor activo...</option>
                  {opcionesProveedor().map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.label}
                    </option>
                  ))}
                </select>
                {errors.id_proveedor && (
                  <span className="form-error">{texto(errors.id_proveedor)}</span>
                )}
              </div>

              <div className="form-group">
                <label>Nº de factura</label>
                <input
                  name="nro_factura"
                  type="text"
                  value={form.nro_factura}
                  onChange={handleChange}
                  onInvalid={handleRequerido("Debe ingresar el número de factura")}
                  maxLength={20}
                  placeholder="0001-00004521"
                  required
                />
                {errors.nro_factura && (
                  <span className="form-error">{texto(errors.nro_factura)}</span>
                )}
              </div>

              <div className="form-group">
                <label>Fecha</label>
                <input
                  name="fecha"
                  type="date"
                  value={form.fecha}
                  onChange={handleChange}
                  onInvalid={handleFechaInvalid}
                  max={hoyLocal()}
                  required
                />
                {errors.fecha && <span className="form-error">{texto(errors.fecha)}</span>}
              </div>

              <div className="form-group">
                <label>Tipo</label>
                <select name="tipo" value={form.tipo} onChange={handleChange}>
                  <option value="C">Contado</option>
                  <option value="X">Cuenta corriente</option>
                </select>
                {errors.tipo && <span className="form-error">{texto(errors.tipo)}</span>}
              </div>

              <div className="form-group full">
                <label>Observaciones</label>
                <textarea
                  name="observaciones"
                  value={form.observaciones}
                  onChange={handleChange}
                  maxLength={OBSERVACIONES_MAX}
                  placeholder="Notas sobre la compra (opcional)"
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
              <span>{esDeLotes ? "Lotes comprados" : "Materias primas compradas"}</span>
            </div>
            {!esDeLotes && (
              <span className="form-hint">
                Si la materia prima todavía no existe, creala primero desde “Materias primas”.
              </span>
            )}
            {esDeLotes && (
              <span className="form-hint">
                Cada línea es un lote. Cuando finalices la compra, quedará esperando que lo asignes
                a un galpón desde “Lotes de gallinas”.
              </span>
            )}

            {typeof errors.lineas === "string" && (
              <div className="banner banner-error">{errors.lineas}</div>
            )}
            {Array.isArray(errors.lineas) && typeof errors.lineas[0] === "string" && (
              <div className="banner banner-error">{errors.lineas.join(" ")}</div>
            )}

            <div style={{ overflowX: "auto" }}>
              <table className="plan-table" style={{ minWidth: 640 }}>
                <thead>
                  <tr>
                    <th>{esDeLotes ? "Concepto" : "Materia prima"}</th>
                    <th style={{ width: 150 }}>{esDeLotes ? "Cantidad de aves" : "Cantidad"}</th>
                    <th style={{ width: 150 }}>{esDeLotes ? "Precio por ave" : "Precio unitario"}</th>
                    <th style={{ width: 130, textAlign: "right" }}>Subtotal</th>
                    <th style={{ width: 40 }}></th>
                  </tr>
                </thead>
                <tbody>
                  {form.lineas.map((linea, index) => {
                    const errLinea = erroresDeLinea(index);
                    return (
                      <tr key={index}>
                        <td>
                          {esDeLotes ? (
                            <span>Lote de gallinas</span>
                          ) : (
                            <>
                              <select
                                name="id_materia_prima"
                                value={linea.id_materia_prima}
                                onChange={(e) => handleLineaChange(index, e)}
                                onInvalid={handleRequerido("Debe seleccionar una materia prima")}
                                required
                                style={estiloCampo}
                              >
                                <option value="">Seleccioná...</option>
                                {opcionesMateria().map((o) => (
                                  <option key={o.id} value={o.id}>
                                    {o.label}
                                  </option>
                                ))}
                              </select>
                              {(errLinea.id_materia_prima || errLinea.non_field_errors) && (
                                <span className="form-error">
                                  {texto(errLinea.id_materia_prima ?? errLinea.non_field_errors)}
                                </span>
                              )}
                            </>
                          )}
                        </td>
                        <td>
                          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                            <input
                              name="cantidad"
                              type="number"
                              step={esDeLotes ? "1" : "0.01"}
                              min={esDeLotes ? "1" : "0.01"}
                              value={linea.cantidad}
                              onChange={(e) => handleLineaChange(index, e)}
                              onInvalid={handleCantidadInvalid}
                              required
                              placeholder="0"
                              style={estiloCampo}
                            />
                            {!esDeLotes && unidadDe(linea) && (
                              <span style={{ fontSize: 13, color: "var(--gray-500)" }}>
                                {unidadDe(linea)}
                              </span>
                            )}
                          </div>
                          {errLinea.cantidad && (
                            <span className="form-error">{texto(errLinea.cantidad)}</span>
                          )}
                        </td>
                        <td>
                          <input
                            name="precio_unitario"
                            type="number"
                            step="0.01"
                            min="0.01"
                            value={linea.precio_unitario}
                            onChange={(e) => handleLineaChange(index, e)}
                            onInvalid={handlePrecioInvalid}
                            required
                            placeholder="0,00"
                            style={estiloCampo}
                          />
                          {errLinea.precio_unitario && (
                            <span className="form-error">{texto(errLinea.precio_unitario)}</span>
                          )}
                        </td>
                        <td style={{ textAlign: "right" }}>{formatPrecio(subtotalDe(linea))}</td>
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
                <tfoot>
                  <tr>
                    <td colSpan={3} style={{ textAlign: "right", fontWeight: 600 }}>
                      Total
                    </td>
                    <td style={{ textAlign: "right", fontWeight: 600 }}>{formatPrecio(total)}</td>
                    <td></td>
                  </tr>
                </tfoot>
              </table>
            </div>

            <button
              type="button"
              className="btn btn-outline"
              style={{ marginTop: 8, fontSize: 13 }}
              onClick={addLinea}
            >
              <i className="fa-solid fa-plus"></i> {esDeLotes ? "Agregar lote" : "Agregar materia prima"}
            </button>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-outline" onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-green" disabled={saving}>
              <i className="fa-solid fa-check"></i>{" "}
              {saving ? "Guardando..." : isEdit ? "Guardar cambios" : "Crear compra"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
