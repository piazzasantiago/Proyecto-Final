# Recolección diaria — documentación de la feature

**Rama:** `feature/gestion-recolecciones`
**Casos de uso cubiertos:** CU24 a CU32

---

## Casos de uso implementados

| ID | Nombre | Actor |
|---|---|---|
| CU24 | Registrar recolección diaria | Administrador, Operario |
| CU25 | Agregar líneas de recolección (producto + cantidad) | Administrador, Operario |
| CU26 | Editar recolección en estado Pendiente | Administrador, Operario |
| CU27 | Finalizar recolección | Administrador, Operario |
| CU28 | Eliminar recolección | Administrador |
| CU29 | Listar recolecciones (con filtros por galpón y estado) | Todos |
| CU30 | Ver detalle de una recolección | Todos |
| CU31 | Filtrar recolecciones por galpón | Todos |
| CU32 | Filtrar recolecciones por estado | Todos |

---

## Modelo de datos

### Estructura cabecera-líneas

La recolección sigue el patrón **cabecera + líneas** ya establecido en el
proyecto:

- **`Recoleccion`** (cabecera): una por día y por galpón. Registra el galpón,
  el lote activo en ese momento, la fecha y hora, el estado, el usuario que
  cargó la recolección y observaciones opcionales.
- **`LineaRecoleccion`** (líneas): una por cada tipo de producto recolectado.
  Registra el producto, la cantidad y el galpón (redundante con la cabecera,
  pero útil para consultas futuras por producto y galpón sin pasar por la
  cabecera).

### Campos de `Recoleccion`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_recoleccion` | PK | Identificador |
| `id_galpon` | FK → Galpon | Galpón donde se realizó la recolección |
| `id_lote` | FK → Lote | Lote activo al momento de crear la recolección (ver decisión de diseño) |
| `id_usuario` | FK → Usuario | Usuario que registró la recolección (ver decisión de diseño) |
| `fecha` | DateTimeField | Fecha y hora de la recolección |
| `estado` | CHAR(1) | `P` = Pendiente, `F` = Finalizada |
| `observaciones` | TextField | Texto libre, opcional |

### Campos de `LineaRecoleccion`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_linea_recoleccion` | PK | Identificador |
| `id_recoleccion` | FK → Recoleccion | Cabecera a la que pertenece |
| `id_producto` | FK → Producto | Producto recolectado |
| `id_galpon` | FK → Galpon | Galpón (propagado desde la cabecera al crear) |
| `cantidad` | PositiveIntegerField | Unidades recolectadas |

---

## Decisión de diseño: FK `id_lote` en `Recoleccion`

### Problema

Una recolección ocurre mientras un lote de gallinas está activo en un galpón.
Cuando ese lote finaliza (las gallinas se retiran o mueren), el galpón queda
vacío y luego puede recibir un nuevo lote. La pregunta es: ¿cómo saber, meses
después, a qué lote correspondía una recolección histórica?

### Opciones evaluadas

**Opción A — Sin FK, derivar el lote por fecha:**
No guardar `id_lote` en la recolección. Para saber a qué lote pertenece una
recolección histórica, buscar qué lote estaba activo en ese galpón en esa
fecha.

- ✅ No agrega campo al modelo.
- ❌ La consulta es compleja y frágil: depende de que las fechas de los lotes
  sean consistentes, y falla si hay solapamientos o datos incorrectos.
- ❌ Si se editan las fechas de un lote, el resultado de la consulta histórica
  cambia retroactivamente.

**Opción B — FK directa `id_lote` en `Recoleccion` (implementada):**
Al crear una recolección, la API detecta automáticamente el lote activo del
galpón (estado `T` o `P`) y lo guarda en `id_lote`. El campo queda fijo en la
recolección: si el lote cambia de estado más adelante, la recolección histórica
sigue apuntando al lote correcto.

- ✅ Consulta trivial: `recoleccion.id_lote` es directo.
- ✅ Datos históricos inmunes a cambios futuros del lote.
- ✅ Sin lote activo en el galpón → la API devuelve 400 antes de crear la
  recolección, lo que refuerza la integridad del negocio.
