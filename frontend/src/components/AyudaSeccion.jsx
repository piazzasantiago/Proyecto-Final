import { useTutorial } from "./TutorialContext";

/**
 * Botón "?" del encabezado de cada pantalla: abre el tutorial de esa sección.
 * Mientras el usuario no lo abrió, lleva un puntito para que lo encuentre.
 */
export default function AyudaSeccion({ seccion }) {
  const tutorial = useTutorial();
  if (!tutorial) return null;
  const nuevo = !tutorial.seccionVista(seccion);

  return (
    <button
      type="button"
      className={`ayuda-btn${nuevo ? " ayuda-nueva" : ""}`}
      onClick={() => tutorial.iniciarSeccion(seccion)}
      title="Ver cómo funciona esta pantalla"
      aria-label="Ver cómo funciona esta pantalla"
    >
      <i className="fa-solid fa-circle-question"></i>
    </button>
  );
}
