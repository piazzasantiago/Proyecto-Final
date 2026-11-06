import { useState } from "react";
import { createLote, updateLote } from "../api/lotes";
import Combobox from "./Combobox";

const SEMANAS = [1, 2, 3, 4];

function emptyPlan() {
  return {
    agua_semana1: "", alimento_semana1: "", horas_luz_semana1: "",
    agua_semana2: "", alimento_semana2: "", horas_luz_semana2: "",
    agua_semana3: "", alimento_semana3: "", horas_luz_semana3: "",
    agua_semana4: "", alimento_semana4: "", horas_luz_semana4: "",
  };
}

function initForm(initialData) {
  if (!initialData) {
    return {
      id_linea_compra: "",
      id_galpon_id: "",
      fecha_ingreso: "",
      cantidad_inicial: "",
      observaciones: "",
      plan_transicion: emptyPlan(),
    };
  }
  const p = initialData.plan_transicion || {};
  return {
    id_galpon_id: initialData.galpon?.id_galpon ?? "",
    fecha_ingreso: initialData.fecha_ingreso ?? "",
    cantidad_inicial: initialData.cantidad_inicial ?? "",
    observaciones: initialData.observaciones ?? "",
    plan_transicion: {
      agua_semana1: p.agua_semana1 ?? "",
      alimento_semana1: p.alimento_semana1 ?? "",
      horas_luz_semana1: p.horas_luz_semana1 ?? "",
      agua_semana2: p.agua_semana2 ?? "",
      alimento_semana2: p.alimento_semana2 ?? "",
      horas_luz_semana2: p.horas_luz_semana2 ?? "",
      agua_semana3: p.agua_semana3 ?? "",
      alimento_semana3: p.alimento_semana3 ?? "",
      horas_luz_semana3: p.horas_luz_semana3 ?? "",
      agua_semana4: p.agua_semana4 ?? "",
      alimento_semana4: p.alimento_semana4 ?? "",
      horas_luz_semana4: p.horas_luz_semana4 ?? "",
    },
  };
}

const hoyISO = new Date().toISOString().slice(0, 10);

const miles = (n) => Number(n).toLocaleString("es-AR");

