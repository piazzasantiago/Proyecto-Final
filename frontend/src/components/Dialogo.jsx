import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

const DialogoContext = createContext(null);

/**
 * Cuadros de confirmación y de aviso con el estilo del sistema, en lugar de los
 * cartelitos nativos del navegador (confirm / alert).
 *
 *   const { confirmar, avisar } = useDialogo();
 *   if (!(await confirmar({ titulo, mensaje, confirmarTexto, peligro: true }))) return;
 *   await avisar({ titulo: "No se pudo eliminar", mensaje: err.message });
 *
 * `confirmar` devuelve una promesa con true (aceptó) o false (canceló o cerró);
 * `avisar` espera a que la persona lo cierre.
 */
export function DialogoProvider({ children }) {
  const [dialogo, setDialogo] = useState(null);
  const resolverRef = useRef(null);

  const abrir = useCallback(
    (config) =>
      new Promise((resolve) => {
        resolverRef.current = resolve;
        setDialogo(config);
      }),
    []
  );

  const confirmar = useCallback((opciones) => abrir({ tipo: "confirmar", ...opciones }), [abrir]);
  const avisar = useCallback((opciones) => abrir({ tipo: "aviso", ...opciones }), [abrir]);

  function cerrar(resultado) {
    setDialogo(null);
    resolverRef.current?.(resultado);
    resolverRef.current = null;
  }

  return (
    <DialogoContext.Provider value={{ confirmar, avisar }}>
      {children}
      {dialogo && <Dialogo config={dialogo} onCerrar={cerrar} />}
    </DialogoContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useDialogo() {
  const ctx = useContext(DialogoContext);
  if (!ctx) throw new Error("useDialogo debe usarse dentro de <DialogoProvider>.");
  return ctx;
}

function Dialogo({ config, onCerrar }) {
  const esConfirmacion = config.tipo === "confirmar";
  const peligro = Boolean(config.peligro);
  const esError = !esConfirmacion && config.variante !== "info";
  const botonRef = useRef(null);

  // El foco va a "Cancelar" si la acción es destructiva (evita un Enter accidental).
  useEffect(() => {
    botonRef.current?.focus();
  }, []);

  useEffect(() => {
    function alTeclear(e) {
      if (e.key === "Escape") {
        e.stopPropagation();
        onCerrar(false);
      }
    }
    document.addEventListener("keydown", alTeclear, true);
    return () => document.removeEventListener("keydown", alTeclear, true);
  });

  const icono = esConfirmacion
    ? peligro
      ? "fa-triangle-exclamation"
      : "fa-circle-question"
    : esError
    ? "fa-circle-exclamation"
    : "fa-circle-info";
  const claseIcono = peligro || esError ? "dialogo-icono peligro" : "dialogo-icono";

  return (
    <div className="modal-overlay active dialogo-overlay" onClick={(e) => e.target === e.currentTarget && onCerrar(false)}>
      <div className="modal-card dialogo-card" role="alertdialog" aria-modal="true">
        <div className="dialogo-cuerpo">
          <div className={claseIcono}>
            <i className={`fa-solid ${icono}`}></i>
          </div>
          <div className="dialogo-texto">
            <h3>{config.titulo ?? (esConfirmacion ? "Confirmar" : "Aviso")}</h3>
            {config.mensaje && <p>{config.mensaje}</p>}
          </div>
        </div>
        <div className="dialogo-botones">
          {esConfirmacion && (
            <button
              type="button"
              className="btn btn-outline"
              ref={peligro ? botonRef : null}
              onClick={() => onCerrar(false)}
            >
              {config.cancelarTexto ?? "Cancelar"}
            </button>
          )}
          <button
            type="button"
            className={`btn ${peligro ? "btn-danger" : "btn-green"}`}
            ref={peligro ? null : botonRef}
            onClick={() => onCerrar(true)}
          >
            {config.confirmarTexto ?? (esConfirmacion ? "Aceptar" : "Entendido")}
          </button>
        </div>
      </div>
    </div>
  );
}
