/**
 * Definición del menú lateral y matriz rol × sección.
 *
 * Un solo lugar define qué sección ve cada rol: lo consume el sidebar para
 * mostrar u ocultar enlaces, y App.jsx para proteger las rutas. Si estuviera
 * en dos lugares distintos, tarde o temprano quedarían desincronizados.
 *
 * Roles: A = Administrador, O = Operario, C = Consulta
 *
 * IMPORTANTE: esta matriz controla la VISIBILIDAD en el frontend.
 * Los permisos de escritura/lectura de cada endpoint se validan en el backend
 * (permission_classes de cada ViewSet), que responde 403 ante cualquier
 * operación no autorizada aunque el usuario llegue por otra vía.
 * Cuando una sección pase de estática a funcional, replicar esta matriz
 * en el permission_classes del ViewSet correspondiente.
 *
 * Matriz definida según la descripción de usuarios participantes:
 *
 *   Administrador: CRUD completo en todas las secciones.
 *
 *   Operario:
 *     - Dashboard: sí
 *     - Galpones: solo consulta
 *     - Lotes de Gallinas: solo consulta
 *     - Recolección diaria: CRUD completo
 *     - Descartes: CRUD completo
 *     - Salidas: CRUD completo
 *     - Entradas: CRUD completo
 *     - Materias Primas: solo consulta
 *     - Compras, Proveedores, Informes, Productos, Usuarios: sin acceso
 *
 *   Consulta:
 *     - Todas las secciones excepto Productos y Usuarios: solo consulta (lectura)
 *     - Productos, Usuarios: sin acceso
 *
 * Nota: los permisos de escritura (CRUD vs solo consulta) dentro de cada
 * sección se implementan en el backend cuando la sección tenga endpoints
 * propios. En el menú, si el rol puede ver la sección (aunque sea solo para
 * consultar) el enlace aparece; el backend rechaza las operaciones no
 * permitidas con 403.
 */

export const TODOS = ["A", "O", "C"];

export const MENU = [
  {
    grupo: "Principal",
    items: [
      {
        to: "/app/dashboard",
        icono: "fa-gauge-high",
        texto: "Dashboard",
        roles: TODOS,
      },
    ],
  },
  {
    grupo: "Producción",
    items: [
      {
        to: "/app/galpones",
        icono: "fa-warehouse",
        texto: "Galpones",
        roles: TODOS,              // A: CRUD · O: consulta · C: consulta
      },
      {
        to: "/app/lotes",
        icono: "fa-kiwi-bird",
        texto: "Lotes de Gallinas",
        roles: TODOS,              // A: CRUD · O: consulta · C: consulta
      },
      {
        to: "/app/recoleccion",
        icono: "fa-egg",
        texto: "Recolección diaria",
        roles: TODOS,              // A: CRUD · O: CRUD · C: consulta
      },
      {
        to: "/app/descartes",
        icono: "fa-trash-can",
        texto: "Descartes",
        roles: TODOS,              // A: CRUD · O: CRUD · C: consulta
      },
      {
        to: "/app/salidas",
        icono: "fa-truck-ramp-box",
        texto: "Salidas",
        roles: TODOS,              // A: CRUD · O: CRUD · C: consulta
      },
    ],
  },
  {
    grupo: "Insumos",
    items: [
      {
        to: "/app/entradas",
        icono: "fa-dolly",
        texto: "Entradas",
        roles: TODOS,              // A: CRUD · O: CRUD · C: consulta
      },
      {
        to: "/app/materias-primas",
        icono: "fa-boxes-stacked",
        texto: "Materias Primas",
        roles: TODOS,              // A: CRUD · O: consulta · C: consulta
      },
      {
        to: "/app/compras",
        icono: "fa-cart-shopping",
        texto: "Compras",
        roles: ["A", "C"],         // A: CRUD · C: consulta · O: sin acceso
      },
      {
        to: "/app/proveedores",
        icono: "fa-truck",
        texto: "Proveedores",
        roles: ["A", "C"],         // A: CRUD · C: consulta · O: sin acceso
      },
    ],
  },
  {
    grupo: "Gestión",
    items: [
      {
        to: "/app/informes",
        icono: "fa-chart-simple",
        texto: "Informes",
        roles: ["A", "C"],         // A: acceso · C: acceso · O: sin acceso
      },
      {
        to: "/app/productos",
        icono: "fa-egg",
        texto: "Productos",
        roles: ["A"],              // solo Administrador (CU49-54)
      },
      {
        to: "/app/usuarios",
        icono: "fa-users",
        texto: "Usuarios",
        roles: ["A"],              // solo Administrador
      },
    ],
  },
];

/** Devuelve los roles habilitados para una ruta. Se usa en App.jsx. */
export function rolesDe(ruta) {
  for (const grupo of MENU) {
    const item = grupo.items.find((i) => i.to === ruta);
    if (item) return item.roles;
  }
  return TODOS;
}