function formatFechaCorta(iso) {
  if (!iso) return "";
  const [y, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
}

export default function LoteFormModal({
  galpones = [],
  lotesPendientes = [],
  initialData,
  onClose,
  onSubmit,
  onCreated,
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

  function handleLoteCompradoInvalid(e) {
    e.target.setCustomValidity("Debe seleccionar el lote comprado que quiere asignar");
  }

  // Lote comprado elegido: de ahí sale la cantidad inicial.
  const loteElegido = lotesPendientes.find(
    (l) => String(l.id_linea_compra) === String(form.id_linea_compra)
  );
  const cantidadInicial = isEdit ? form.cantidad_inicial : loteElegido?.cantidad ?? "";

  // Galpón elegido y si le alcanza la capacidad para las aves del lote (F-07 / F-08).
  const galponElegido = galpones.find((g) => String(g.id_galpon) === String(form.id_galpon_id));
  const capacidad = galponElegido?.capacidad;
  const excedeCapacidad =
    !isEdit && capacidad != null && cantidadInicial !== "" && Number(cantidadInicial) > capacidad;
  const sinGalponesLibres = !isEdit && galpones.length === 0;

  function handleGalponInvalid(e) {
    e.target.setCustomValidity("Debe seleccionar un galpón");
  }

  function handleFechaIngresoInvalid(e) {
    e.target.setCustomValidity(
      e.target.validity.rangeOverflow
        ? "La fecha de ingreso no puede ser una fecha futura"
        : "Debe ingresar la fecha de ingreso"
    );
  }

  function handlePlanChange(e) {
    const { name, value } = e.target;
    setForm((f) => ({
      ...f,
      plan_transicion: { ...f.plan_transicion, [name]: value },
    }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (excedeCapacidad) {
      setErrors({
        id_galpon_id:
          `El galpón tiene capacidad para ${miles(capacidad)} aves y el lote tiene ` +
          `${miles(cantidadInicial)}. Elegí un galpón con mayor capacidad.`,
      });
      return;
    }
    setSaving(true);
    setErrors({});
    try {
      const payload = {
        ...form,
        id_galpon_id: Number(form.id_galpon_id),
        plan_transicion: {
          agua_semana1: form.plan_transicion.agua_semana1,
          alimento_semana1: form.plan_transicion.alimento_semana1,
          horas_luz_semana1: form.plan_transicion.horas_luz_semana1,
          agua_semana2: form.plan_transicion.agua_semana2,
          alimento_semana2: form.plan_transicion.alimento_semana2,
          horas_luz_semana2: form.plan_transicion.horas_luz_semana2,
          agua_semana3: form.plan_transicion.agua_semana3,
          alimento_semana3: form.plan_transicion.alimento_semana3,
          horas_luz_semana3: form.plan_transicion.horas_luz_semana3,
          agua_semana4: form.plan_transicion.agua_semana4,
          alimento_semana4: form.plan_transicion.alimento_semana4,
          horas_luz_semana4: form.plan_transicion.horas_luz_semana4,
        },
      };

      // La cantidad inicial no se envía: sale de la compra del lote.
      delete payload.cantidad_inicial;
      delete payload.id_linea_compra;

      let result;
      if (isEdit) {
        result = await updateLote(initialData.id_lote, payload);
      } else {
        payload.id_linea_compra = Number(form.id_linea_compra);
        result = await createLote(payload);
        if (onCreated) onCreated(result.id_lote);
      }
      await onSubmit(result);
    } catch (err) {
      if (err.detail && typeof err.detail === "object") {
        setErrors(err.detail);
      } else {
        setErrors({ non_field_errors: [err.message || "No se pudo guardar el lote."] });
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-overlay active" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-card" style={{ maxWidth: 640 }}>
        <div className="modal-header">
          <h3>{isEdit ? "Editar lote" : "Nuevo lote"}</h3>
          <button className="modal-close" onClick={onClose}><i className="fa-solid fa-xmark"></i></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {errors.non_field_errors && (
              <div className="banner banner-error">{errors.non_field_errors.join(" ")}</div>
            )}

            {/* ---- Datos del lote ---- */}
            <div className="form-row">
              {!isEdit && (
                <div className="form-group full">
                  <label>Lotes a asignar</label>
                  <Combobox
                    name="id_linea_compra"
                    value={form.id_linea_compra}
                    onChange={handleChange}
                    onInvalid={handleLoteCompradoInvalid}
                    required
                    placeholder="Seleccioná un lote comprado..."
                    options={lotesPendientes.map((l) => ({
                      value: l.id_linea_compra,
                      label:
                        `Comprobante ${l.nro_comprobante} · ${l.proveedor_nombre} · ` +
                        `${Number(l.cantidad).toLocaleString("es-AR")} aves · comprado el ` +
                        `${formatFechaCorta(l.fecha_compra)}`,
                    }))}
                  />
                  {errors.id_linea_compra && (
                    <span className="form-error">
                      {Array.isArray(errors.id_linea_compra)
                        ? errors.id_linea_compra.join(" ")
                        : errors.id_linea_compra}
                    </span>
                  )}
                  <span className="form-hint">
                    Son los lotes de compras finalizadas que todavía no se asignaron a un galpón.
                  </span>
                </div>
              )}

              <div className="form-group full">
                <label>Galpón</label>
                <Combobox
                  name="id_galpon_id"
                  value={form.id_galpon_id}
                  onChange={handleChange}
                  onInvalid={handleGalponInvalid}
                  required
                  disabled={isEdit || sinGalponesLibres}
                  placeholder={isEdit ? "Galpón del lote" : "Seleccioná un galpón libre..."}
                  valueLabel={
                    isEdit && initialData?.galpon
                      ? `G-${String(initialData.galpon.id_galpon).padStart(2, "0")} · ${initialData.galpon.galpon}`
                      : undefined
                  }
                  options={galpones.map((g) => {
                    const noAlcanza = !isEdit && cantidadInicial !== "" && Number(cantidadInicial) > g.capacidad;
                    return {
                      value: g.id_galpon,
                      label:
                        `G-${String(g.id_galpon).padStart(2, "0")} · ${g.galpon} · capacidad ${miles(g.capacidad)} aves` +
                        (noAlcanza ? " (no alcanza para este lote)" : ""),
                      disabled: noAlcanza,
                    };
                  })}
                />
                {sinGalponesLibres && (
                  <span className="form-hint">
                    No hay galpones activos libres. Un galpón queda libre cuando se hace el vaciado
                    sanitario de su lote.
                  </span>
                )}
                {capacidad != null && !excedeCapacidad && (
                  <span className="form-hint">Capacidad del galpón: {miles(capacidad)} aves.</span>
                )}
                {excedeCapacidad && (
                  <span className="form-error">
                    El galpón tiene capacidad para {miles(capacidad)} aves y el lote tiene {miles(cantidadInicial)}.
                  </span>
                )}
                {!isEdit && !sinGalponesLibres && (
                  <span className="form-hint">
                    Solo se listan los galpones activos que no tienen un lote en curso.
                  </span>
                )}
                {errors.id_galpon_id && <span className="form-error">{Array.isArray(errors.id_galpon_id) ? errors.id_galpon_id.join(" ") : errors.id_galpon_id}</span>}
                {isEdit && <span className="form-hint">El galpón no se puede cambiar después de crear el lote.</span>}
              </div>

              <div className="form-group">
                <label>Fecha de ingreso</label>
                <input
                  name="fecha_ingreso"
                  type="date"
                  value={form.fecha_ingreso}
                  onChange={handleChange}
                  onInvalid={handleFechaIngresoInvalid}
                  max={hoyISO}
                  required
                  disabled={isEdit}
                />
                {errors.fecha_ingreso && <span className="form-error">{errors.fecha_ingreso.join(" ")}</span>}
                {isEdit && <span className="form-hint">La fecha de ingreso no se puede modificar.</span>}
              </div>

              <div className="form-group">
                <label>Cantidad inicial (aves)</label>
                <input
                  name="cantidad_inicial"
                  type="number"
                  step="1"
                  min="1"
                  value={cantidadInicial}
                  readOnly
                  disabled
                  placeholder="Se completa con el lote elegido"
                />
                <span className="form-hint">La cantidad inicial viene de la compra.</span>
                {errors.cantidad_inicial && <span className="form-error">{Array.isArray(errors.cantidad_inicial) ? errors.cantidad_inicial.join(" ") : errors.cantidad_inicial}</span>}
              </div>

              <div className="form-group full">
                <label>Observaciones</label>
                <textarea
                  name="observaciones"
                  value={form.observaciones}
                  onChange={handleChange}
                  placeholder="Notas sobre el lote (procedencia, raza, condiciones de ingreso, etc.)"
                />
                {errors.observaciones && <span className="form-error">{errors.observaciones.join(" ")}</span>}
              </div>
            </div>

            {/* ---- Plan de transición ---- */}
            <div className="form-lines-title">
              <span>Plan de transición (4 semanas)</span>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table className="plan-table" style={{ minWidth: 460 }}>
                <thead>
                  <tr>
                    <th style={{ width: 70 }}>Semana</th>
                    <th>Agua (L)</th>
                    <th>Alimento (kg)</th>
                    <th>Luz (hs)</th>
                  </tr>
                </thead>
                <tbody>
                  {SEMANAS.map((s) => (
                    <tr key={s}>
                      <td style={{ fontWeight: 700, color: "var(--gray-700)" }}>{s}</td>
                      <td>
                        <input
                          className="plan-input"
                          name={`agua_semana${s}`}
                          type="number"
                          step="0.01"
                          min="0.01"
                          value={form.plan_transicion[`agua_semana${s}`]}
                          onChange={handlePlanChange}
                          required
                          placeholder="4.20"
                          style={{ width: "100%", padding: "6px 8px", border: "1.5px solid var(--gray-300)", borderRadius: 7, fontSize: 14, fontFamily: "inherit" }}
                        />
                        {errors.plan_transicion?.[`agua_semana${s}`] && (
                          <span className="form-error">{errors.plan_transicion[`agua_semana${s}`].join(" ")}</span>
                        )}
                      </td>
                      <td>
                        <input
                          className="plan-input"
                          name={`alimento_semana${s}`}
                          type="number"
                          step="0.01"
                          min="0.01"
                          value={form.plan_transicion[`alimento_semana${s}`]}
                          onChange={handlePlanChange}
                          required
                          placeholder="18.00"
                          style={{ width: "100%", padding: "6px 8px", border: "1.5px solid var(--gray-300)", borderRadius: 7, fontSize: 14, fontFamily: "inherit" }}
                        />
                        {errors.plan_transicion?.[`alimento_semana${s}`] && (
                          <span className="form-error">{errors.plan_transicion[`alimento_semana${s}`].join(" ")}</span>
                        )}
                      </td>
                      <td>
                        <input
                          className="plan-input"
                          name={`horas_luz_semana${s}`}
                          type="number"
                          step="0.01"
                          min="0.01"
                          max="24"
                          value={form.plan_transicion[`horas_luz_semana${s}`]}
                          onChange={handlePlanChange}
                          required
                          placeholder="10.00"
                          style={{ width: "100%", padding: "6px 8px", border: "1.5px solid var(--gray-300)", borderRadius: 7, fontSize: 14, fontFamily: "inherit" }}
                        />
                        {errors.plan_transicion?.[`horas_luz_semana${s}`] && (
                          <span className="form-error">{errors.plan_transicion[`horas_luz_semana${s}`].join(" ")}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <span className="form-hint">
              La fecha de inicio del plan coincide con la fecha de ingreso del lote. La transición dura como máximo 4 semanas: si pasado ese plazo no se inició la producción, el lote pasa solo a Producción.
            </span>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-outline" onClick={onClose}>Cancelar</button>
            <button type="submit" className="btn btn-green" disabled={saving}>
              <i className="fa-solid fa-check"></i> {saving ? "Guardando..." : isEdit ? "Guardar cambios" : "Crear lote"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
