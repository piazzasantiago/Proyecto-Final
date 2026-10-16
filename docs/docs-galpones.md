# Gestión de Galpones

**Rama:** `feature/gestion-galpones`
**Casos de uso:** CU09, CU10, CU11, CU12, CU13, CU14

Completa el módulo de Galpones. Incluye los endpoints de alta y baja lógica, la
tabla `UsuariosDelGalpon` (asignación de operarios), el filtrado de galpones por
rol, el control de permisos en la interfaz según el rol del usuario, y los tests
automatizados.

---

## 1. Alcance

### Qué incluye

- Endpoints `alta` y `baja` para el cambio de estado de un galpón (baja lógica).
- Modelo `UsuarioDelGalpon`: asigna operarios a galpones.
- Filtrado en `get_queryset`: el operario ve solo sus galpones asignados; el
  administrador y el rol consulta ven todos.
- Selector múltiple de operarios en el formulario de alta y edición.
- Panel de detalle con chips de operarios asignados.
- Tests automatizados del módulo (52 tests en 8 clases).
- Interfaz React con botones de acción visibles solo para el rol Administrador.

### Qué no incluye

- La gestión de lotes en sí (creación, ciclo de vida T→P→F, plan de
  transición). Eso se modela en `feature/gestion-lotes` (ver
  `docs-lotes.md`). Este módulo solo consume esos datos: muestra el
  `lote_actual` de cada galpón y bloquea la baja de un galpón con lote
  activo (CU14, flujo 1b).

---

## 2. Casos de uso

### CU09 – Buscar Galpón

**Actor:** cualquier usuario autenticado.

**Flujo principal**

1. El usuario accede a la sección Galpones.
2. El sistema muestra el listado de galpones según su rol:
   - Administrador y Consulta: todos los galpones.
   - Operario: solo los galpones que tiene asignados.
3. El usuario ingresa un texto de búsqueda o aplica el filtro por estado.
4. El sistema muestra los galpones que cumplen los criterios.
5. El usuario selecciona una tarjeta y el sistema muestra el panel de detalle.

**Flujos alternativos**

- **2a. Operario sin galpones asignados:** el sistema muestra lista vacía con el
  mensaje "No tenés galpones asignados."
- **4a. Sin resultados:** el sistema muestra un mensaje indicando que no hay
  galpones que coincidan con la búsqueda.

**Notas:** la búsqueda se realiza sobre nombre (`galpon`) y descripción.
El filtro de estado acepta `A` (Activo) o `I` (Inactivo).

---

### CU10 – Nuevo Galpón

**Actor:** Administrador.

**Flujo principal**

1. El Administrador selecciona "Nuevo galpón".
2. El sistema muestra el formulario de alta.
3. El Administrador completa nombre, latitud, longitud, superficie, capacidad,
   descripción (opcional) y selecciona los operarios a asignar (opcional).
4. El sistema valida los datos.
5. El sistema registra el galpón con estado Activo y guarda las asignaciones.
6. El sistema muestra el galpón creado seleccionado en el listado.

**Flujos alternativos**

- **4a. Capacidad menor o igual a 0:** el sistema lo informa y no crea el galpón.
- **4b. Superficie menor o igual a 0:** el sistema lo informa y no crea el galpón.
- **4c. ID de operario inválido:** el sistema devuelve 400 con detalle de los IDs inválidos.

**Postcondición:** el galpón queda disponible para la asignación de lotes.

---

### CU11 – Modificar Galpón

**Actor:** Administrador.

**Flujo principal**

1. El Administrador selecciona un galpón y elige "Editar".
2. El sistema muestra el formulario con los datos actuales, incluyendo los
   operarios ya asignados marcados.
3. El Administrador modifica los campos que necesite.
4. El sistema valida y guarda los cambios. Si `operarios_ids` se envía, la
   lista de asignaciones se reemplaza completamente.

**Flujos alternativos**

- **4a. Valores inválidos:** el sistema lo informa y no guarda.

**Notas:** la modificación es parcial: los campos no enviados conservan su
valor anterior. Si `operarios_ids` no se incluye en el PATCH, las asignaciones
no cambian.

---

### CU12 – Borrar Galpón

**Actor:** Administrador.

**Flujo principal**

1. El Administrador selecciona un galpón y elige "Eliminar".
2. El sistema solicita confirmación.
3. El Administrador confirma.
4. El sistema elimina el registro y todas sus asignaciones de operarios.

**Notas:** el borrado es físico. Para conservar el historial conviene darlo de
baja (CU14) en lugar de eliminarlo.

