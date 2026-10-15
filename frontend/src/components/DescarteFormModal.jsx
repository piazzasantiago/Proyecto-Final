import { useEffect, useState } from "react";
import { createDescarte, updateDescarte } from "../api/descartes";
import { listLotes } from "../api/lotes";

// Debe coincidir con el max_length de `observaciones` en el serializer.
const OBSERVACIONES_MAX = 500;
// Debe coincidir con el max_length de `motivo` en el modelo LineaDescarte.
const MOTIVO_MAX = 200;

export const CATEGORIA_GALPON = "G";
export const CATEGORIA_STOCK = "S";

export const CATEGORIAS = [
  {
    value: CATEGORIA_GALPON,
    label: "Galpón",
    icono: "fa-warehouse",
    ayuda:
      "Algo que se pierde dentro de un galpón: una gallina que muere o deja de producir, alimento servido que se pudrió, un nidal roto, huevos rotos. Es estadístico y no baja el stock; solo las gallinas descuentan de la cantidad del lote.",
  },
  {
    value: CATEGORIA_STOCK,
    label: "Stock",
    icono: "fa-boxes-stacked",
    ayuda:
      "Baja de lo que ya está almacenado: huevos ya recolectados o materias primas listas para consumir. Al finalizarlo descuenta el stock de cada ítem.",
  },
];

// `categorias` indica en qué categorías se puede usar cada tipo de ítem: las
// gallinas solo se descartan desde un galpón.
export const TIPOS = [
  {
    value: "materia_prima",
    label: "Materia prima",
    campo: "id_materia_prima",
    categorias: [CATEGORIA_GALPON, CATEGORIA_STOCK],
  },
  {
    value: "producto",
    label: "Producto",
    campo: "id_producto",
    categorias: [CATEGORIA_GALPON, CATEGORIA_STOCK],
  },
  {
    value: "lote",
    label: "Gallinas (lote)",
    campo: "id_lote",
    categorias: [CATEGORIA_GALPON],
  },
];

function tiposDe(categoria) {
  return TIPOS.filter((t) => t.categorias.includes(categoria));
}

function campoDe(tipo) {
  return TIPOS.find((t) => t.value === tipo).campo;
}

