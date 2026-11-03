/**
 * Tutoriales de cada sección (el botón "?" del encabezado de la pantalla).
 *
 * Mismo formato que config/tutorial.js, con dos diferencias:
 *   - No llevan `ruta`: el tutorial se abre estando ya en la sección.
 *   - `abrir: "sec-fila"` hace que, si el elemento del paso (por ejemplo el detalle) todavía no
 *     está en pantalla, el tutorial toque la primera fila de la lista para mostrarlo. Si la lista
 *     está vacía, el paso se salta.
 *
 * Los elementos resaltados llevan estos data-tutorial en cada pantalla:
 *   sec-nuevo     botón para crear un registro (solo si el rol puede)
 *   sec-filtros   barra de filtros
 *   sec-lista     lista, tarjetas o tablero con los registros
 *   sec-detalle   panel de detalle del registro elegido
 *   sec-acciones  botones del detalle (editar, finalizar, eliminar...)
 *
 * Roles: A = Administrador, O = Operario, C = Consulta.
 */

const ESCRIBEN = ["A", "O"];

/** Pasos que se repiten casi igual en las pantallas de registros diarios. */
function pasosDeRegistro({ nombre, intro, nuevo, filtros, lista, detalle, acciones, ciclo }) {
  return [
    { id: "intro", titulo: nombre, texto: intro },
    { id: "nuevo", objetivo: "sec-nuevo", roles: ESCRIBEN, titulo: "Cargar un registro nuevo", texto: nuevo },
    { id: "filtros", objetivo: "sec-filtros", titulo: "Filtros", texto: filtros },
    { id: "lista", objetivo: "sec-lista", titulo: "El listado", texto: lista },
    { id: "detalle", objetivo: "sec-detalle", abrir: "sec-fila", lado: ["izquierda", "abajo", "arriba"], titulo: "El detalle", texto: detalle },
    { id: "acciones", objetivo: "sec-acciones", abrir: "sec-fila", lado: ["izquierda", "abajo", "arriba"], roles: ESCRIBEN, titulo: "Qué podés hacer con un registro", texto: acciones },
    { id: "ciclo", titulo: "Pendiente y finalizado", texto: ciclo },
  ];
}