---

### CU13 – Dar de Alta Galpón

**Actor:** Administrador.
**Precondición:** el galpón está en estado Inactivo.

**Flujo principal**

1. El Administrador selecciona un galpón dado de baja y elige "Dar de alta".
2. El sistema cambia su estado a Activo.

**Flujos alternativos**

- **1a. El galpón ya está activo:** el sistema lo informa (409 Conflict).

---

### CU14 – Dar de Baja Galpón

**Actor:** Administrador.
**Precondición:** el galpón está en estado Activo.

**Flujo principal**

1. El Administrador selecciona un galpón y elige "Dar de baja".
2. El sistema cambia el estado del galpón a Inactivo.

**Flujos alternativos**

- **1a. El galpón ya está dado de baja:** el sistema lo informa (409 Conflict).
- **1b. El galpón tiene un lote activo:** si aloja un lote en estado Transición
  o Producción, el sistema rechaza la baja (409 Conflict) e indica el código
  y estado del lote que la bloquea. El Administrador debe finalizar ese lote
  (ver `docs-lotes.md`, endpoint `vaciar`) antes de poder dar de baja el
  galpón — dar de baja no reubica ni finaliza lotes por sí solo.

**Postcondición:** el galpón queda inactivo pero su registro y asignaciones se
conservan.

---

## 3. Matriz rol × caso de uso

| Caso de uso | Administrador | Operario | Consulta |
|---|:---:|:---:|:---:|
| CU09 Buscar Galpón | Todos | Solo asignados | Todos |
| CU10 Nuevo Galpón | Sí | No | No |
| CU11 Modificar Galpón | Sí | No | No |
| CU12 Borrar Galpón | Sí | No | No |
| CU13 Dar de Alta Galpón | Sí | No | No |
| CU14 Dar de Baja Galpón | Sí | No | No |

**Implementación:** el permiso `LecturaAutenticados_EscrituraAdministrador`
(definido en `usuarios/permissions.py`) aplica a todas las rutas del ViewSet.
El filtrado por rol se implementa en `get_queryset()`: los operarios ven solo
sus galpones asignados; los demás roles ven todos.

---

## 4. Modelo de datos

### Tabla `Galpones`

| Campo | Tipo | Restricciones |
|---|---|---|
| `idGalpon` | AutoField | Clave primaria |
| `galpon` | VARCHAR(80) | Obligatorio |
| `latitud` | DECIMAL(9,6) | Obligatorio |
| `longitud` | DECIMAL(9,6) | Obligatorio |
| `superficie` | DECIMAL(9,6) | Obligatorio, debe ser > 0 |
| `capacidad` | INTEGER | Obligatorio, debe ser > 0 |
| `estado` | CHAR(1) | A (Activo), I (Inactivo) |
| `descripcion` | TEXT | Opcional |

### Tabla `UsuariosDelGalpon`

| Campo | Tipo | Restricciones |
|---|---|---|
| `idUsuario` | INTEGER | FK → Usuarios, solo rol Operario |
| `idGalpon` | INTEGER | FK → Galpones |

**Restricción:** `UNIQUE(idUsuario, idGalpon)` — un operario no puede estar
asignado dos veces al mismo galpón.

**Propiedad calculada (no es columna):**

- `estado_display` — texto legible del estado (`"Activo"` / `"Inactivo"`),
  incluido en todas las respuestas de la API.
- `operarios` — lista de `{id_usuario, nombre_completo}` en las respuestas de lectura.

**Etiqueta visual:** el código `G-01`, `G-02`, etc., es una etiqueta derivada
del `id_galpon` generada en el frontend con `formatCodigo(id)`. No es un campo
de la base de datos.

---

## 5. Endpoints

| Caso de uso | Método | Ruta | Rol |
|---|---|---|---|
| CU09 | GET | `/api/galpones/` | autenticado |
| CU09 (detalle) | GET | `/api/galpones/{id}/` | autenticado |
| CU10 | POST | `/api/galpones/` | Administrador |
| CU11 | PATCH | `/api/galpones/{id}/` | Administrador |
| CU12 | DELETE | `/api/galpones/{id}/` | Administrador |
| CU13 | POST | `/api/galpones/{id}/alta/` | Administrador |
| CU14 | POST | `/api/galpones/{id}/baja/` | Administrador |
| — (info del detalle) | GET | `/api/galpones/{id}/existencias/` | autenticado (el operario, solo sus galpones) |