function emptyLinea() {
  return { tipo: "materia_prima", id_item: "", cantidad: "", motivo: "" };
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
      categoria: CATEGORIA_GALPON,
      id_galpon: "",
      fecha: "",
      observaciones: "",
      lineas: [emptyLinea()],
    };
  }
  return {
    categoria: initialData.categoria ?? CATEGORIA_GALPON,
    id_galpon: initialData.galpon?.id_galpon ?? initialData.id_galpon ?? "",
    fecha: initialData.fecha ? initialData.fecha.slice(0, 16) : "",
    observaciones: initialData.observaciones ?? "",
    lineas: initialData.lineas?.length
      ? initialData.lineas.map((l) => ({
          tipo: l.tipo,
          id_item: l.id_materia_prima ?? l.id_producto ?? l.id_lote ?? "",
          cantidad: l.cantidad ?? "",
          motivo: l.motivo ?? "",
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
  return Number.isNaN(n) ? "—" : n.toLocaleString("es-AR", { maximumFractionDigits: 2 });
}

export default function DescarteFormModal({
  galpones = [],
  materiasPrimas = [],
  productos = [],
  initialData,
  onClose,
  onSubmit,
}) {
  const isEdit = Boolean(initialData);
  const [form, setForm] = useState(() => initForm(initialData));
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);
  // Lotes del galpón elegido (solo los activos, o los que ya tenía el descarte).
  const [lotes, setLotes] = useState([]);

  const esStock = form.categoria === CATEGORIA_STOCK;
  const categoriaActual = CATEGORIAS.find((c) => c.value === form.categoria);

  // Los lotes solo hacen falta en los descartes de galpón, y cambian con el galpón.
  useEffect(() => {
    if (esStock || !form.id_galpon) {
      setLotes([]);
      return;
    }
    let cancelado = false;
    listLotes({ id_galpon: form.id_galpon })
      .then((d) => {
        if (!cancelado) setLotes(d.results ?? d);
      })
      .catch(() => {
        if (!cancelado) setLotes([]);
      });
    return () => {
      cancelado = true;
    };
  }, [form.id_galpon, esStock]);

  function handleChange(e) {
    const { name, value } = e.target;
    e.target.setCustomValidity("");
    setForm((f) => {
      const siguiente = { ...f, [name]: value };
      // Al cambiar de galpón, las líneas de gallinas dejan de ser válidas.
      if (name === "id_galpon") {
        siguiente.lineas = f.lineas.map((l) =>
          l.tipo === "lote" ? { ...l, id_item: "" } : l
        );
      }
      return siguiente;
    });
  }

  function handleCategoria(categoria) {
    if (isEdit || categoria === form.categoria) return;
    setErrors({});
    setForm((f) => ({
      ...f,
      categoria,
      // Un descarte de stock no tiene galpón ni admite gallinas.
      id_galpon: categoria === CATEGORIA_STOCK ? "" : f.id_galpon,
      lineas: f.lineas.map((l) =>
        categoria === CATEGORIA_STOCK && l.tipo === "lote"
          ? { ...l, tipo: "materia_prima", id_item: "" }
          : l
      ),
    }));
  }

  function handleLineaChange(index, e) {
    const { name, value } = e.target;
    e.target.setCustomValidity("");
    setForm((f) => ({
      ...f,
      lineas: f.lineas.map((l, i) => {
        if (i !== index) return l;
        // Cambiar el tipo invalida el ítem elegido.
        if (name === "tipo") return { ...l, tipo: value, id_item: "" };
        return { ...l, [name]: value };
      }),
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
        ? "Debe ingresar la fecha y hora del descarte"
        : v.rangeOverflow
        ? "La fecha y hora del descarte no puede ser futura"
        : "La fecha y hora no es válida. Completá día, mes, año, hora y minutos."
    );
  }

  function handleGalponInvalid(e) {
    e.target.setCustomValidity("Debe seleccionar un galpón");
  }

  function handleItemInvalid(e) {
    e.target.setCustomValidity("Debe seleccionar qué se descarta");
  }

  function handleMotivoInvalid(e) {
    e.target.setCustomValidity("Debe indicar el motivo del descarte");
  }

  function handleCantidadInvalid(e, disponible) {
    const v = e.target.validity;
    e.target.setCustomValidity(
      v.valueMissing
        ? "Debe ingresar la cantidad"
        : v.rangeOverflow
        ? `La cantidad supera el stock disponible (${formatNumero(disponible)})`
        : "La cantidad debe ser un número mayor que 0 (los productos y las gallinas, sin decimales)"
    );
  }

  // Stock disponible del ítem elegido (solo se muestra en descartes de stock).
  function stockDe(linea) {
    const id = Number(linea.id_item);
    if (!id) return null;
    if (linea.tipo === "materia_prima") {
      return materiasPrimas.find((m) => m.id_materia_prima === id)?.stock_actual ?? null;
    }
    if (linea.tipo === "producto") {
      return productos.find((p) => p.id_producto === id)?.stock_actual ?? null;
    }
    return null;
  }

  // Opciones de cada tipo. En edición se conservan los ítems que ya tenía el
  // descarte aunque se hayan desactivado o el lote se haya finalizado después.
  function opcionesDe(linea) {
    const idActual = Number(linea.id_item);
    const conStock = (stock) => (esStock ? ` · stock ${formatNumero(stock)}` : "");
    if (linea.tipo === "materia_prima") {
      const lista = materiasPrimas.map((m) => ({
        id: m.id_materia_prima,
        label: `${m.materia_prima} (${m.unidad})${conStock(m.stock_actual)}`,
      }));
      (initialData?.lineas ?? []).forEach((l) => {
        if (l.id_materia_prima && !lista.some((o) => o.id === l.id_materia_prima)) {
          lista.push({ id: l.id_materia_prima, label: `${l.materia_prima_nombre} (inactiva)` });
        }
      });
      return lista;
    }
    if (linea.tipo === "producto") {
      const lista = productos.map((p) => ({
        id: p.id_producto,
        label: `${p.producto}${conStock(p.stock_actual)}`,
      }));
      (initialData?.lineas ?? []).forEach((l) => {
        if (l.id_producto && !lista.some((o) => o.id === l.id_producto)) {
          lista.push({ id: l.id_producto, label: `${l.producto_nombre} (inactivo)` });
        }
      });
      return lista;
    }
    // lote: solo los activos (Transición o Producción) del galpón elegido.
    const lista = lotes
      .filter((l) => l.estado !== "F" || l.id_lote === idActual)
      .map((l) => ({
        id: l.id_lote,
        label:
          `${l.codigo}` +
          (l.cantidad_actual != null ? ` · ${l.cantidad_actual} gallinas` : "") +
          (l.estado === "F" ? " (finalizado)" : ""),
      }));
    (initialData?.lineas ?? []).forEach((l) => {
      if (l.id_lote && !lista.some((o) => o.id === l.id_lote)) {
        lista.push({ id: l.id_lote, label: l.lote_codigo });
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
        categoria: form.categoria,
        fecha: form.fecha,
        observaciones: form.observaciones,
        lineas: form.lineas.map((l) => ({
          [campoDe(l.tipo)]: Number(l.id_item),
          cantidad: String(l.cantidad),
          motivo: l.motivo.trim(),
        })),
      };
      // Los descartes de stock no pertenecen a un galpón.
      if (!esStock) payload.id_galpon = Number(form.id_galpon);

      const result = isEdit
        ? await updateDescarte(initialData.id_descarte, payload)
        : await createDescarte(payload);
      await onSubmit(result);
    } catch (err) {
      if (err.detail && typeof err.detail === "object") {
        setErrors(err.detail);
      } else {
        setErrors({ non_field_errors: [err.message || "No se pudo guardar el descarte."] });
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
          <h3>{isEdit ? "Editar descarte" : "Nuevo descarte"}</h3>
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

            {/* ---- Categoría ---- */}
            <div className="form-group">
              <label>Categoría</label>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                {CATEGORIAS.map((c) => {
                  const activa = form.categoria === c.value;
                  return (
                    <button
                      key={c.value}
                      type="button"
                      className={`btn ${activa ? "btn-green" : "btn-outline"}`}
                      onClick={() => handleCategoria(c.value)}
                      disabled={isEdit && !activa}
                      aria-pressed={activa}
                    >
                      <i className={`fa-solid ${c.icono}`}></i> {c.label}
                    </button>
                  );
                })}
              </div>
              <span className="form-hint">{categoriaActual?.ayuda}</span>
              {isEdit && (
                <span className="form-hint">
                  La categoría no se puede cambiar después de crear el descarte.
                </span>
              )}
              {errors.categoria && <span className="form-error">{texto(errors.categoria)}</span>}
            </div>

            {/* ---- Cabecera ---- */}
            <div className="form-row">
              {!esStock && (
                <div className="form-group full">
                  <label>Galpón</label>
                  <select
                    name="id_galpon"
                    value={form.id_galpon}
                    onChange={handleChange}
                    onInvalid={handleGalponInvalid}
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
                  {errors.id_galpon && (
                    <span className="form-error">{texto(errors.id_galpon)}</span>
                  )}
                  {isEdit && (
                    <span className="form-hint">
                      El galpón no se puede cambiar después de crear el descarte.
                    </span>
                  )}
                </div>
              )}

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
                  placeholder="Notas sobre el descarte (opcional)"
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
              <span>Ítems descartados</span>
            </div>

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
                    <th style={{ width: 150 }}>Tipo</th>
                    <th>Ítem</th>
                    <th style={{ width: 100 }}>Cantidad</th>
                    <th>Motivo</th>
                    <th style={{ width: 40 }}></th>
                  </tr>
                </thead>
                <tbody>
                  {form.lineas.map((linea, index) => {
                    const errLinea = erroresDeLinea(index);
                    const campoItem = campoDe(linea.tipo);
                    const errItem = errLinea[campoItem] ?? errLinea.non_field_errors ?? null;
                    const entera = linea.tipo !== "materia_prima";
                    // En stock, la cantidad no puede superar lo que hay.
                    const disponible = esStock ? stockDe(linea) : null;
                    return (
                      <tr key={index}>
                        <td>
                          <select
                            name="tipo"
                            value={linea.tipo}
                            onChange={(e) => handleLineaChange(index, e)}
                            style={estiloCampo}
                          >
                            {tiposDe(form.categoria).map((t) => (
                              <option key={t.value} value={t.value}>
                                {t.label}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td>
                          <select
                            name="id_item"
                            value={linea.id_item}
                            onChange={(e) => handleLineaChange(index, e)}
                            onInvalid={handleItemInvalid}
                            required
                            style={estiloCampo}
                          >
                            <option value="">
                              {linea.tipo === "lote" && !form.id_galpon
                                ? "Elegí primero el galpón..."
                                : "Seleccioná..."}
                            </option>
                            {opcionesDe(linea).map((o) => (
                              <option key={o.id} value={o.id}>
                                {o.label}
                              </option>
                            ))}
                          </select>
                          {errItem && <span className="form-error">{texto(errItem)}</span>}
                        </td>
                        <td>
                          <input
                            name="cantidad"
                            type="number"
                            step={entera ? "1" : "0.01"}
                            min={entera ? "1" : "0.01"}
                            max={disponible != null ? disponible : undefined}
                            value={linea.cantidad}
                            onChange={(e) => handleLineaChange(index, e)}
                            onInvalid={(e) => handleCantidadInvalid(e, disponible)}
                            required
                            placeholder="0"
                            style={estiloCampo}
                          />
                          {errLinea.cantidad && (
                            <span className="form-error">{texto(errLinea.cantidad)}</span>
                          )}
                        </td>
                        <td>
                          <input
                            name="motivo"
                            type="text"
                            value={linea.motivo}
                            onChange={(e) => handleLineaChange(index, e)}
                            onInvalid={handleMotivoInvalid}
                            maxLength={MOTIVO_MAX}
                            required
                            placeholder="Ej: vencido, rotos, muerte natural"
                            style={estiloCampo}
                          />
                          {errLinea.motivo && (
                            <span className="form-error">{texto(errLinea.motivo)}</span>
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
              <i className="fa-solid fa-plus"></i> Agregar ítem
            </button>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-outline" onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-green" disabled={saving}>
              <i className="fa-solid fa-check"></i>{" "}
              {saving ? "Guardando..." : isEdit ? "Guardar cambios" : "Crear descarte"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
