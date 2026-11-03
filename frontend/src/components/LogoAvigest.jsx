import { useEffect, useRef } from "react";

/*
  Logo del login (nombre: "AviGest", sin tilde): huevo dorado (solo el contorno) detrás del nombre.
  - El nombre va como trazado vectorial de Poppins Medium: se ve igual en cualquier equipo y no
    depende de cargar una tipografía. Si se cambia el texto hay que volver a generar el trazado.
  - El 3D sale de la perspectiva al inclinarse y de un degradé sutil en el aro.
  - Se inclina hacia el cursor con un resorte (amortiguación 1.0: sin rebote).
  - Al presionar se hunde al instante; al soltar, da una vuelta completa (resorte con rebote leve,
    porque el gesto trae impulso). Cada movimiento parte del valor actual, así que se puede
    interrumpir en cualquier momento sin saltos.
  - Con "reducir movimiento" queda quieto.
*/

// Resorte "à la Apple": respuesta (s) y amortiguación -> rigidez y fricción.
function paso(est, objetivo, respuesta, amort, dt) {
  const w = (2 * Math.PI) / respuesta;
  const acel = w * w * (objetivo - est.x) - 2 * amort * w * est.v;
  est.v += acel * dt;
  est.x += est.v * dt;
}

const AJUSTES = {
  inclinar: { respuesta: 0.4, amort: 1.0 },
  presion: { respuesta: 0.18, amort: 1.0 },
  giro: { respuesta: 0.7, amort: 0.7 },
};

