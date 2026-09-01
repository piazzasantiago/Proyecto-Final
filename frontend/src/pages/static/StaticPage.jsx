// Renderiza el HTML exacto de la pantalla aprobada en el mockup.
// Estas pantallas todavía no tienen backend/frontend real conectado:
// son solo visuales (ver README) hasta que se implemente cada módulo.
export default function StaticPage({ html }) {
  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}