- ⚠️ Agrega un campo al modelo y una migración.
- ⚠️ `id_lote` es `nullable` para tolerar recolecciones históricas anteriores
  a esta migración, aunque en la práctica siempre se llena al crear.

### Decisión

Se implementó la **Opción B**. El campo `id_lote` se llena automáticamente en
`perform_create` del ViewSet, sin que el cliente tenga que enviarlo. Si el
galpón no tiene un lote activo (`T` o `P`), la API rechaza la creación con HTTP
400 y un mensaje descriptivo.

---

## Decisión de diseño: FK `id_usuario` en `Recoleccion`

### Problema

Cuando un operario o administrador carga una recolección, queda registrado quién
fue el responsable de esa carga. Este dato es necesario para trazabilidad y
auditoría operativa.

### Decisión

Se agregó el campo `id_usuario` (FK a `Usuario`) en `Recoleccion`. Al igual que
`id_lote`, se inyecta automáticamente en `perform_create` del ViewSet a partir
del usuario autenticado (`request.user`), sin que el cliente deba enviarlo.

El campo es `nullable` para mantener compatibilidad con recolecciones históricas
creadas antes de esta migración, donde `id_usuario` quedará en `NULL` y se
muestra como `—` en la interfaz.

La exposición en la API se hace mediante `UsuarioResumenSerializer` (campos
`id_usuario`, `nombre_completo`, `usuario`), anidado como campo de solo lectura
en `RecoleccionSerializer`. El campo `nombre_completo` es una propiedad del
modelo `Usuario` que concatena `nombre` y `apellido`.

En la interfaz, la columna **"Cargado por"** aparece tanto en la tabla de
recolecciones como en el panel de detalle, mostrando `nombre_completo` si está
disponible, o el nombre de usuario como fallback.

---

## Permisos por rol

| Operación | Administrador | Operario | Consulta |
|---|:---:|:---:|:---:|
| Listar / Ver detalle | ✅ | ✅ | ✅ |
| Crear recolección | ✅ | ✅ | ❌ |
| Editar recolección PENDIENTE | ✅ | ✅ | ❌ |
| Finalizar recolección | ✅ | ✅ | ❌ |
| Eliminar recolección | ✅ | ❌ | ❌ |

La combinación Administrador-o-Operario se implementa con la clase
`EsAdministradorOOperario` en `usuarios/permissions.py`, en lugar de usar el
operador `|` entre instancias de `BasePermission`, que no está disponible en
la versión de DRF instalada.

---

## Validaciones del backend

- **Sin lote activo:** si el galpón no tiene un lote en estado `T` o `P`, la
  creación devuelve HTTP 400.
- **Sin líneas:** una recolección debe tener al menos una línea; sin líneas
  devuelve HTTP 400.
- **Producto duplicado:** no se puede repetir el mismo producto en dos líneas
  de la misma recolección; devuelve HTTP 400.
- **Producto inactivo:** al crear, o al agregar un producto nuevo a una
  recolección existente, solo se aceptan productos con `estado = A`; devuelve
  HTTP 400. Una recolección que se edita **conserva** los productos que ya tenía
  aunque se hayan desactivado después (desactivar un producto no afecta lo ya
  registrado). El formulario los muestra marcados como "(inactivo)".
- **Una recolección por día y galpón:** un galpón no puede tener dos
  recolecciones en el mismo día (se cuenta el día en horario local, sin importar
  la hora ni el estado). Al crear o al cambiar la fecha de una recolección, si
  ese día ya está ocupado devuelve HTTP 400. La regla se valida en el serializer;
  no hay un constraint en la base, así que dos pedidos simultáneos podrían
  colarse (poco probable con el uso previsto).
- **Edición de recolección finalizada:** intentar editar una recolección en
  estado `F` devuelve HTTP 400.
- **Finalizar recolección ya finalizada:** devuelve HTTP 400.
- **Cantidad entre 1 y 1.000.000:** cada línea debe tener `cantidad >= 1` y no
  superar 1.000.000; un valor cero, negativo o por encima del tope devuelve
  HTTP 400.
