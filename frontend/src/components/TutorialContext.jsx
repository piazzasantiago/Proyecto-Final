import { createContext, useContext } from "react";

/**
 * Permite que cualquier pantalla abra el tutorial de su sección sin conocer cómo funciona.
 * Lo provee AppLayout: { iniciarSeccion(id), seccionVista(id) }.
 */
export const TutorialContext = createContext(null);

export function useTutorial() {
  return useContext(TutorialContext);
}
