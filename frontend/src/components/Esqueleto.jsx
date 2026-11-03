/**
 * Esqueletos de carga.
 *
 * Mientras llegan los datos, cada pantalla muestra su propia forma en gris y con
 * un brillo que la recorre (estilos .esqueleto en index.css) en lugar de un
 * cartel de «Cargando...». El encabezado y los filtros de la pantalla ya están
 * dibujados, así que el esqueleto solo reemplaza el contenido.
 *
 * Cada esqueleto copia la disposición de la pantalla real (lista + detalle,
 * tarjetas, tablero de lotes, informe) para que, al llegar los datos, nada
 * salte de lugar. Si una pantalla cambia su disposición, hay que ajustar acá
 * el esqueleto que le corresponde.
 */

/** Un bloque gris con el brillo que se desliza. */
export function Bloque({ ancho = "100%", alto = 14, radio, style }) {
  return (
    <div
      className="esqueleto"
      style={{ width: ancho, height: alto, borderRadius: radio, ...style }}
    ></div>
  );
}

/** Contenedor accesible: los lectores de pantalla oyen `texto` y no los bloques. */
function Envoltorio({ texto, className, children }) {
  return (
    <div className={className} role="status" aria-busy="true">
      <span className="sr-only">{texto}</span>
      {children}
    </div>
  );
}

/** Panel de detalle de la derecha (Recolecciones, Galpones, Lotes, etc.). */
function DetalleEsqueleto() {
  return (
    <div className="detail-panel esqueleto-detalle">
      <div className="esqueleto-detalle-cabecera">
        <div style={{ flex: 1 }}>
          <Bloque ancho="55%" alto={20} />
          <Bloque ancho="35%" alto={12} style={{ marginTop: 8 }} />
        </div>
        <Bloque ancho={74} alto={22} radio={20} />
      </div>
      <div className="esqueleto-detalle-cuerpo">
        {[0, 1, 2, 3, 4].map((i) => (
          <div className="esqueleto-detalle-fila" key={i}>
            <Bloque ancho="30%" alto={13} />
            <Bloque ancho="38%" alto={13} />
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Pantallas de lista: tabla a la izquierda y detalle a la derecha
 * (Recolecciones, Entradas, Descartes, Salidas y Compras).
 */
export function EsqueletoTabla({ texto = "Cargando...", filas = 9, columnas = 6 }) {
  return (
    <Envoltorio texto={texto} className="page-body-split">
      <div className="list-panel">
        <div className="table-wrap esqueleto-tabla">
          <div className="esqueleto-tabla-cabecera">
            {Array.from({ length: columnas }, (_, i) => (
              <Bloque key={i} ancho="60%" alto={11} />
            ))}
          </div>
          {Array.from({ length: filas }, (_, f) => (
            <div className="esqueleto-tabla-fila" key={f}>
              {Array.from({ length: columnas }, (_, c) => (
                <Bloque key={c} ancho={c === columnas - 1 ? 74 : `${60 + ((f + c) % 3) * 12}%`} alto={13} />
              ))}
            </div>
          ))}
        </div>
      </div>
      <DetalleEsqueleto />
    </Envoltorio>
  );
}

/**
 * Pantallas de tarjetas con detalle a la derecha (Galpones, Materias primas,
 * Proveedores, Usuarios y Productos). `productos` usa la grilla más angosta.
 */
export function EsqueletoTarjetas({ texto = "Cargando...", cantidad = 8, productos = false }) {
  return (
    <Envoltorio texto={texto} className="page-body-split">
      <div className="card-column">
        <div className={productos ? "producto-grid" : "card-grid"}>
          {Array.from({ length: cantidad }, (_, i) => (
            <div className="esqueleto-tarjeta" key={i}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                <Bloque ancho="55%" alto={16} />
                <Bloque ancho={52} alto={18} radio={20} />
              </div>
              <Bloque ancho="40%" alto={12} style={{ marginTop: 12 }} />
              <Bloque ancho="85%" alto={12} style={{ marginTop: 26 }} />
              <Bloque ancho="65%" alto={12} style={{ marginTop: 10 }} />
            </div>
          ))}
        </div>
      </div>
      <DetalleEsqueleto />
    </Envoltorio>
  );
}

/** Tablero de Lotes: tres columnas de tarjetas y el detalle a la derecha. */
export function EsqueletoTablero({ texto = "Cargando..." }) {
  const tarjetasPorColumna = [2, 3, 1];
  return (
    <Envoltorio texto={texto} className="page-body-split">
      <div className="kanban-cols">
        {tarjetasPorColumna.map((n, col) => (
          <div className="kanban-col" key={col}>
            <div className="kanban-col-head esqueleto-kanban-cabecera">
              <Bloque ancho="45%" alto={12} />
              <Bloque ancho={22} alto={16} radio={20} />
            </div>
            {Array.from({ length: n }, (_, i) => (
              <div className="esqueleto-tarjeta" key={i}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                  <Bloque ancho="50%" alto={16} />
                  <Bloque ancho={70} alto={18} radio={20} />
                </div>
                <Bloque ancho="35%" alto={12} style={{ marginTop: 10 }} />
                <Bloque ancho="60%" alto={12} style={{ marginTop: 18 }} />
                <Bloque ancho="75%" alto={12} style={{ marginTop: 10 }} />
              </div>
            ))}
          </div>
        ))}
      </div>
      <DetalleEsqueleto />
    </Envoltorio>
  );
}

/** Informes: tarjetas de resumen y una tabla de ancho completo. */
export function EsqueletoInforme({ texto = "Generando informe..." }) {
  return (
    <Envoltorio texto={texto}>
      <div className="card" style={{ marginBottom: 18 }}>
        <Bloque ancho={190} alto={18} />
        {[0, 1, 2, 3, 4].map((i) => (
          <div className="esqueleto-fila" key={i}>
            <Bloque ancho={80} alto={12} />
            <Bloque ancho={`${88 - i * 11}%`} alto={10} radio={6} />
          </div>
        ))}
      </div>
      <div className="table-wrap esqueleto-tabla">
        <div className="esqueleto-tabla-cabecera">
          {[0, 1, 2, 3, 4].map((i) => (
            <Bloque key={i} ancho="60%" alto={11} />
          ))}
        </div>
        {[0, 1, 2, 3, 4].map((f) => (
          <div className="esqueleto-tabla-fila" key={f}>
            {[0, 1, 2, 3, 4].map((c) => (
              <Bloque key={c} ancho={`${60 + ((f + c) % 3) * 12}%`} alto={13} />
            ))}
          </div>
        ))}
      </div>
    </Envoltorio>
  );
}
