/**
 * Pasos del tutorial guiado y recordatorio de "ya lo vio".
 *
 * Cada paso resalta un elemento de la pantalla, el que lleva `data-tutorial="<objetivo>"`.
 * Un paso sin `objetivo` se muestra centrado. Si el elemento no existe (por ejemplo, no hay
 * stock cargado todavía), el paso se salta solo.
 *
 *   objetivo  nombre del atributo data-tutorial del elemento a resaltar
 *   ruta      pantalla donde está ese elemento; el tutorial navega hasta ahí
 *   menu      true si el elemento vive en el menú lateral (en tablet se abre solo)
 *   movil     cambios para el celular (hasta 700 px), donde no hay menú lateral sino la barra de abajo
 *             y la hoja «Más»: { objetivo, hoja: "mas" | "cuenta", lado, texto }
 *   soloMovil true si el paso solo existe en celular (hasta 700 px)
 *   roles     roles que ven el paso; sin esta clave, lo ven todos
 *   texto     un texto, o uno por rol: { A: "...", O: "...", C: "..." }
 *
 * Roles: A = Administrador, O = Operario, C = Consulta.
 */

export const PASOS = [
  {
    id: "bienvenida",
    titulo: "¡Bienvenido a AviGest!",
    texto:
      "En un minuto te mostramos cómo está organizado el sistema. Podés omitir la guía cuando quieras y volver a verla desde el menú.",
  },
  {
    id: "menu",
    objetivo: "menu",
    menu: true,
    lado: ["derecha"],
    movil: {
      objetivo: "barra-inferior",
      lado: ["arriba"],
      texto: {
        A: "Abajo tenés las secciones de uso diario. Como administrador las ves todas y podés crear, editar y eliminar en cada una.",
        O: "Abajo tenés las secciones que más usás en tu trabajo diario.",
        C: "Abajo tenés las secciones de uso diario. Con tu rol podés ver toda la información, pero no modificarla.",
      },
    },
    titulo: "El menú",
    texto: {
      A: "Desde acá entrás a cada sección del sistema. Como administrador las ves todas y podés crear, editar y eliminar en cada una.",
      O: "Desde acá entrás a las secciones que usás en tu trabajo diario.",
      C: "Desde acá entrás a las secciones del sistema. Con tu rol podés ver toda la información, pero no modificarla.",
    },
  },
  {
    id: "mas",
    objetivo: "boton-mas",
    soloMovil: true,
    lado: ["arriba"],
    titulo: "Más secciones",
    texto: "Tocá «Más» para abrir el resto de las secciones del sistema. Las vas a ver agrupadas en Producción, Insumos y Gestión.",
  },
  {
    id: "produccion",
    objetivo: "menu-produccion",
    menu: true,
    lado: ["derecha"],
    movil: {
      objetivo: "hoja-produccion",
      hoja: "mas",
      texto: {
        A: "Acá están las Entradas de alimento, los Descartes y las Salidas. Galpones, Lotes y la Recolección diaria están en la barra de abajo.",
        O: "Cargás las Entradas, los Descartes y las Salidas. La Recolección diaria está en la barra de abajo.",
        C: "Consultás las Entradas, los Descartes y las Salidas. Galpones, Lotes y la Recolección diaria están en la barra de abajo.",
      },
    },
    titulo: "Producción",
    texto: {
      A: "Acá se maneja el día a día: Galpones y Lotes (dónde y con qué se produce) y lo que se carga cada día: Recolección, Entradas de alimento, Descartes y Salidas.",
      O: "Es tu lugar de trabajo. Cargás la Recolección diaria, las Entradas, los Descartes y las Salidas. Galpones y Lotes son solo para consultar.",
      C: "Acá consultás los Galpones, los Lotes y todo lo que se registra a diario: Recolección, Entradas, Descartes y Salidas.",
    },
  },
  {
    id: "insumos",
    objetivo: "menu-insumos",
    menu: true,
    lado: ["derecha"],
    movil: { objetivo: "hoja-insumos", hoja: "mas" },
    titulo: "Insumos",
    texto: {
      A: "Lo necesario para alimentar a las gallinas: Materias Primas, Compras y Proveedores.",
      O: "Podés consultar las Materias Primas disponibles. Es solo de lectura.",
      C: "Podés consultar las Materias Primas, las Compras y los Proveedores.",
    },
  },
  {
    id: "gestion",
    objetivo: "menu-gestion",
    menu: true,
    lado: ["derecha"],
    movil: { objetivo: "hoja-gestion", hoja: "mas" },
    roles: ["A", "C"],
    titulo: "Gestión",
    texto: {
      A: "El catálogo de Productos, los Informes para analizar la producción y los Usuarios que acceden al sistema.",
      C: "Consultá el catálogo de Productos y analizá la producción con los Informes.",
    },
  },
  {
    id: "perfil",
    objetivo: "boton-perfil",
    soloMovil: true,
    lado: ["abajo"],
    titulo: "Tu perfil",
    texto: "Tocá tu avatar, arriba a la izquierda, para ver tu cuenta, cambiar entre modo claro y oscuro, volver a ver este tutorial o cerrar sesión.",
  },
  {
    id: "panel",
    objetivo: "dash-titulo",
    ruta: "/app/dashboard",
    titulo: "Panel principal",
    texto: {
      A: "Es lo primero que ves al entrar: un resumen de toda la granja con los datos de hoy.",
      O: "Es lo primero que ves al entrar: un resumen con los datos de tus galpones asignados.",
      C: "Es lo primero que ves al entrar: un resumen de toda la granja con los datos de hoy.",
    },
  },
  {
    id: "accesos",
    objetivo: "dash-acciones",
    ruta: "/app/dashboard",
    roles: ["A", "O"],
    titulo: "Accesos rápidos",
    texto: {
      A: "Atajos para cargar una recolección, un descarte o una compra sin pasar por el menú.",
      O: "Atajos para cargar una recolección o un descarte sin pasar por el menú.",
    },
  },
  {
    id: "indicadores",
    objetivo: "dash-kpis",
    ruta: "/app/dashboard",
    titulo: "Indicadores del día",
    texto:
      "Huevos recolectados, postura promedio, galpones en producción y alertas activas. Tocá cualquier tarjeta para ir al detalle.",
  },
  {
    id: "produccion-semana",
    objetivo: "dash-produccion",
    ruta: "/app/dashboard",
    titulo: "Producción de la semana",
    texto: {
      A: "Los huevos recolectados cada día. El de hoy se marca en dorado. Tocá una barra para ir a los informes.",
      O: "Los huevos recolectados cada día. El de hoy se marca en dorado.",
      C: "Los huevos recolectados cada día. El de hoy se marca en dorado. Tocá una barra para ir a los informes.",
    },
  },
  {
    id: "alertas",
    objetivo: "dash-alertas",
    ruta: "/app/dashboard",
    titulo: "Alertas",
    texto:
      "Avisan cuando algo se sale de lo esperado en un lote. Tocá una para ver el lote y revisarlo.",
  },
  {
    id: "pendientes",
    objetivo: "dash-pendientes",
    ruta: "/app/dashboard",
    titulo: "Pendientes de finalizar",
    texto: {
      A: "Registros que ya cargaste pero todavía no impactan en el stock. Mientras estén pendientes el stock no los cuenta, así que acordate de finalizarlos.",
      O: "Registros que ya cargaste pero todavía no impactan en el stock. Mientras estén pendientes el stock no los cuenta, así que acordate de finalizarlos.",
      C: "Registros que ya fueron cargados pero todavía no impactan en el stock. Mientras estén pendientes, el stock no los cuenta.",
    },
  },
  {
    id: "stock",
    objetivo: "dash-stock",
    ruta: "/app/dashboard",
    titulo: "Stock actual",
    texto:
      "Cuántos huevos hay de cada producto y qué parte del total representa cada uno.",
  },
  {
    id: "repetir",
    objetivo: "btn-tutorial",
    menu: true,
    lado: ["derecha"],
    movil: {
      objetivo: "hoja-tutorial",
      hoja: "cuenta",
      texto: "Cuando quieras, este botón repite la guía. Acá también podés cambiar entre modo claro y oscuro.",
    },
    titulo: "¿Querés volver a verlo?",
    texto:
      "Cuando quieras, este botón repite la guía. Acá abajo también podés cambiar entre modo claro y oscuro.",
  },
];

/** Los pasos que corresponden a un rol, con el texto ya elegido para ese rol. */
export function pasosParaRol(rol) {
  const elegir = (t) => (typeof t === "string" ? t : t?.[rol] ?? "");
  return PASOS.filter((p) => !p.roles || p.roles.includes(rol)).map((p) => ({
    ...p,
    texto: elegir(p.texto),
    movil: p.movil && { ...p.movil, texto: p.movil.texto === undefined ? undefined : elegir(p.movil.texto) },
  }));
}

// "Ya lo vio" se guarda en el navegador, por usuario: si entra desde otro equipo, lo ve una vez más.
const clave = (usuario) => `avigest-tutorial-visto:${usuario?.id ?? "anon"}`;

export function tutorialVisto(usuario) {
  try {
    return localStorage.getItem(clave(usuario)) === "1";
  } catch {
    return true; // sin almacenamiento no se insiste con el tutorial
  }
}

export function marcarTutorialVisto(usuario) {
  try {
    localStorage.setItem(clave(usuario), "1");
  } catch {
    // Sin almacenamiento: se vuelve a mostrar la próxima vez, sin consecuencias.
  }
}
