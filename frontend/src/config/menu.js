/**
 * Definición del menú lateral y de qué rol puede ver cada sección.
 *
 * Un solo lugar define la matriz rol x sección: lo usa el sidebar para mostrar
 * u ocultar enlaces, y App.jsx para proteger las rutas. Si estuviera repetida
 * en los dos lados, tarde o temprano quedarían desincronizadas.
 *
 * Roles: A = Administrador, O = Operario, C = Consulta
 *
 * Criterio (según la descripción de usuarios participantes del proyecto):
 *   - Administrador: acceso total.
 *   - Operario: carga y consulta de la operación diaria de la granja.
 *   - Consulta: solo lectura de la información productiva e informes; no
 *     accede a la administración de usuarios.
 */

export const TODOS = ["A", "O", "C"];

export const MENU = [
  {
    grupo: "Principal",
    items: [
      { to: "/app/dashboard", icono: "fa-gauge-high", texto: "Dashboard", roles: TODOS },
    ],
  },
  {
    grupo: "Producción",
    items: [
      { to: "/app/galpones", icono: "fa-warehouse", texto: "Galpones", roles: TODOS },
      { to: "/app/lotes", icono: "fa-kiwi-bird", texto: "Lotes de Gallinas", roles: TODOS },
      { to: "/app/recoleccion", icono: "fa-egg", texto: "Recolección diaria", roles: TODOS },
      { to: "/app/descartes", icono: "fa-trash-can", texto: "Descartes", roles: TODOS },
      { to: "/app/salidas", icono: "fa-truck-ramp-box", texto: "Salidas", roles: TODOS },
    ],
  },
  {
    grupo: "Insumos",
    items: [
      { to: "/app/entradas", icono: "fa-dolly", texto: "Entradas", roles: TODOS },
      { to: "/app/materias-primas", icono: "fa-boxes-stacked", texto: "Materias Primas", roles: TODOS },
      { to: "/app/compras", icono: "fa-cart-shopping", texto: "Compras", roles: ["A"] },
      { to: "/app/proveedores", icono: "fa-truck", texto: "Proveedores", roles: ["A"] },
    ],
  },
  {
    grupo: "Gestión",
    items: [
      { to: "/app/informes", icono: "fa-chart-simple", texto: "Informes", roles: ["A"] },
      { to: "/app/usuarios", icono: "fa-users", texto: "Usuarios", roles: ["A"] },
    ],
  },
];

/** Devuelve los roles habilitados para una ruta. Se usa al proteger rutas. */
export function rolesDe(ruta) {
  for (const grupo of MENU) {
    const item = grupo.items.find((i) => i.to === ruta);
    if (item) return item.roles;
  }
  return TODOS;
}