`existencias` devuelve, por materia prima que ingresó al galpón: `ultimo_ingreso` y
`ultimo_ingreso_fecha` (entrada finalizada más reciente), `descartado_desde_entonces`
(descartes de galpón finalizados posteriores a esa entrada), `existencia_estimada`
(`ultimo_ingreso − descartado_desde_entonces`, nunca negativa) y la unidad.
No es un caso de uso aparte: es información adicional del detalle del galpón,
mostrada en la sección "Materias primas en el galpón". Es una **estimación**, porque el
sistema no registra el consumo diario de las gallinas. El cálculo vive en
`entradas/stock.py` (ver `docs-entradas.md`) y sus tests, en `entradas/tests.py`.

**Filtros de CU09:** `?search=` (nombre o descripción), `?estado=A|I`,
`?ordering=galpon|capacidad|superficie`

**Respuesta de ejemplo (CU09):**

```json
{
  "count": 1,
  "results": [
    {
      "id_galpon": 1,
      "galpon": "Galpón Norte",
      "latitud": "-26.808000",
      "longitud": "-65.217000",
      "superficie": "200.000000",
      "capacidad": 500,
      "estado": "A",
      "estado_display": "Activo",
      "descripcion": "",
      "operarios": [
        {"id_usuario": 3, "nombre_completo": "Juan Pérez"}
      ],
      "lote_actual": {
        "id_lote": 7,
        "codigo": "L-2026-007",
        "estado": "T",
        "estado_display": "Transición",
        "cantidad_actual": 2500
      }
    }
  ]
}
```

**Campo `lote_actual` (solo lectura):** datos del lote en curso alojado en el
galpón (estado Transición o Producción), o `null` si el galpón está vacío. Se
resuelve en `GalponSerializer.get_lote_actual` con un import diferido de
`lotes.models.Lote` para no crear una dependencia de import a nivel de módulo
entre las apps `galpones` y `lotes` (ver `docs-lotes.md`).

**Campo `operarios_ids` (solo escritura):** lista de IDs de usuarios operarios
activos a asignar. En un PATCH, si se omite el campo, las asignaciones no cambian.

**Alta y baja:** se usan `POST` sobre URLs con nombre de acción en lugar de
`PATCH` sobre el campo `estado`, porque son transiciones con lógica de negocio
(validación de idempotencia, respuesta 409) y no simples ediciones de un campo.

---

## 6. Tests automatizados

Los tests viven en `backend/galpones/tests.py`. Se organizan en nueve clases
independientes; Django crea una base temporaria al principio y la destruye al
terminar.

### Estructura

| Clase | Tests | Qué cubre |
|---|:---:|---|
| `BuscarGalponTests` | 6 | CU09: listado, búsqueda por nombre y descripción, filtros por estado |
| `NuevoGalponTests` | 9 | CU10: alta válida, estado por defecto, validaciones de capacidad y superficie |
| `ModificarGalponTests` | 4 | CU11: modificación parcial, campo inválido, galpón inexistente |
| `BorrarGalponTests` | 2 | CU12: borrado físico, galpón inexistente |
| `AltaGalponTests` | 4 | CU13: alta, persistencia, idempotencia (409), galpón inexistente |
| `BajaGalponTests` | 9 | CU14: baja, persistencia, idempotencia (409), galpón inexistente, y el bloqueo si el galpón tiene un lote activo (Transición o Producción) |
| `PermisosGalponesTests` | 18 | Matriz rol × operación (Admin / Operario / Consulta / sin token) |
| `UsuariosDelGalponTests` | 10 | Asignación de operarios, validaciones, filtrado por rol en queryset |
| `OperariosInactivosTests` | 8 | Un operario dado de baja conserva su asignación pero no se lista, y no se pisa al editar el galpón |
| **Total** | **70** | |

### Cómo correrlos

```bash
cd backend
python manage.py test galpones
```

O junto con todos los tests del proyecto:

```bash
python manage.py test --verbosity=2
```

---

## 7. Archivos de la feature

### Backend

```
backend/
└── galpones/
    ├── models.py         Galpon + UsuarioDelGalpon
    ├── serializers.py    GalponSerializer con operarios (lectura/escritura)
    ├── views.py          GalponViewSet con alta/baja y get_queryset por rol
    ├── permissions.py    reutiliza LecturaAutenticados_EscrituraAdministrador
    ├── urls.py           router DefaultRouter
    ├── admin.py          GalponAdmin con OperarioInline + UsuarioDelGalponAdmin
    ├── migrations/
    │   ├── 0001_initial.py
    │   └── 0002_usuariodelgalpon.py
    └── tests.py          53 tests en 8 clases
```

