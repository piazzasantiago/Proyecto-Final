// Renderiza el HTML exacto de la pantalla aprobada en el mockup.
// Hoy lo usa solo el Dashboard (src/pages/static/raw/dashboard.html), que todavía
// no tiene backend/frontend real conectado: es solo visual (ver README) hasta que
// se implemente. Todos los demás módulos ya tienen su pantalla real.
export default function StaticPage({ html }) {
  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}
