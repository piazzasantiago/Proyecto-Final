import { useLayoutEffect, useRef, useState } from "react";

// Gráfica de línea simple en SVG (sin librerías): la serie real y, opcionalmente,
// una línea constante con el valor objetivo que carga el usuario.

const W_MAX = 760;
const ANGOSTO = 500; // por debajo de este ancho (celular) el gráfico se acomoda al espacio, sin deslizar

const nf = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 2 });

function maximoRedondo(valor) {
  if (!valor || valor <= 0) return 10;
  const potencia = 10 ** Math.floor(Math.log10(valor));
  for (const paso of [1, 2, 2.5, 5, 10]) {
    if (paso * potencia >= valor) return paso * potencia;
  }
  return 10 * potencia;
}

function etiquetaFecha(iso) {
  const [, m, d] = iso.split("-");
  return `${d}/${m}`;
}

/**
 * El gráfico toma el ancho disponible: en celular se dibuja más angosto y con menos marcas, así que
 * nunca hace falta deslizar de costado.
 */
export default function GraficoIndicador(props) {
  const caja = useRef(null);
  const [ancho, setAncho] = useState(W_MAX);

  useLayoutEffect(() => {
    const el = caja.current;
    if (!el) return undefined;
    const medir = () => setAncho(Math.round(Math.min(W_MAX, Math.max(240, el.clientWidth))));
    medir();
    const observador = new ResizeObserver(medir);
    observador.observe(el);
    return () => observador.disconnect();
  }, []);

  return (
    <div ref={caja}>
      <Grafico {...props} W={ancho} />
    </div>
  );
}

function Grafico({ serie, objetivo, unidad, W }) {
  const angosto = W < ANGOSTO;
  const H = angosto ? 240 : 300;
  const M = angosto ? { izq: 40, der: 22, arriba: 14, abajo: 34 } : { izq: 56, der: 18, arriba: 16, abajo: 38 };
  const valores = serie.map((p) => p.valor).filter((v) => v !== null);
  const hayObjetivo = objetivo !== null && objetivo !== undefined && !Number.isNaN(objetivo);
  const maxDato = Math.max(0, ...valores, hayObjetivo ? objetivo : 0);
  const yMax = maximoRedondo(maxDato * 1.08);

  const ancho = W - M.izq - M.der;
  const alto = H - M.arriba - M.abajo;
  const x = (i) => M.izq + (serie.length <= 1 ? ancho / 2 : (i / (serie.length - 1)) * ancho);
  const y = (v) => M.arriba + alto - (v / yMax) * alto;

  // La línea se corta en los días sin dato (por ejemplo, sin recolección).
  let trazo = "";
  let abierto = false;
  serie.forEach((p, i) => {
    if (p.valor === null) {
      abierto = false;
      return;
    }
    trazo += `${abierto ? "L" : "M"}${x(i).toFixed(1)},${y(p.valor).toFixed(1)} `;
    abierto = true;
  });

  const marcasY = [0, 0.25, 0.5, 0.75, 1].map((f) => f * yMax);
  const paso = Math.max(1, Math.ceil(serie.length / (angosto ? 5 : 8)));

  if (valores.length === 0) {
    return (
      <div className="empty-state" style={{ padding: 32 }}>
        No hay datos del indicador en el período elegido.
      </div>
    );
  }

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label="Gráfica del indicador a lo largo del período"
      style={{ width: "100%", height: "auto", display: "block" }}
    >
      {marcasY.map((v) => (
        <g key={v}>
          <line x1={M.izq} x2={W - M.der} y1={y(v)} y2={y(v)} stroke="var(--linea-grafico)" strokeWidth="1" />
          <text x={M.izq - 8} y={y(v) + 4} textAnchor="end" fontSize="12" fill="var(--gray-500)">
            {nf.format(v)}
          </text>
        </g>
      ))}

      {serie.map((p, i) =>
        (i % paso === 0 && serie.length - 1 - i >= paso / 2) || i === serie.length - 1 ? (
          <text key={p.fecha} x={x(i)} y={H - 14} textAnchor="middle" fontSize="12" fill="var(--gray-500)">
            {etiquetaFecha(p.fecha)}
          </text>
        ) : null
      )}

      {hayObjetivo && (
        <g>
          <line
            x1={M.izq} x2={W - M.der} y1={y(objetivo)} y2={y(objetivo)}
            stroke="#c9962b" strokeWidth="2" strokeDasharray="7 5"
          />
          <text x={W - M.der} y={y(objetivo) - 6} textAnchor="end" fontSize="12" fontWeight="700" fill="var(--gold-texto)">
            Objetivo {nf.format(objetivo)}{unidad === "%" ? " %" : ""}
          </text>
        </g>
      )}

      <path d={trazo} fill="none" stroke="var(--serie-real)" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
      {serie.map((p, i) =>
        p.valor === null ? null : (
          <circle key={p.fecha} cx={x(i)} cy={y(p.valor)} r="3.5" fill="var(--serie-real)">
            <title>{`${etiquetaFecha(p.fecha)}: ${nf.format(p.valor)} ${unidad}`}</title>
          </circle>
        )
      )}
    </svg>
  );
}