### Frontend

```
frontend/src/
├── api/
│   ├── galpones.js       listGalpones, getGalpon, createGalpon, updateGalpon,
│   │                     deleteGalpon, altaGalpon, bajaGalpon
│   └── usuarios.js       + listOperarios()
├── pages/GalponesPage.jsx    tarjetas + panel de detalle con acciones por rol
│                             + chips de operarios asignados
└── components/GalponFormModal.jsx  formulario con selector múltiple de operarios
```

---

## 8. Decisiones de diseño

### 8.1 Reutilización del permiso de usuarios

`LecturaAutenticados_EscrituraAdministrador` ya estaba definido en
`usuarios/permissions.py`. Esta feature lo reutiliza sin duplicarlo.

### 8.2 Alta y baja como acciones POST, no PATCH

Dar de alta o de baja un galpón es una transición de estado con nombre, con
validación de idempotencia y un significado de negocio específico. Por eso se
expone como `POST /galpones/{id}/alta/` y `POST /galpones/{id}/baja/` en lugar
de `PATCH /galpones/{id}/` con `{"estado": "I"}`. La misma decisión se tomó
para usuarios (CU07 y CU08).

### 8.3 Baja sin confirmación en el frontend

La baja de un galpón no requiere `confirm()` porque es reversible: el Administrador
puede dar de alta el galpón inmediatamente. El borrado físico (CU12) sí pide
confirmación, porque es irreversible.

### 8.4 Filtrado por rol en `get_queryset`

El operario recibe solo los galpones que tiene asignados en `UsuariosDelGalpon`.
Esto aplica también al endpoint de detalle (`GET /galpones/{id}/`): si el
operario no está asignado a ese galpón, recibe 404, no 403, porque para él ese
recurso simplemente no existe.

### 8.5 `operarios_ids` solo al escribir, `operarios` solo al leer

El campo `operarios_ids` (lista de IDs) es `write_only`; el campo `operarios`
(lista de objetos `{id_usuario, nombre_completo}`) es calculado por
`SerializerMethodField` y es `read_only`. Esta separación evita que el
frontend tenga que transformar los objetos para enviarlos, y que el backend
devuelva IDs crudos que el frontend tenga que resolver.

### 8.6 Sincronización completa de operarios

Al modificar un galpón con `operarios_ids`, la lista anterior se elimina y se
reemplaza por completo. Esto simplifica la lógica del frontend (envía el estado
final deseado, no un diff) y evita inconsistencias.

### 8.7 Solo operarios activos pueden ser asignados

`validate_operarios_ids` rechaza cualquier ID que no corresponda a un usuario
con `rol=O` y `estado=A`. Esto impide asignar administradores, usuarios de
consulta, o usuarios dados de baja.

---

## 9. Verificación realizada

**Backend**

- 53 tests en verde.
- Los tres roles pueden listar y ver el detalle de sus galpones.
- Operario y Consulta reciben 403 al intentar crear, modificar, borrar o
  cambiar el estado de un galpón.
- Sin token, la API responde 401.
- Alta y baja devuelven 409 si el galpón ya está en el estado solicitado.
- Operario sin asignaciones recibe lista vacía (count: 0).
- Operario asignado a g1 y g2 no puede acceder a g3 (404).
- IDs de no-operarios en `operarios_ids` devuelven 400.

**Frontend**

- El botón "Nuevo galpón" no aparece para Operario y Consulta.
- El panel de detalle no muestra los botones de acción para esos roles.
- El botón "Dar de baja" aparece cuando el galpón está activo; "Dar de alta"
  cuando está inactivo.
- El formulario carga los operarios disponibles y marca los ya asignados.
- El panel de detalle muestra chips de operarios asignados.
- El operario ve el mensaje "No tenés galpones asignados" si su lista está vacía.

---

## 10. Pendientes

- **Existencia real de materias primas por galpón:** requiere un registro de consumo
  (alimentación diaria) que hoy no existe; la existencia mostrada es una estimación.

- ~~**Asociación con lotes:** cuando se implemente `feature/lotes`, un galpón
  dado de baja con lotes activos podría requerir validación adicional.~~
  Resuelto: ahora que `feature/gestion-lotes` existe, CU14 rechaza la baja
  (409) si el galpón tiene un lote en Transición o Producción (ver flujo
  alternativo 1b más arriba). El serializer también expone `lote_actual`
  en la respuesta de `GET /api/galpones/` para mostrarlo en el listado y
  en el panel de detalle.
