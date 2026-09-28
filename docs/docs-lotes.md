# Gestión de Lotes de Gallinas — CU42 a CU48

Documentación técnica del módulo `lotes`, implementado en la rama
`feature/gestion-lotes` e integrado a `develop` mediante Pull Request.

---

## Casos de uso cubiertos

| CU | Nombre | Actor |
|---|---|---|
| CU42 | Buscar Lote | Administrador, Operario, Consulta |
| CU43 | Nuevo Lote | Administrador |
| CU44 | Modificar Lote | Administrador |
| CU45 | Borrar Lote | Administrador |
| CU46 | Iniciar Producción | Administrador |
| CU48 | Vaciado Sanitario | Administrador |

---

## Modelo de datos

### `Lote`

Representa un conjunto de gallinas ponedoras alojadas en un galpón.

| Campo | Tipo | Descripción |
|---|---|---|
| `id_lote` | PK autoincremental | Identificador del lote |
| `id_galpon` | FK → `Galpon` | Galpón donde está alojado el lote |
| `fecha_ingreso` | `date` | Fecha en que ingresaron las aves |
| `cantidad_inicial` | `int` | Cantidad de aves al ingresar |
| `cantidad_actual` | `int` | Cantidad de aves en este momento |
| `estado` | `char(1)` | Estado del ciclo de vida (ver abajo) |
| `fecha_vaciado` | `date` | Fecha del vaciado sanitario; nula hasta que se registra |
| `observaciones` | `text` | Observaciones libres (opcional) |

**Estados del ciclo de vida:**

| Código | Nombre | Descripción |
|---|---|---|
| `T` | Transición | Las aves recién ingresaron; siguen el plan de transición |
| `P` | Producción | Las aves están en plena producción de huevos |
| `F` | Finalizado | El lote fue vaciado sanitariamente y el galpón está libre |

El estado inicial siempre es `T` (Transición). Las transiciones permitidas son
`T → P` (iniciar producción) y `T → F` o `P → F` (vaciado sanitario).
No existe retroceso de estado.

### `PlanTransicion`

Registro del plan de alimentación, agua y luz artificial para las cuatro semanas
de adaptación de las aves recién ingresadas.

| Campo | Tipo | Descripción |
|---|---|---|
| `id_plan` | PK autoincremental | |
| `id_lote` | FK → `Lote` (CASCADE) | Lote al que pertenece el plan |
| `estado` | `char(1)` | `E` En curso / `F` Finalizado |
| `fecha_inicio` | `date` | Igual a `fecha_ingreso` del lote |
| `fecha_fin` | `date` | 28 días después de `fecha_inicio` |
| `agua_semana1..4` | `decimal(6,2)` | Litros de agua por ave por día, semana 1 a 4 |
| `alimento_semana1..4` | `decimal(6,2)` | Gramos de alimento por ave por día |
| `horas_luz_semana1..4` | `decimal(4,2)` | Horas de luz artificial por día |

El plan se crea automáticamente al crear el lote y se finaliza (estado `F`)
cuando el lote pasa a Producción.

---

## Reglas de negocio

### Un galpón, un lote activo

Un galpón solo puede albergar **un lote activo a la vez**. Se consideran activos
los lotes en estado `T` (Transición) o `P` (Producción). Para registrar un nuevo
lote en un galpón, el lote anterior debe estar en estado `F` (Finalizado).

Esta regla se valida en `LoteSerializer.validate()` antes de crear el lote. Si
el galpón ya tiene un lote activo, el endpoint devuelve `400 Bad Request` con el
detalle del lote que lo ocupa.

### Galpón activo obligatorio

Solo se puede crear un lote en un galpón con estado `A` (Activo). Un galpón dado
de baja no puede recibir nuevas aves.

### Cantidad inicial positiva

`cantidad_inicial` debe ser mayor que cero. `cantidad_actual` se inicializa
igual a `cantidad_inicial` al crear el lote.

### Transiciones de estado

Las transiciones de estado solo ocurren a través de los endpoints dedicados
(`iniciar-produccion` y `vaciar`). El campo `estado` es `read_only` en el
serializer; modificarlo vía `PATCH` no tiene efecto.