- **Fecha y hora no futura:** `fecha` no puede ser posterior al momento actual,
  al crear ni al editar; devuelve HTTP 400. El formulario también limita el
  campo al momento actual y muestra el aviso en español.
- **Observaciones:** máximo 500 caracteres; más devuelve HTTP 400. El formulario
  limita el campo y muestra un contador.
- **Galpón inmutable:** una vez creada la recolección no se puede cambiar el
  galpón (HTTP 400). Reenviar el mismo galpón es válido.

### Impacto en el stock de Productos

El stock de cada producto (ver `docs-productos.md`) suma lo recolectado en
recolecciones **finalizadas**: al pasar una recolección a Finalizada, la cantidad
de cada una de sus líneas se incorpora al `stock_actual` del producto. Las
pendientes no suman. No se guarda nada al finalizar: el stock se calcula en cada
consulta, de modo que borrar una recolección finalizada (solo el Administrador)
lo baja automáticamente.

### Lote en Transición

Se puede registrar una recolección con el lote del galpón en **Transición** (`T`)
o en **Producción** (`P`). Es una decisión deliberada: según la Educción de
requisitos, en la etapa de transición las gallinas "no son productivas, aunque
eventualmente pueden dejar huevos pequeños", y esos huevos se registran como
cualquier otro. No se bloquea ni se muestra aviso.

---

## Endpoints

| Método | Ruta | Descripción | Rol |
|---|---|---|---|
| GET | `/api/recolecciones/` | Listar (`?id_galpon=`, `?estado=`) | autenticado |
| POST | `/api/recolecciones/` | Crear con líneas | Adm. / Operario |
| GET | `/api/recolecciones/{id}/` | Detalle | autenticado |
| PUT/PATCH | `/api/recolecciones/{id}/` | Editar (solo PENDIENTE) | Adm. / Operario |
| DELETE | `/api/recolecciones/{id}/` | Eliminar | Administrador |
| POST | `/api/recolecciones/{id}/finalizar/` | Finalizar | Adm. / Operario |

### Ejemplo de payload para crear

```json
{
  "id_galpon_id": 1,
  "fecha": "2026-06-15T08:00:00",
  "observaciones": "Recolección matutina sin novedades.",
  "lineas": [
    { "id_producto_id": 1, "cantidad": 320 },
    { "id_producto_id": 2, "cantidad": 15 }
  ]
}
```

Los campos `id_lote` e `id_usuario` no se envían: la API los detecta e inyecta
automáticamente.

### Ejemplo de respuesta

```json
{
  "id_recoleccion": 7,
  "galpon": { "id_galpon": 1, "galpon": "Galpón Norte" },
  "lote": { "id_lote": 3, "codigo": "L-2026-003" },
  "usuario": {
    "id_usuario": 2,
    "nombre_completo": "Juan Pérez",
    "usuario": "jperez"
  },
  "fecha": "2026-06-15T08:00:00Z",
  "estado": "P",
  "estado_display": "Pendiente",
  "observaciones": "Recolección matutina sin novedades.",
  "lineas": [
    {
      "id_linea_recoleccion": 12,
      "producto": { "id_producto": 1, "producto": "Huevo grande" },
      "cantidad": 320
    },
    {
      "id_linea_recoleccion": 13,
      "producto": { "id_producto": 2, "producto": "Huevo roto" },
      "cantidad": 15
    }
  ]
}
```

---

## Tests

Se implementaron **74 tests** en `backend/recolecciones/tests.py`, organizados
en 13 clases:

| Clase | Tests | Qué verifica |
|---|:---:|---|
| `BuscarRecoleccionTests` | 5 | Listar, filtrar por galpón y estado, ver detalle con líneas y lote |
| `CrearRecoleccionTests` | 9 | Creación exitosa, estado inicial, lote asignado automáticamente, validaciones (sin líneas, producto duplicado, producto inactivo, galpón sin lote activo) |
| `EditarRecoleccionTests` | 6 | Editar observaciones, reemplazar líneas, bloqueo de recolección finalizada, imposibilidad de editar el estado vía PATCH, producto duplicado en edición |
| `BorrarRecoleccionTests` | 4 | Borrado exitoso, cascade a líneas, borrado de finalizada (permitido para Admin), 404 en inexistente |
| `FinalizarRecoleccionTests` | 5 | Finalizar exitoso, persistencia en base, idempotencia (ya finalizada → 400), 404 en inexistente, respuesta incluye lote |
| `PermisosRecoleccionTests` | 10 | Matriz completa: Admin puede crear/listar/eliminar; Operario puede crear/listar pero no eliminar; Consulta solo lista; sin token → 401 |
| `LoteFKTests` | 3 | FK guardada al crear, FK no cambia cuando el lote del galpón cambia, galpón sin lote activo devuelve 400 |
| `ValidacionesCantidadYGalponTests` | 8 | Cantidad negativa o cero → 400, cantidad 1 y 1.000.000 válidas, sobre el tope o enorme → 400 (no 500), no se puede cambiar el galpón al editar, reenviar el mismo galpón es válido |
| `FechaRecoleccionTests` | 4 | Fecha de mañana o hora futura del mismo día → 400, fecha pasada válida, no se puede editar la fecha a una futura |
| `ObservacionesRecoleccionTests` | 3 | 500 caracteres es válido, 501 → 400, no se puede editar a más de 500 |
| `UnaRecoleccionPorDiaTests` | 7 | Segunda recolección del mismo día y galpón → 400, otro galpón u otro día válidos, la finalizada también cuenta, medianoche (días distintos), editar dentro del mismo día, mover la fecha a un día ocupado → 400 |
| `ProductoDesactivadoTests` | 4 | Conservar un producto desactivado al editar, sumar uno activo, no agregar uno inactivo nuevo, no crear con inactivo |
| `StockDeProductosTests` | 6 | El stock de Productos: sin recolecciones es el inicial, las pendientes no suman, las finalizadas sí, finalizar por la API lo sube, suma varias y separa por producto, borrar una finalizada lo baja |

Ejecutar:

```bash
python manage.py test recolecciones --verbosity=2
```

---

## Archivos modificados o creados

### Backend

| Archivo | Cambio |
|---|---|
| `recolecciones/models.py` | Nuevo: modelos `Recoleccion` y `LineaRecoleccion`; agrega FK `id_usuario` |
| `recolecciones/migrations/0001_initial.py` | Migración inicial |
| `recolecciones/migrations/0002_recoleccion_id_lote.py` | Agrega FK `id_lote` |
| `recolecciones/migrations/0003_recoleccion_id_usuario.py` | Agrega FK `id_usuario` |
| `recolecciones/serializers.py` | Nuevo: serializers cabecera-líneas con `LoteResumenSerializer` y `UsuarioResumenSerializer` |
| `recolecciones/views.py` | Nuevo: `RecoleccionViewSet` con `perform_create` (inyecta `id_lote` e `id_usuario`) y acción `/finalizar/` |
| `recolecciones/urls.py` | Nuevo: router DRF |
| `recolecciones/tests.py` | Nuevo: 74 tests |
| `usuarios/models.py` | Agrega propiedad `es_operario` al modelo `Usuario` |
| `usuarios/migrations/0002_alter_usuario_options.py` | Sincroniza opciones de Meta (`verbose_name`, `verbose_name_plural`) |
| `usuarios/permissions.py` | Agrega clases `EsOperario` y `EsAdministradorOOperario` |
| `config/urls.py` | Registra el router de recolecciones |

### Frontend

| Archivo | Cambio |
|---|---|
| `src/api/recolecciones.js` | Nuevo: `listRecolecciones`, `createRecoleccion`, `updateRecoleccion`, `deleteRecoleccion`, `finalizarRecoleccion` |
| `src/pages/RecoleccionesPage.jsx` | Nuevo: pantalla principal con tabla, panel de detalle y filtros; incluye columna y fila de detalle "Cargado por" |
| `src/components/RecoleccionFormModal.jsx` | Nuevo: modal de alta y edición con gestión dinámica de líneas |