export const SECCIONES = {
  recoleccion: pasosDeRegistro({
    nombre: "Recolección diaria",
    intro: "Acá se registran los huevos que se recolectan en cada galpón, por producto.",
    nuevo: "Registrá una recolección: elegís el galpón y cargás la cantidad de huevos de cada producto.",
    filtros: "Filtrá por fechas, galpón, lote y estado para encontrar una recolección.",
    lista: "Cada fila es una recolección, con su galpón, lote, total de unidades y estado. Tocá una para ver el detalle.",
    detalle: "Los datos completos: qué productos y cuántas unidades se recolectaron, quién la cargó y las observaciones.",
    acciones: {
      A: "Mientras está pendiente podés editarla, finalizarla o eliminarla.",
      O: "Mientras está pendiente podés editarla o finalizarla.",
    },
    ciclo: {
      A: "Una recolección nace Pendiente y todavía se puede corregir. Cuando está todo bien, la finalizás y esos huevos se suman al stock. Una vez finalizada ya no se puede editar.",
      O: "Una recolección nace Pendiente y todavía se puede corregir. Cuando está todo bien, la finalizás y esos huevos se suman al stock. Una vez finalizada ya no se puede editar.",
      C: "Una recolección puede estar Pendiente (todavía se puede corregir) o Finalizada. Solo las finalizadas se suman al stock.",
    },
  }),

  entradas: pasosDeRegistro({
    nombre: "Entradas",
    intro: "Acá se registra la materia prima que sale del depósito y se lleva a un galpón, por ejemplo el balanceado de los comederos.",
    nuevo: "Registrá una entrada: elegís el galpón y las materias primas con sus cantidades.",
    filtros: "Filtrá por fechas, galpón, materia prima y estado para encontrar una entrada.",
    lista: "Cada fila es una entrada, con su galpón, fecha y estado. Tocá una para ver el detalle.",
    detalle: "Los datos completos: qué materias primas y qué cantidades se llevaron al galpón, y quién la cargó.",
    acciones: "Mientras está pendiente podés editarla, finalizarla o eliminarla.",
    ciclo: {
      A: "Una entrada nace Pendiente y todavía se puede corregir. Al finalizarla se descuenta del stock de cada materia prima y ya no se puede editar.",
      O: "Una entrada nace Pendiente y todavía se puede corregir. Al finalizarla se descuenta del stock de cada materia prima y ya no se puede editar.",
      C: "Una entrada puede estar Pendiente (todavía se puede corregir) o Finalizada. Al finalizarse se descuenta del stock de cada materia prima.",
    },
  }),

  descartes: pasosDeRegistro({
    nombre: "Descartes",
    intro: "Acá se registran las bajas: las que ocurren en un galpón (para estadística) y las bajas del stock de productos y materias primas.",
    nuevo: "Registrá un descarte: elegís de qué categoría es y cargás lo que se descarta.",
    filtros: "Filtrá por fechas, categoría (de galpón o de stock) y estado.",
    lista: "Cada fila es un descarte, con su categoría, fecha y estado. Tocá uno para ver el detalle.",
    detalle: "Los datos completos: qué se descartó, en qué cantidad, de qué tipo es y quién lo cargó.",
    acciones: "Mientras está pendiente podés editarlo, finalizarlo o eliminarlo.",
    ciclo: {
      A: "Un descarte nace Pendiente y todavía se puede corregir. Los de galpón son solo estadísticos y no tocan el stock; los de stock, al finalizarse, se descuentan del stock de cada ítem. Finalizado, ya no se puede editar.",
      O: "Un descarte nace Pendiente y todavía se puede corregir. Los de galpón son solo estadísticos y no tocan el stock; los de stock, al finalizarse, se descuentan del stock de cada ítem. Finalizado, ya no se puede editar.",
      C: "Un descarte puede estar Pendiente o Finalizado. Los de galpón son solo estadísticos; los de stock, al finalizarse, se descuentan del stock de cada ítem.",
    },
  }),

  salidas: pasosDeRegistro({
    nombre: "Salidas",
    intro: "Acá se registran los productos que salen de la granja, por ejemplo el camión que se lleva los huevos para la venta.",
    nuevo: "Registrá una salida: elegís los productos y las cantidades que se llevan.",
    filtros: "Filtrá por fechas, producto y estado para encontrar una salida.",
    lista: "Cada fila es una salida, con su fecha y estado. Tocá una para ver el detalle.",
    detalle: "Los datos completos: qué productos y qué cantidades salieron, y quién la cargó.",
    acciones: "Mientras está pendiente podés editarla, finalizarla o eliminarla.",
    ciclo: {
      A: "Una salida nace Pendiente y todavía se puede corregir. Al finalizarla se descuenta del stock de cada producto y ya no se puede editar.",
      O: "Una salida nace Pendiente y todavía se puede corregir. Al finalizarla se descuenta del stock de cada producto y ya no se puede editar.",
      C: "Una salida puede estar Pendiente (todavía se puede corregir) o Finalizada. Al finalizarse se descuenta del stock de cada producto.",
    },
  }),

  galpones: [
    {
      id: "intro",
      titulo: "Galpones",
      texto: {
        A: "Las instalaciones donde se alojan los lotes de gallinas. Acá las administrás.",
        O: "Las instalaciones donde se alojan los lotes de gallinas. Ves los galpones que tenés asignados.",
        C: "Las instalaciones donde se alojan los lotes de gallinas. Acá las consultás.",
      },
    },
    { id: "nuevo", objetivo: "sec-nuevo", roles: ["A"], titulo: "Crear un galpón", texto: "Tocá este botón para dar de alta un galpón nuevo, con su nombre y su capacidad de aves." },
    { id: "filtros", objetivo: "sec-filtros", titulo: "Buscar y filtrar", texto: "Buscá por nombre o descripción y filtrá por estado (activo o dado de baja)." },
    { id: "lista", objetivo: "sec-lista", titulo: "Las tarjetas", texto: "Cada tarjeta es un galpón, con su código, capacidad y estado. Tocá una para ver el detalle." },
    { id: "detalle", objetivo: "sec-detalle", abrir: "sec-fila", lado: ["izquierda", "abajo", "arriba"], titulo: "El detalle", texto: "La capacidad, los operarios asignados y lo que hay en el galpón." },
    {
      id: "acciones",
      objetivo: "sec-acciones",
      abrir: "sec-fila",
      lado: ["izquierda", "abajo", "arriba"],
      roles: ["A"],
      titulo: "Qué podés hacer con un galpón",
      texto: "Podés editarlo, darlo de baja (o activarlo de nuevo) y eliminarlo.",
    },
  ],

  lotes: [
    {
      id: "intro",
      titulo: "Lotes de gallinas",
      texto: "El seguimiento del ciclo de vida de cada lote, desde que ingresa hasta el vaciado sanitario.",
    },
    { id: "nuevo", objetivo: "sec-nuevo", roles: ["A"], titulo: "Crear un lote", texto: "Los lotes se compran en Compras; acá se asignan a un galpón con este botón." },
    { id: "filtros", objetivo: "sec-filtros", titulo: "Buscar y filtrar", texto: "Buscá un lote por su código y filtrá por fechas y galpón." },
    { id: "lista", objetivo: "sec-lista", titulo: "Las tres etapas", texto: "Los lotes se agrupan en tres columnas según su etapa: Transición, Producción y Finalizado. Tocá un lote para ver el detalle." },
    { id: "detalle", objetivo: "sec-detalle", abrir: "sec-fila", lado: ["izquierda", "abajo", "arriba"], titulo: "El detalle", texto: "El recorrido del lote por sus etapas y su plan de producción." },
    {
      id: "acciones",
      objetivo: "sec-acciones",
      abrir: "sec-fila",
      lado: ["izquierda", "abajo", "arriba"],
      roles: ["A"],
      titulo: "Qué podés hacer con un lote",
      texto: "Podés editarlo, iniciar la producción cuando termina la transición, hacer el vaciado sanitario al cerrar su ciclo, o eliminarlo.",
    },
    {
      id: "ciclo",
      titulo: "El ciclo de un lote",
      texto: "Un lote empieza en Transición, pasa a Producción cuando se inicia y termina en Finalizado con el vaciado sanitario.",
    },
  ],
};

/** Los pasos de una sección para un rol, con el texto ya elegido. */
export function pasosSeccion(id, rol) {
  return (SECCIONES[id] ?? [])
    .filter((p) => !p.roles || p.roles.includes(rol))
    .map((p) => ({ ...p, texto: typeof p.texto === "string" ? p.texto : p.texto?.[rol] ?? "" }));
}

// Qué secciones ya abrió el usuario (para el puntito del botón "?"), en el navegador y por usuario.
const clave = (usuario) => `avigest-tutorial-secciones:${usuario?.id ?? "anon"}`;

export function seccionesVistas(usuario) {
  try {
    return JSON.parse(localStorage.getItem(clave(usuario)) ?? "[]");
  } catch {
    return [];
  }
}

export function marcarSeccionVista(usuario, id) {
  try {
    const vistas = seccionesVistas(usuario);
    if (!vistas.includes(id)) localStorage.setItem(clave(usuario), JSON.stringify([...vistas, id]));
  } catch {
    // Sin almacenamiento: el puntito vuelve a aparecer, sin consecuencias.
  }
}
