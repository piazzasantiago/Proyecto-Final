# Auditoría de los registros (F-23)

Registra **quién** y **cuándo** creó, editó y finalizó cada registro, y lo muestra
en el panel de detalle con un botón «ojito».

## Qué se guarda

La clase base abstracta `ModeloAuditable` (`backend/config/auditoria.py`) agrega
seis campos a los modelos principales:

| Campo | Se completa cuando |
|---|---|
| `creado_por`, `fecha_creacion` | se crea el registro |
| `editado_por`, `fecha_editado` | se modifica (incluye activar/desactivar y dar de alta/baja) |
| `finalizado_por`, `fecha_finalizado` | el estado pasa a **Finalizado** (`F`) |

La heredan los 11 modelos: Compra, Descarte, Entrada, Salida, Recolección, Lote,
Galpón, Materia prima, Producto, Proveedor y Usuario. Solo los seis primeros
tienen el concepto de finalizar (`ESTADOS_FINALIZADO = ("F",)`); en el resto los
campos de finalización quedan siempre vacíos.

Los campos se completan solos en `save()`, tomando al usuario de la petición en
curso (`AuditoriaMixin`, que usan todos los ViewSets). Las vistas no tienen que
pasarlo, y las acciones propias (`finalizar`, `baja`, `vaciar`, `activar`...) quedan
auditadas sin código extra.

Reglas:

- Si el estado pasa a finalizado, se registra la **finalización** y no la edición.
- Editar un registro ya finalizado no pisa los datos de finalización.
- Un cambio que no viene de una persona (por ejemplo, la transición automática de un
  lote a Producción) guarda la fecha sin usuario y se muestra como «Sistema».
- Iniciar sesión (actualiza `last_login`) no cuenta como edición.
- Los registros anteriores a esta función no tienen fechas: se muestran como
  «Sin registro». En Compras, Descartes, Entradas, Salidas y Recolecciones la
  migración copia el `id_usuario` que ya tenían a `creado_por`.
- Los borrados no dejan rastro (el registro ya no existe); la auditoría cubre
  alta, edición y finalización.

## Qué ve cada rol

La API agrega el campo `auditoria` a cada registro **solo** para Administrador y
Consulta. El Operario no lo recibe y no ve el botón.

```json
"auditoria": {
  "creado":     { "fecha": "2026-10-28T21:30:00Z", "por": { "nombre": "Ana Pérez", "usuario": "aperez" } },
  "editado":    { "fecha": null, "por": null },
  "finalizado": { "fecha": null, "por": null }
}
```

## Pantalla

Un ícono de ojo (`AuditoriaBoton`) muestra el historial de dos maneras: al **pasar el cursor** (o enfocarlo con el teclado) aparece una tarjeta chica, y al **hacer clic** se abre la ventana **Historial** (también sirve en pantallas táctiles). Ambas tienen **Creado**, **Última edición** y,
en los módulos que se finalizan, **Finalizado**, con el nombre, el usuario y la fecha y hora.

- **Compras, Descartes, Entradas, Salidas y Recolecciones** (listados en tabla): el ojito
  está al final de cada fila. La columna «Cargado por» se ve en pantallas de 1700 px o más
  y se oculta en las angostas cuando la persona ve la auditoría; el Operario, que no ve el
  ojito, la conserva siempre. El dato sigue en el panel de detalle.
- **Galpones, Lotes, Materias primas, Productos, Proveedores y Usuarios** (tarjetas): el ojito
  está en el panel de detalle, junto al estado.

## Rendimiento

`AuditoriaMixin` trae los tres usuarios con `select_related`, así que listar
registros no hace una consulta extra por fila.

## Tests

`backend/config/tests_auditoria.py` (20 tests): alta, edición, baja, finalización,
registros anteriores, cambios sin usuario, login, visibilidad por rol, consultas por
listado y que el usuario de una petición no se arrastre a la siguiente.
