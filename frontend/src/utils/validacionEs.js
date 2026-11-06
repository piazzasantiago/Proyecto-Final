/**
 * Mensajes de validación de los formularios en español.
 *
 * Los avisos del navegador ("Please fill out this field.") salen en el idioma del navegador,
 * no en el de la página. Acá se reemplazan por textos propios, para todos los formularios del
 * sistema a la vez, sin tocar cada campo.
 */
function mensaje(el) {
  const v = el.validity;
  if (v.valueMissing) {
    if (el.type === "checkbox") return "Marcá esta casilla para continuar.";
    if (el.type === "radio" || el.tagName === "SELECT") return "Seleccioná una opción de la lista.";
    if (el.type === "file") return "Seleccioná un archivo.";
    return "Completá este campo.";
  }
  if (v.typeMismatch) {
    if (el.type === "email") return "Ingresá un correo electrónico válido.";
    if (el.type === "url") return "Ingresá una dirección web válida.";
    return "El valor ingresado no es válido.";
  }
  if (v.patternMismatch) return el.title || "El formato ingresado no es válido.";
  if (v.tooShort) return `Usá al menos ${el.minLength} caracteres.`;
  if (v.tooLong) return `Usá como máximo ${el.maxLength} caracteres.`;
  if (v.rangeUnderflow) return `El valor debe ser mayor o igual a ${el.min}.`;
  if (v.rangeOverflow) return `El valor debe ser menor o igual a ${el.max}.`;
  if (v.stepMismatch || v.badInput) return "Ingresá un valor válido.";
  return "";
}

/** Los mensajes puestos por la aplicación (customError) no se tocan: solo los del navegador. */
const propios = new WeakSet();

export function activarValidacionEnEspanol() {
  document.addEventListener(
    "invalid",
    (e) => {
      const el = e.target;
      if (!el.validity || (el.validity.customError && !propios.has(el))) return;
      const texto = mensaje(el);
      if (texto) {
        el.setCustomValidity(texto);
        propios.add(el);
      }
    },
    true,
  );
  // Al corregir el campo se limpia el aviso; si sigue mal, se vuelve a calcular al enviar.
  const limpiar = (e) => {
    const el = e.target;
    if (el.setCustomValidity && propios.has(el)) {
      el.setCustomValidity("");
      propios.delete(el);
    }
  };
  document.addEventListener("input", limpiar, true);
  document.addEventListener("change", limpiar, true);
}