export default function LogoAvigest({ compacto = false }) {
  const botonRef = useRef(null);
  const sombraRef = useRef(null);
  const estado = useRef({
    rx: { x: 0, v: 0 }, ry: { x: 0, v: 0 }, giro: { x: 0, v: 0 }, esc: { x: 1, v: 0 },
    objRx: 0, objRy: 0, objGiro: 0, objEsc: 1,
    raf: 0, ultimo: 0,
  });

  useEffect(() => {
    const reducido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const e = estado.current;
    const boton = botonRef.current;
    const sombra = sombraRef.current;
    if (compacto || !boton || reducido) return undefined;

    const dibujar = () => {
      boton.style.transform =
        `perspective(500px) rotateX(${e.rx.x}deg) rotateY(${e.ry.x + e.giro.x}deg) scale(${e.esc.x})`;
      // La sombra se estira un poco cuando el huevo se inclina.
      sombra.style.transform = `translateX(${e.ry.x * 0.25}px) scaleX(${1 + Math.abs(e.ry.x) / 120}) scale(${e.esc.x})`;
      sombra.style.opacity = String(0.9 - Math.abs(e.rx.x) / 80);
    };

    const tick = (t) => {
      const dt = Math.min((t - e.ultimo) / 1000 || 0.016, 0.032);
      e.ultimo = t;
      paso(e.rx, e.objRx, AJUSTES.inclinar.respuesta, AJUSTES.inclinar.amort, dt);
      paso(e.ry, e.objRy, AJUSTES.inclinar.respuesta, AJUSTES.inclinar.amort, dt);
      paso(e.esc, e.objEsc, AJUSTES.presion.respuesta, AJUSTES.presion.amort, dt);
      paso(e.giro, e.objGiro, AJUSTES.giro.respuesta, AJUSTES.giro.amort, dt);
      dibujar();
      const quieto = [e.rx, e.ry, e.esc, e.giro].every((s) => Math.abs(s.v) < 0.01)
        && Math.abs(e.rx.x - e.objRx) < 0.01 && Math.abs(e.ry.x - e.objRy) < 0.01
        && Math.abs(e.esc.x - e.objEsc) < 0.0005 && Math.abs(e.giro.x - e.objGiro) < 0.05;
      e.raf = quieto ? 0 : requestAnimationFrame(tick);
    };
    const despertar = () => {
      if (!e.raf) { e.ultimo = performance.now(); e.raf = requestAnimationFrame(tick); }
    };

    // Inclinación hacia el cursor: se mide contra el centro del huevo, en toda la ventana.
    const mover = (ev) => {
      const r = boton.getBoundingClientRect();
      const dx = (ev.clientX - (r.left + r.width / 2)) / Math.max(window.innerWidth / 2, 1);
      const dy = (ev.clientY - (r.top + r.height / 2)) / Math.max(window.innerHeight / 2, 1);
      e.objRy = Math.max(-1, Math.min(1, dx)) * 22;
      e.objRx = Math.max(-1, Math.min(1, dy)) * -16;
      despertar();
    };
    const abajo = () => { e.objEsc = 0.94; despertar(); };
    const arriba = () => { e.objEsc = 1; despertar(); };
    const click = () => { e.objGiro += 360; despertar(); };   // parte del valor actual: interrumpible
    const salir = () => { e.objRx = 0; e.objRy = 0; e.objEsc = 1; despertar(); };

    window.addEventListener("pointermove", mover, { passive: true });
    document.addEventListener("pointerleave", salir);
    boton.addEventListener("pointerdown", abajo);
    window.addEventListener("pointerup", arriba);
    boton.addEventListener("click", click);
    return () => {
      cancelAnimationFrame(e.raf);
      e.raf = 0;
      window.removeEventListener("pointermove", mover);
      document.removeEventListener("pointerleave", salir);
      boton.removeEventListener("pointerdown", abajo);
      window.removeEventListener("pointerup", arriba);
      boton.removeEventListener("click", click);
    };
  }, [compacto]);

  const Contenedor = compacto ? "div" : "button";

  return (
    <div className={`logo-marca${compacto ? " compacto" : ""}`}>
      <div className="logo-huevo-pos">
        <span className="logo-sombra" ref={sombraRef} aria-hidden="true" />
        <Contenedor
          className="logo-huevo"
          ref={botonRef}
          {...(compacto ? { "aria-hidden": "true" } : { type: "button", "aria-label": "Huevo de AviGest" })}
        >
          <svg viewBox="0 0 100 124" aria-hidden="true" focusable="false">
            <defs>
              <linearGradient id="lg-aro" x1="12%" y1="0%" x2="88%" y2="100%">
                <stop offset="0" stopColor="#F7D982" />
                <stop offset="0.45" stopColor="#E2B340" />
                <stop offset="1" stopColor="#B98320" />
              </linearGradient>
            </defs>
            <path
              d="M50 6 C70 6 88 46 88 78 C88 102 71 118 50 118 C29 118 12 102 12 78 C12 46 30 6 50 6 Z"
              fill="none" stroke="url(#lg-aro)" strokeWidth="11" strokeLinejoin="round"
            />
          </svg>
        </Contenedor>
      </div>
      <svg className="logo-nombre" viewBox="0 -800 3693 850" role="img" aria-label="AviGest">
        <path fill="currentColor" d="M494 -142H203L153 0H34L283 -696H415L664 0H544ZM462 -235 349 -558 235 -235Z M965.0 -102 1121.0 -551H1242.0L1032.0 0H896.0L687.0 -551H809.0Z M1293.0 -697Q1293.0 -728 1314.0 -749.0Q1335.0 -770 1366.0 -770Q1396.0 -770 1417.0 -749.0Q1438.0 -728 1438.0 -697Q1438.0 -666 1417.0 -645.0Q1396.0 -624 1366.0 -624Q1335.0 -624 1314.0 -645.0Q1293.0 -666 1293.0 -697ZM1422.0 -551V0H1308.0V-551Z M2055.0 -495Q2028.0 -547 1980.0 -573.5Q1932.0 -600 1869.0 -600Q1800.0 -600 1746.0 -569.0Q1692.0 -538 1661.5 -481.0Q1631.0 -424 1631.0 -349Q1631.0 -274 1661.5 -216.5Q1692.0 -159 1746.0 -128.0Q1800.0 -97 1869.0 -97Q1962.0 -97 2020.0 -149.0Q2078.0 -201 2091.0 -290H1830.0V-381H2213.0V-292Q2202.0 -211 2155.5 -143.0Q2109.0 -75 2034.5 -34.5Q1960.0 6 1869.0 6Q1771.0 6 1690.0 -39.5Q1609.0 -85 1561.5 -166.0Q1514.0 -247 1514.0 -349Q1514.0 -451 1561.5 -532.0Q1609.0 -613 1690.5 -658.5Q1772.0 -704 1869.0 -704Q1980.0 -704 2066.5 -649.5Q2153.0 -595 2192.0 -495Z M2806.0 -233H2385.0Q2390.0 -167 2434.0 -127.0Q2478.0 -87 2542.0 -87Q2634.0 -87 2672.0 -164H2795.0Q2770.0 -88 2704.5 -39.5Q2639.0 9 2542.0 9Q2463.0 9 2400.5 -26.5Q2338.0 -62 2302.5 -126.5Q2267.0 -191 2267.0 -276Q2267.0 -361 2301.5 -425.5Q2336.0 -490 2398.5 -525.0Q2461.0 -560 2542.0 -560Q2620.0 -560 2681.0 -526.0Q2742.0 -492 2776.0 -430.5Q2810.0 -369 2810.0 -289Q2810.0 -258 2806.0 -233ZM2691.0 -325Q2690.0 -388 2646.0 -426.0Q2602.0 -464 2537.0 -464Q2478.0 -464 2436.0 -426.5Q2394.0 -389 2386.0 -325Z M2872.0 -169H2990.0Q2993.0 -134 3023.5 -110.5Q3054.0 -87 3100.0 -87Q3148.0 -87 3174.5 -105.5Q3201.0 -124 3201.0 -153Q3201.0 -184 3171.5 -199.0Q3142.0 -214 3078.0 -232Q3016.0 -249 2977.0 -265.0Q2938.0 -281 2909.5 -314.0Q2881.0 -347 2881.0 -401Q2881.0 -445 2907.0 -481.5Q2933.0 -518 2981.5 -539.0Q3030.0 -560 3093.0 -560Q3187.0 -560 3244.5 -512.5Q3302.0 -465 3306.0 -383H3192.0Q3189.0 -420 3162.0 -442.0Q3135.0 -464 3089.0 -464Q3044.0 -464 3020.0 -447.0Q2996.0 -430 2996.0 -402Q2996.0 -380 3012.0 -365.0Q3028.0 -350 3051.0 -341.5Q3074.0 -333 3119.0 -320Q3179.0 -304 3217.5 -287.5Q3256.0 -271 3284.0 -239.0Q3312.0 -207 3313.0 -154Q3313.0 -107 3287.0 -70.0Q3261.0 -33 3213.5 -12.0Q3166.0 9 3102.0 9Q3037.0 9 2985.5 -14.5Q2934.0 -38 2904.0 -78.5Q2874.0 -119 2872.0 -169Z M3549.0 -458V-153Q3549.0 -122 3563.5 -108.5Q3578.0 -95 3613.0 -95H3683.0V0H3593.0Q3516.0 0 3475.0 -36.0Q3434.0 -72 3434.0 -153V-458H3369.0V-551H3434.0V-688H3549.0V-551H3683.0V-458Z" />
      </svg>
    </div>
  );
}
