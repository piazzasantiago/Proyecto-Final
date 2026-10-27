import { useEffect, useState } from "react";
import { listCompras } from "../api/compras";
import CompraFormModal from "./CompraFormModal";

/** Cuántas compras se muestran en el detalle. */
const CANTIDAD = 4;

function formatFecha(iso) {
  if (!iso) return "—";
  const [y, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${y}`;
}

function formatNumero(valor) {
  const n = Number(valor);
  return Number.isNaN(n) ? "—" : n.toLocaleString("es-AR", { maximumFractionDigits: 2 });
}

function formatPrecio(valor) {
  const n = Number(valor);
  return Number.isNaN(n)
    ? "—"
    : n.toLocaleString("es-AR", { style: "currency", currency: "ARS", minimumFractionDigits: 2 });
}

/**
 * Sección "Compras recientes" de los paneles de detalle.
 *
 * Muestra las últimas compras (la más nueva primero) de un proveedor
 * (`proveedorId`) o que incluyen una materia prima (`materiaPrimaId`). Se usa
 * en Proveedores (F-11) y en Materias primas (F-12).
 *
 * En el detalle de una materia prima se destaca lo que interesa de ESA
 * materia prima (cantidad comprada y proveedor); en el del proveedor, la
 * categoría y el total de la compra.
 */
export default function ComprasRecientes({ proveedorId, materiaPrimaId, unidad }) {
  const [compras, setCompras] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  // Compra abierta en la ventana de detalle (solo lectura).
  const [abierta, setAbierta] = useState(null);

  useEffect(() => {
    let vigente = true; // evita pisar el resultado si cambió la selección mientras cargaba
    setLoading(true);
    setError(false);
    const params = { page_size: CANTIDAD };
    if (proveedorId) params.id_proveedor = proveedorId;
    if (materiaPrimaId) params.id_materia_prima = materiaPrimaId;
    listCompras(params)
      .then((data) => {
        if (!vigente) return;
        const lista = data.results ?? data;
        setCompras(lista.slice(0, CANTIDAD));
        setTotal(data.count ?? lista.length);
      })
      .catch(() => vigente && setError(true))
      .finally(() => vigente && setLoading(false));
    return () => {
      vigente = false;
    };
  }, [proveedorId, materiaPrimaId]);

  if (loading) {
    return <div className="compras-rec-vacio">Cargando compras...</div>;
  }
  if (error) {
    return <div className="compras-rec-vacio">No se pudieron cargar las compras.</div>;
  }
  if (compras.length === 0) {
    return <div className="compras-rec-vacio">Todavía no hay compras registradas.</div>;
  }

  return (
    <div className="compras-rec">
      {compras.map((c) => {
        const pendiente = c.estado === "P";
        // Cantidad de ESTA materia prima en la compra (puede tener más de una línea).
        const cantidadMp = materiaPrimaId
          ? c.lineas
              .filter((l) => l.id_materia_prima === materiaPrimaId)
              .reduce((suma, l) => suma + Number(l.cantidad), 0)
          : null;
        return (
          <div
            className="compra-rec"
            key={c.id_compra}
            role="button"
            tabIndex={0}
            title="Ver el detalle de la compra"
            onClick={() => setAbierta(c)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                setAbierta(c);
              }
            }}
          >
            <div className="compra-rec-top">
              <span className="compra-rec-nro">N° {c.nro_comprobante}</span>
              <span className={`badge ${pendiente ? "badge-gold" : "badge-green"}`}>
                {c.estado_display}
              </span>
            </div>
            <div className="compra-rec-linea">
              <span>{formatFecha(c.fecha)}</span>
              <span>
                {materiaPrimaId
                  ? `${formatNumero(cantidadMp)} ${unidad ?? ""}`.trim()
                  : formatPrecio(c.total)}
              </span>
            </div>
            <div className="compra-rec-linea compra-rec-sec">
              <span>{materiaPrimaId ? c.proveedor?.nombre : c.categoria_display}</span>
              {materiaPrimaId && <span>{formatPrecio(c.total)}</span>}
            </div>
          </div>
        );
      })}
      {total > compras.length && (
        <div className="compras-rec-mas">
          Mostrando las últimas {compras.length} de {total} compras.
        </div>
      )}
      {abierta && (
        <CompraFormModal initialData={abierta} soloLectura onClose={() => setAbierta(null)} />
      )}
    </div>
  );
}
