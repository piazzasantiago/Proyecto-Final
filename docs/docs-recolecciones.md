# Recolección diaria — documentación de la feature

**Rama:** `feature/gestion-recolecciones`
**Casos de uso cubiertos:** CU24 a CU32

---

## Casos de uso implementados

Numeración y nombres según la *Educción de requisitos*. Los CU24 a CU28
corresponden a la cabecera (la recolección) y los CU29 a CU32 a sus líneas
(producto + cantidad). Las líneas no tienen endpoints propios: se leen y se
modifican siempre a través de la recolección a la que pertenecen (ver cada CU).

### Recolecciones

#### CU24 – Buscar Avanzado Recolecciones

**Actor:** cualquier usuario autenticado (Administrador, Operario y Consulta).

Lista las recolecciones con sus líneas, lote, galpón y usuario que las cargó.
Permite filtrar por galpón (`?id_galpon=`), lote (`?id_lote=`), estado
(`?estado=P|F`) y rango de fechas (`?fecha_desde=AAAA-MM-DD` y
`?fecha_hasta=AAAA-MM-DD`); los filtros se pueden combinar. Las fechas son
inclusivas y se comparan por día, de modo que una recolección de las 23:00 entra
con `fecha_hasta` de ese mismo día. Una fecha con formato inválido, una
`fecha_desde` posterior a `fecha_hasta`, o un `id_galpon` / `id_lote` que no sea un
número entero válido, devuelve 400. El detalle de una
recolección se obtiene con `GET /api/recolecciones/{id}/`.

El listado está **paginado de a 16 registros** (`?page=N`). Se puede pedir otro
tamaño con `?page_size=N` (máximo 100). La respuesta trae `count`, `next`,
`previous` y `results`; los filtros se aplican antes de paginar.

En la pantalla, la barra de paginación permite elegir los **elementos por página**
(10, 16, 25 o 50; 16 por defecto). La elección se recuerda en el navegador.
Entre "Anterior" y "Siguiente" se muestran los **números de página**, que se
pueden tocar para ir directo a esa página. La cantidad de páginas se calcula con
los elementos elegidos, y cuando son muchas se muestran la primera, la última y las
cercanas a la actual, con "…" en los tramos omitidos (por ejemplo
`1 … 7 8 9 10 11 … 20`). Al cambiar los elementos por página se vuelve a la página 1. La barra se muestra
siempre que haya registros, incluso con una sola página (el número 1 activo y
Anterior / Siguiente deshabilitados).

#### CU25 – Nueva Recolección

**Actor:** Administrador, Operario.

Registra la recolección de un galpón con su fecha y hora, observaciones
opcionales y al menos una línea. El sistema completa solo el lote activo del
galpón (`id_lote`) y el usuario que la carga (`id_usuario`), y la crea en estado
**Pendiente**. Se rechaza con 400 si:

- el galpón no tiene un lote activo (Transición o Producción);
- el galpón ya tiene otra recolección ese día;
- la fecha es futura;
- no hay líneas, o hay un producto repetido o inactivo;
- las observaciones superan los 500 caracteres.

#### CU26 – Modificar Recolección

**Actor:** Administrador, Operario.

Modifica la fecha, las observaciones y/o las líneas de una recolección
**Pendiente**. Una recolección Finalizada no se puede modificar
(*"Recolección finalizada. No se puede editar."*). El galpón no se puede
cambiar una vez creada la recolección, y el estado solo cambia con CU28. Si la
fecha se mueve a un día en que el galpón ya tiene otra recolección, devuelve 400.
Las validaciones de fecha, observaciones y líneas son las mismas que en CU25.

#### CU27 – Borrar Recolección

**Actor:** Administrador.

