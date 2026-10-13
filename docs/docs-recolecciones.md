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
  el lote activo en ese momento, la fecha y hora, el estado y observaciones
  opcionales.
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

El campo `id_lote` no se envía: la API lo detecta e inyecta automáticamente.

### Ejemplo de respuesta

```json
{
  "id_recoleccion": 7,
  "galpon": { "id_galpon": 1, "galpon": "Galpón Norte" },
  "lote": { "id_lote": 3, "codigo": "L-2026-003" },
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

Se implementaron **68 tests** en `backend/recolecciones/tests.py`, organizados
en 12 clases:

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

Ejecutar:

```bash
python manage.py test recolecciones --verbosity=2
```

---

## Archivos modificados o creados

### Backend

| Archivo | Cambio |
|---|---|
| `recolecciones/models.py` | Nuevo: modelos `Recoleccion` y `LineaRecoleccion` |
| `recolecciones/migrations/0001_initial.py` | Migración inicial |
| `recolecciones/migrations/0002_recoleccion_id_lote.py` | Agrega FK `id_lote` |
| `recolecciones/serializers.py` | Nuevo: serializers cabecera-líneas con `LoteResumenSerializer` |
| `recolecciones/views.py` | Nuevo: `RecoleccionViewSet` con `perform_create` y acción `/finalizar/` |
| `recolecciones/urls.py` | Nuevo: router DRF |
| `recolecciones/tests.py` | Nuevo: 68 tests |
| `usuarios/models.py` | Agrega propiedad `es_operario` al modelo `Usuario` |
| `usuarios/permissions.py` | Agrega clases `EsOperario` y `EsAdministradorOOperario` |
| `config/urls.py` | Registra el router de recolecciones |

### Frontend

| Archivo | Cambio |
|---|---|
| `src/api/recolecciones.js` | Nuevo: `listRecolecciones`, `createRecoleccion`, `updateRecoleccion`, `deleteRecoleccion`, `finalizarRecoleccion` |
| `src/pages/RecoleccionesPage.jsx` | Nuevo: pantalla principal con tabla, panel de detalle y filtros |
| `src/components/RecoleccionFormModal.jsx` | Nuevo: modal de alta y edición con gestión dinámica de líneas |

---

## Pendientes de la feature

Los siguientes puntos quedaron identificados para resolver antes de integrar a
`develop` o en un `fix/` posterior:

### 1. Permitir al Operario eliminar recolecciones en estado Pendiente

Actualmente solo el Administrador puede eliminar recolecciones (endpoint
`DELETE`). La regla de negocio a definir es si el Operario debería poder
eliminar las que él mismo creó mientras están en estado `P`, pero no las
finalizadas.

Para implementarlo, cambiar `get_permissions` en `RecoleccionViewSet`:

```python
def get_permissions(self):
    if self.action in ("list", "retrieve"):
        return [IsAuthenticated()]
    if self.action == "destroy":
        # Opción actual: solo Admin
        return [EsAdministrador()]
        # Opción propuesta: Admin siempre; Operario solo si está PENDIENTE
        # (la restricción por estado se aplica en perform_destroy o has_object_permission)
    return [EsAdministradorOOperario()]
```

La lógica de estado (`solo PENDIENTE para Operario`) se implementa mejor en
`has_object_permission` dentro de una clase de permiso específica, para no
mezclar validación de negocio con la lógica de permisos del ViewSet.

### 2. Quitar el ícono de "ojito" en la tabla de recolecciones

La última columna de la tabla (`RecoleccionesPage.jsx`) muestra un ícono
`fa-eye` decorativo. Dado que el detalle se despliega al hacer clic en la fila,
el ícono no aporta funcionalidad y genera confusión visual. Simplemente
eliminar la columna `<th></th>` y la `<td>` con el ícono.

### ~~3. Definir si se puede editar el galpón de una recolección existente~~

Resuelto: no se puede cambiar el galpón de una recolección existente. El
serializer rechaza el cambio con HTTP 400 (ver "Validaciones del backend"). Si
se equivocaron de galpón, se elimina la recolección y se crea de nuevo.
