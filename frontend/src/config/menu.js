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
 *
 * Orden del menú (F-24). Las secciones van de lo que más se usa a lo que menos:
 *
 *   Principal   lo primero que se abre al entrar al sistema.
 *   Producción  el ciclo productivo y las operaciones de todos los días:
 *               primero dónde y con qué se produce (Galpones y Lotes) y después
 *               lo que se carga a diario (Recolección, Entradas, Descartes y
 *               Salidas). Entradas vive acá, y no en Insumos, porque llevar
 *               alimento al galpón es una tarea diaria del operario, igual que
 *               recolectar.
 *   Insumos     el abastecimiento, que se toca cada tanto: cuando se pide, se
 *               compra o se da de alta un proveedor.
 *   Gestión     catálogo, análisis y administración del sistema.
 *
 * Matriz definida según la descripción de usuarios participantes:
 *
 *   Administrador: CRUD completo en todas las secciones.
 *
 *   Operario:
 *     - Dashboard: sí (solo los datos de sus galpones asignados)
 *     - Galpones: solo consulta
 *     - Lotes de Gallinas: solo consulta
 *     - Recolección diaria: CRUD completo
 *     - Entradas: CRUD completo
 *     - Descartes: CRUD completo
 *     - Salidas: CRUD completo
 *     - Materias Primas: solo consulta
 *     - Compras, Proveedores, Productos, Informes y Usuarios: sin acceso
 *
 *   Consulta:
 *     - Todas las secciones excepto Usuarios: solo consulta (lectura)
 *     - Usuarios: sin acceso
 *
 * En el menú, si el rol puede ver la sección (aunque sea solo para consultar)
 * el enlace aparece; el backend rechaza las operaciones no permitidas con 403.
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
        to: "/app/entradas",
        icono: "fa-dolly",
        texto: "Entradas",
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
        to: "/app/productos",
        icono: "fa-egg",
        texto: "Productos",
        roles: ["A", "C"],         // A: CRUD completo · C: solo consulta (CU49-54)
      },
      {
        to: "/app/informes",
        icono: "fa-chart-simple",
        texto: "Informes",
        roles: ["A", "C"],         // A: acceso · C: acceso · O: sin acceso
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
