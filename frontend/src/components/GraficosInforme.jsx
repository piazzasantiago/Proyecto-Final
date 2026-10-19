// Gráficos simples para los informes: barras horizontales y dona (sin librerías).

const COLORES = {
  verde: "var(--green-600)",
  dorado: "var(--gold-500)",
  rojo: "var(--red-500)",
  gris: "var(--gray-300)",
};

// Colores de la dona, en orden. Después de agotarse se repiten.
const PALETA_DONA = [
  COLORES.rojo, COLORES.dorado, COLORES.verde, "#6b8fb0", "#8c6bb0", "#d98c5f", "#5fa3a3", COLORES.gris,
];

const nf = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 1 });

export { COLORES };

/**
 * Barras horizontales. filas: [{ etiqueta, valor (número o null), texto, color }].
 * Una fila con valor null se muestra vacía con "—" (por ejemplo, un galpón sin datos).
 * `maximo` es el valor que ocupa el 100 % del ancho.
 */
export function BarrasHorizontales({ titulo, filas, maximo, nota }) {
  return (
    <div className="card">
      <div className="card-title">
        <h3>{titulo}</h3>
      </div>
      <div className="hbar-list">
        {filas.map((f) => {
          const ancho = f.valor === null || !maximo ? 0 : Math.min(100, (f.valor / maximo) * 100);
          return (
            <div className="hbar-row" key={f.etiqueta}>
              <span
                className="hbar-label"
                title={f.etiqueta}
                style={{ width: 110, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
              >
                {f.etiqueta}
              </span>
              <div className="hbar-track">
                <div className="hbar-fill" style={{ width: `${ancho}%`, background: f.color || COLORES.verde }}></div>
              </div>
              <span className="hbar-value" style={{ width: 64 }}>{f.valor === null ? "—" : f.texto}</span>
            </div>
          );
        })}
      </div>
      {nota && <div className="form-hint" style={{ marginTop: 14 }}>{nota}</div>}
    </div>
  );
}

/**
 * Dona. segmentos: [{ etiqueta, valor }]. `centro` = { numero, texto } va en el hueco.
 */
export function Dona({ titulo, segmentos, centro, nota }) {
  const total = segmentos.reduce((acc, s) => acc + s.valor, 0);
  let acumulado = 0;
  const tramos = segmentos.map((s, i) => {
    const desde = (acumulado / total) * 100;
    acumulado += s.valor;
    return { ...s, color: PALETA_DONA[i % PALETA_DONA.length], desde, hasta: (acumulado / total) * 100 };
  });
  const fondo = `conic-gradient(${tramos.map((t) => `${t.color} ${t.desde}% ${t.hasta}%`).join(", ")})`;

  return (
    <div className="card">
      <div className="card-title">
        <h3>{titulo}</h3>
      </div>
      <div className="donut-wrap">
        <div className="donut" style={{ background: fondo }} role="img" aria-label={titulo}>
          <div className="donut-center">
            <b>{centro.numero}</b>
            <span>{centro.texto}</span>
          </div>
        </div>
        <div className="donut-legend">
          {tramos.map((t) => (
            <div className="legend-item" key={t.etiqueta}>
              <span className="legend-dot" style={{ background: t.color }}></span>
              {t.etiqueta} <b>{nf.format((t.valor / total) * 100)}%</b>
            </div>
          ))}
        </div>
      </div>
      {nota && <div className="form-hint" style={{ marginTop: 14 }}>{nota}</div>}
    </div>
  );
}