Elimina físicamente la recolección y, en cascada, todas sus líneas. **Solo se
puede borrar una recolección Pendiente.** Una Finalizada ya sumó stock y forma
parte del historial: la API responde **409** (*"No se puede eliminar una
recolección finalizada."*) y no borra nada. La interfaz tampoco muestra el botón
"Eliminar" en las finalizadas. El Operario recibe 403.

#### CU28 – Finalizar Recolección

**Actor:** Administrador, Operario.

Pasa la recolección de Pendiente (`P`) a Finalizada (`F`) con
`POST /api/recolecciones/{id}/finalizar/`. A partir de ahí no se puede editar y
sus cantidades se suman al stock de cada producto. Si ya estaba finalizada
devuelve 400.

### Líneas de recolección

Cada línea indica un producto y la cantidad recolectada (entera, de 1 a
1.000.000). Una recolección no puede repetir el mismo producto ni quedar sin
líneas.

#### CU29 – Listar Líneas de Recolección

**Actor:** cualquier usuario autenticado.

Las líneas de una recolección vienen anidadas en el campo `lineas` de la
respuesta de CU24 (listado y detalle), cada una con su producto y cantidad. En
la pantalla se ven en el panel de detalle de la recolección seleccionada.

#### CU30 – Nueva Línea de Recolección

**Actor:** Administrador, Operario.

Se agrega al crear la recolección (CU25) o, en una Pendiente, enviando en
`lineas` (CU26) las existentes más la nueva. Solo se aceptan productos
**activos**; los productos desactivados que la recolección ya tenía se conservan
(se muestran como "(inactivo)").

#### CU31 – Modificar Línea de Recolección

**Actor:** Administrador, Operario.

Se cambia la cantidad (o el producto) de una línea de una recolección
Pendiente enviando en `lineas` (CU26) el listado actualizado. La API reemplaza
todas las líneas de la recolección por las recibidas.

#### CU32 – Borrar Línea de Recolección

**Actor:** Administrador, Operario.

Se quita una línea de una recolección Pendiente omitiéndola del listado `lineas`
enviado en CU26. No se puede dejar la recolección sin líneas: para eliminarla
por completo se usa CU27.

### Matriz rol × caso de uso

| Caso de uso | Administrador | Operario | Consulta |
|---|:---:|:---:|:---:|
| CU24 Buscar Avanzado Recolecciones | Sí | Sí | Sí |
| CU25 Nueva Recolección | Sí | Sí | No |
| CU26 Modificar Recolección (Pendiente) | Sí | Sí | No |
| CU27 Borrar Recolección (Pendiente) | Sí | No | No |
| CU28 Finalizar Recolección | Sí | Sí | No |
| CU29 Listar Líneas de Recolección | Sí | Sí | Sí |
| CU30 Nueva Línea de Recolección | Sí | Sí | No |
| CU31 Modificar Línea de Recolección | Sí | Sí | No |
| CU32 Borrar Línea de Recolección | Sí | Sí | No |

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
| Listar / Ver detalle (CU24, CU29) | ✅ | ✅ | ✅ |
| Crear recolección (CU25, CU30) | ✅ | ✅ | ❌ |
| Editar recolección PENDIENTE (CU26, CU30 a CU32) | ✅ | ✅ | ❌ |
| Finalizar recolección (CU28) | ✅ | ✅ | ❌ |
| Eliminar recolección PENDIENTE (CU27) | ✅ | ❌ | ❌ |

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
consulta. Como una recolección finalizada no se puede eliminar (ver CU27), lo
recolectado nunca se resta por un borrado.

### Lote en Transición

Se puede registrar una recolección con el lote del galpón en **Transición** (`T`)
o en **Producción** (`P`). Es una decisión deliberada: según la Educción de
requisitos, en la etapa de transición las gallinas "no son productivas, aunque
eventualmente pueden dejar huevos pequeños", y esos huevos se registran como
cualquier otro. No se bloquea ni se muestra aviso.

---

## Endpoints

| CU | Método | Ruta | Descripción | Rol |
|---|---|---|---|---|
| CU24, CU29 | GET | `/api/recolecciones/` | Listar paginado, con líneas (`?id_galpon=`, `?id_lote=`, `?estado=`, `?fecha_desde=`, `?fecha_hasta=`, `?page=`, `?page_size=`) | autenticado |
| CU25, CU30 | POST | `/api/recolecciones/` | Crear con líneas | Adm. / Operario |
| CU24, CU29 | GET | `/api/recolecciones/{id}/` | Detalle | autenticado |
| CU26, CU30 a CU32 | PUT/PATCH | `/api/recolecciones/{id}/` | Editar, incluidas las líneas (solo PENDIENTE) | Adm. / Operario |
| CU27 | DELETE | `/api/recolecciones/{id}/` | Eliminar (solo PENDIENTE; finalizada → 409) | Administrador |
| CU28 | POST | `/api/recolecciones/{id}/finalizar/` | Finalizar | Adm. / Operario |

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

Se implementaron **95 tests** en `backend/recolecciones/tests.py`, organizados
en 16 clases:

| Clase | Tests | Qué verifica |
|---|:---:|---|
| `BuscarRecoleccionTests` | 5 | Listar, filtrar por galpón y estado, ver detalle con líneas y lote |
| `CrearRecoleccionTests` | 9 | Creación exitosa, estado inicial, lote asignado automáticamente, validaciones (sin líneas, producto duplicado, producto inactivo, galpón sin lote activo) |
| `EditarRecoleccionTests` | 6 | Editar observaciones, reemplazar líneas, bloqueo de recolección finalizada, imposibilidad de editar el estado vía PATCH, producto duplicado en edición |
| `BorrarRecoleccionTests` | 3 | Borrado exitoso de una pendiente, cascade a líneas, 404 en inexistente |
| `FinalizarRecoleccionTests` | 5 | Finalizar exitoso, persistencia en base, idempotencia (ya finalizada → 400), 404 en inexistente, respuesta incluye lote |
| `PermisosRecoleccionTests` | 10 | Matriz completa: Admin puede crear/listar/eliminar; Operario puede crear/listar pero no eliminar; Consulta solo lista; sin token → 401 |
| `LoteFKTests` | 3 | FK guardada al crear, FK no cambia cuando el lote del galpón cambia, galpón sin lote activo devuelve 400 |
| `ValidacionesCantidadYGalponTests` | 8 | Cantidad negativa o cero → 400, cantidad 1 y 1.000.000 válidas, sobre el tope o enorme → 400 (no 500), no se puede cambiar el galpón al editar, reenviar el mismo galpón es válido |
| `FechaRecoleccionTests` | 4 | Fecha de mañana o hora futura del mismo día → 400, fecha pasada válida, no se puede editar la fecha a una futura |
| `ObservacionesRecoleccionTests` | 3 | 500 caracteres es válido, 501 → 400, no se puede editar a más de 500 |
| `UnaRecoleccionPorDiaTests` | 7 | Segunda recolección del mismo día y galpón → 400, otro galpón u otro día válidos, la finalizada también cuenta, medianoche (días distintos), editar dentro del mismo día, mover la fecha a un día ocupado → 400 |
| `ProductoDesactivadoTests` | 4 | Conservar un producto desactivado al editar, sumar uno activo, no agregar uno inactivo nuevo, no crear con inactivo |
| `StockDeProductosTests` | 5 | El stock de Productos: sin recolecciones es el inicial, las pendientes no suman, las finalizadas sí, finalizar por la API lo sube, suma varias y separa por producto |
| `BorrarFinalizadaBloqueadoTests` | 4 | Una finalizada devuelve 409 al Administrador, el Operario sigue recibiendo 403, el stock y las líneas no cambian, una pendiente sí se elimina |
| `FiltrosRecoleccionTests` | 13 | Fecha desde y hasta inclusivas (una recolección de las 23:00 entra con ese día), rango, mismo día, filtro por lote, filtros combinados, fecha inválida → 400, desde posterior a hasta → 400, `id_lote` / `id_galpon` no numérico o fuera de rango → 400, lote o galpón inexistente → lista vacía, `page_size` inválido usa el valor por defecto, Consulta y Operario pueden filtrar |
| `PaginacionRecoleccionTests` | 5 | 16 por página, última página con el resto, página inexistente → 404, `page_size` con tope de 100, el filtro se aplica antes de paginar |

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
| `recolecciones/views.py` | Nuevo: `RecoleccionViewSet` con `perform_create` (inyecta `id_lote` e `id_usuario`), acción `/finalizar/`, filtros por galpón, lote, estado y fechas, paginación y borrado solo de pendientes (409 en finalizadas) |
| `config/pagination.py` | Nuevo: `PaginacionListado` (16 por página, `page_size` hasta 100), reutilizable por otros módulos |
| `recolecciones/urls.py` | Nuevo: router DRF |
| `recolecciones/tests.py` | Nuevo: 95 tests |
| `usuarios/models.py` | Agrega propiedad `es_operario` al modelo `Usuario` |
| `usuarios/migrations/0002_alter_usuario_options.py` | Sincroniza opciones de Meta (`verbose_name`, `verbose_name_plural`) |
| `usuarios/permissions.py` | Agrega clases `EsOperario` y `EsAdministradorOOperario` |
| `config/urls.py` | Registra el router de recolecciones |

### Frontend

| Archivo | Cambio |
|---|---|
| `src/api/recolecciones.js` | Nuevo: `listRecolecciones`, `createRecoleccion`, `updateRecoleccion`, `deleteRecoleccion`, `finalizarRecoleccion` |
| `src/pages/RecoleccionesPage.jsx` | Nuevo: pantalla principal con tabla, panel de detalle, filtros (fecha desde/hasta, galpón, lote, estado, limpiar filtros) y paginación con selector de elementos por página; sin botón "Eliminar" en las finalizadas; incluye columna y fila de detalle "Cargado por" |
| `src/components/Paginacion.jsx` | Nuevo: barra de paginación reutilizable (Anterior / Siguiente, "Mostrando X–Y de N", números de página clickeables, selector de elementos por página y hook `useTamanoPagina` que recuerda la elección) |
| `src/index.css` | Estilos de la barra de paginación |
| `src/components/RecoleccionFormModal.jsx` | Nuevo: modal de alta y edición con gestión dinámica de líneas |