---

## API REST

Base URL: `/api/lotes/`

### Listar lotes — `GET /api/lotes/`

Devuelve una lista paginada de lotes. Los resultados se filtran por rol:

- **Administrador / Consulta:** ven todos los lotes.
- **Operario:** ve solo los lotes de los galpones a los que está asignado.

**Parámetros de filtro:**

| Parámetro | Descripción | Ejemplo |
|---|---|---|
| `estado` | Filtra por estado del ciclo de vida | `?estado=T` |
| `id_galpon` | Filtra por galpón | `?id_galpon=3` |

**Respuesta `200`:**
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id_lote": 1,
      "codigo": "L-001",
      "id_galpon_id": 1,
      "galpon_nombre": "Galpón Norte",
      "fecha_ingreso": "2026-01-18",
      "cantidad_inicial": 2500,
      "cantidad_actual": 2500,
      "estado": "T",
      "estado_display": "Transición",
      "fecha_vaciado": null,
      "observaciones": "",
      "plan_transicion": { ... }
    }
  ]
}
```

### Detalle de lote — `GET /api/lotes/{id}/`

Devuelve el lote con su plan de transición completo. Los operarios solo pueden
ver los lotes de sus galpones asignados; cualquier otro devuelve `404`.

### Crear lote — `POST /api/lotes/`

**Rol requerido:** Administrador.

**Body:**
```json
{
  "id_galpon_id": 1,
  "fecha_ingreso": "2026-01-18",
  "cantidad_inicial": 2500,
  "observaciones": "",
  "plan_transicion": {
    "agua_semana1": "4.20",
    "alimento_semana1": "18.00",
    "horas_luz_semana1": "10.00",
    "agua_semana2": "4.80",
    "alimento_semana2": "21.50",
    "horas_luz_semana2": "12.00",
    "agua_semana3": "5.50",
    "alimento_semana3": "25.00",
    "horas_luz_semana3": "14.00",
    "agua_semana4": "6.10",
    "alimento_semana4": "28.50",
    "horas_luz_semana4": "16.00"
  }
}
```

**Respuesta `201`:** el lote creado con su plan de transición.

**Errores:**

| Código | Causa |
|---|---|
| `400` | Galpón inactivo, cantidad inicial ≤ 0, o galpón ya tiene un lote activo |
| `403` | El usuario no es Administrador |

### Modificar lote — `PATCH /api/lotes/{id}/`

**Rol requerido:** Administrador.

Permite modificar `observaciones`, `cantidad_actual` y campos del
`plan_transicion` (parcialmente). El estado no puede modificarse por este
endpoint.

### Eliminar lote — `DELETE /api/lotes/{id}/`

**Rol requerido:** Administrador.

Elimina el lote y su plan de transición (CASCADE). Devuelve `204 No Content`.

### Iniciar producción — `POST /api/lotes/{id}/iniciar-produccion/`

**Rol requerido:** Administrador.

Avanza el lote de `T` (Transición) a `P` (Producción) y marca el plan de
transición como Finalizado.

**Errores:**

| Código | Causa |
|---|---|
| `409` | El lote no está en estado Transición |

### Vaciar — `POST /api/lotes/{id}/vaciar/`

**Rol requerido:** Administrador.

Registra el vaciado sanitario del galpón: el lote pasa a estado `F`
(Finalizado) y se registra la `fecha_vaciado` con la fecha del día. Aplica
tanto desde `T` como desde `P`.

**Errores:**

| Código | Causa |
|---|---|
| `409` | El lote ya está Finalizado |

---

## Frontend

### Archivos

| Archivo | Descripción |
|---|---|
| `src/pages/LotesPage.jsx` | Pantalla principal del módulo |
| `src/components/LoteFormModal.jsx` | Modal de creación y edición de lotes |
| `src/api/lotes.js` | Funciones de acceso a la API de lotes |

### `LotesPage`

Sigue el mismo patrón de `GalponesPage`: lista de tarjetas a la izquierda y
panel de detalle a la derecha. Incluye:

- Búsqueda por texto y filtro por estado (Transición / Producción / Finalizado).
- Tarjeta por lote con código (`L-001`), galpón, estado y cantidad de aves.
- Panel de detalle con datos del lote, plan de transición en tabla y **stepper
  del ciclo de vida**.
- Botones de acción (solo visibles para Administrador): Editar, Iniciar
  Producción, Vaciar, Eliminar.
- Los operarios ven solo los lotes de sus galpones asignados y no pueden
  modificar nada.

### Stepper del ciclo de vida

El panel de detalle muestra un gráfico de cuatro pasos:

```
Ingreso → Transición → Producción → Vaciado sanitario
```

Los pasos completados se muestran en verde; el paso actual, en azul; los
siguientes, en gris. Se implementa con CSS Grid de cuatro columnas iguales para
mantener los círculos alineados horizontalmente en cualquier tamaño de pantalla.

### `LoteFormModal`

Modal de dos secciones:

1. **Datos del lote:** galpón (select con galpones activos), fecha de ingreso,
   cantidad inicial y observaciones.
2. **Plan de transición:** tabla de 4 semanas × 3 parámetros (agua, alimento,
   horas de luz).

En modo edición, los campos del lote y del plan se pre-cargan con los valores
actuales.

---

## Tests

Ubicación: `backend/lotes/tests.py`

**Total: 50 tests — 50/50 ✅**

| Clase | Tests | Qué cubre |
|---|---|---|
| `BuscarLoteTests` | 6 | CU42: listar, filtrar por estado, filtrar por galpón, detalle con plan |
| `NuevoLoteTests` | 9 | CU43: creación exitosa, estado inicial, plan creado, validaciones de negocio, galpón ocupado |
| `ModificarLoteTests` | 5 | CU44: modificar campos y plan, inmutabilidad del estado via PATCH |
| `BorrarLoteTests` | 3 | CU45: borrar lote y plan en cascada, 404 en lote inexistente |
| `IniciarProduccionTests` | 5 | CU46: transición exitosa, persistencia, plan finalizado, 409 desde estado incorrecto |
| `VaciarTests` | 5 | CU48: vaciado desde T y P, fecha registrada, 409 si ya finalizado |
| `PermisosLotesTests` | 12 | Matriz rol × operación (Administrador / Operario / Consulta / sin token) |
| `FiltradoPorRolTests` | 5 | Operario ve solo sus galpones; Administrador y Consulta ven todo |

Correr solo este módulo:

```bash
python manage.py test lotes --verbosity=2
```

---

## Decisiones de diseño

**Validación de galpón ocupado en el serializer, no en el modelo.**
La validación cross-field se implementa en `LoteSerializer.validate()` en lugar
de un constraint en la base de datos. Esto permite que DRF devuelva un `400`
con un mensaje legible en lugar de una excepción de integridad sin contexto.
En edición (`PATCH`) la validación se omite porque el galpón no cambia.

**`PlanTransicion` como objeto anidado.**
El plan de transición no se expone como endpoint propio (`/api/planes/`). Se
crea, lee y edita siempre a través del lote al que pertenece. Esto simplifica
el contrato de la API y refleja que el plan no tiene sentido fuera de su lote.

**Código de lote generado en el frontend.**
El campo `codigo` (ej. `L-001`) es una etiqueta visual derivada del `id_lote`
con `padStart`. No se persiste en la base de datos, de la misma forma que el
código de galpón (`G-01`).

**Estado `read_only` en el serializer.**
El campo `estado` no puede modificarse vía `PATCH`. Los cambios de estado solo
ocurren a través de los endpoints de acción (`iniciar-produccion`, `vaciar`),
que validan la transición permitida y devuelven `409` si el estado no es el
esperado. Esto hace el flujo explícito y evita estados inconsistentes.

**Filtrado por rol en `get_queryset`.**
En lugar de usar permisos de objeto (DRF `has_object_permission`), el filtrado
se aplica directamente en `get_queryset`: los operarios reciben un queryset
restringido a los galpones a los que están asignados, lo que devuelve `404` en
lugar de `403` al intentar acceder a un lote de otro galpón — el comportamiento
habitual en sistemas donde la existencia del recurso también es confidencial.
