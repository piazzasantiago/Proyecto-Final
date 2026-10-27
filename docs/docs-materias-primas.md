# Gestión de Materias Primas

**Rama:** `feature/gestion-materias-primas`
**Casos de uso:** CU55, CU56, CU57, CU58, CU59, CU60

Módulo que administra el catálogo de materias primas (insumos y consumibles)
utilizados en los galpones: alimentos balanceados, productos de sanidad,
materiales de cama, etc. Es prerrequisito para el módulo de Descartes, ya que
los descartes pueden registrarse contra gallinas de un lote, productos o
materias primas.

---

## 1. Alcance

### Qué incluye

- CRUD completo de materias primas (nombre, descripción, unidad, estado,
  stock mínimo, stock inicial).
- Activar / desactivar como acciones dedicadas (no vía `PATCH` del estado).
- `stock_actual` expuesto como campo calculado de solo lectura:
  `stock_inicial` más lo comprado en compras finalizadas (`stock_compras`) menos lo
  descartado (`stock_descartado`) y lo enviado a galpones (`stock_entradas`).
- Alerta visual en la tarjeta y en el panel de detalle cuando
  `stock_actual < stock_minimo`.
- Acceso de solo lectura para los roles Operario y Consulta.
- Tests automatizados del módulo (58 tests en 10 clases).
- Interfaz React con tarjetas compactas y panel de detalle; botones de acción
  visibles solo para el rol Administrador.
- Script standalone `seed_materias_primas.py` (raíz del repo) para poblar la
  tabla con 18 materias primas de ejemplo.

- Sección "Compras recientes" en el panel de detalle: las últimas 4 compras que
  incluyen esa materia prima (la más nueva primero), con N° de comprobante, fecha,
  estado, cantidad comprada de esa materia prima, proveedor y total de la compra.
  Usa `GET /api/compras/?id_materia_prima=N&page_size=4`. El Operario no la ve
  (no tiene acceso al módulo de Compras).

### Qué no incluye

- Las compras se registran en su propio módulo (ver `docs-compras.md`); acá solo
  se refleja su efecto en el stock.

---

## 2. Casos de uso

### CU55 – Buscar Materia Prima

**Actor:** cualquier usuario autenticado.

Lista las materias primas con búsqueda por nombre/descripción (`?search=`) y
filtro por estado (`?estado=A|I`).

### CU56 – Nueva Materia Prima

**Actor:** Administrador.

Crea una materia prima con nombre (único, hasta 80 caracteres), unidad de
medida, stock mínimo y stock inicial. La descripción es opcional. El estado
inicial siempre es Activo.

### CU57 – Modificar Materia Prima

**Actor:** Administrador.

Modifica nombre, descripción, unidad, stock mínimo o stock inicial. El estado
no se puede cambiar por este medio.

### CU58 – Borrar Materia Prima

**Actor:** Administrador.

Elimina la materia prima físicamente. Si tiene registros asociados (compras,
entradas o descartes), el borrado se rechaza con `409` y el mensaje indica que
debe desactivarse en su lugar.

### CU59 – Dar de Alta Materia Prima

**Actor:** Administrador.

Pasa una materia prima de Inactiva a Activa. Devuelve `409` si ya estaba
activa.

### CU60 – Dar de Baja Materia Prima

**Actor:** Administrador.

Pasa una materia prima de Activa a Inactiva. Devuelve `409` si ya estaba
inactiva. Desactivar no afecta los registros históricos ya asociados.

---

## 3. Matriz rol × caso de uso

| Caso de uso | Administrador | Operario | Consulta |
|---|:---:|:---:|:---:|
| CU55 Buscar Materia Prima | Sí | Sí | Sí |
| CU56 Nueva Materia Prima | Sí | No | No |
| CU57 Modificar Materia Prima | Sí | No | No |
| CU58 Borrar Materia Prima | Sí | No | No |
| CU59 Dar de Alta Materia Prima | Sí | No | No |
| CU60 Dar de Baja Materia Prima | Sí | No | No |

**Implementación:** el permiso `LecturaAutenticados_EscrituraAdministrador`
(definido en `usuarios/permissions.py`) aplica a todas las rutas del ViewSet.
El menú habilita la sección para los tres roles (`roles: ["A", "O", "C"]` en
`config/menu.js`); el botón "Nueva materia prima" y las acciones del detalle
solo se renderizan cuando `esAdministrador` es verdadero.

---

## 4. Modelo de datos

### Tabla `MateriasPrimas`

| Campo | Tipo | Restricciones |
|---|---|---|
| `id_materia_prima` | AutoField | Clave primaria |
| `materia_prima` | VARCHAR(80) | Obligatorio, único sin distinguir mayúsculas ni tildes (ver 5.1) |
| `descripcion` | TEXT | Opcional |
| `unidad` | VARCHAR(20) | Obligatorio; una de: kg, g, L, mL, unid., dosis, bolsa, saco (default kg) |
| `estado` | CHAR(1) | A (Activo), I (Inactivo) — default A |
| `stock_minimo` | DecimalField(10,2) | Obligatorio ≥ 0 — default 0 |
| `stock_inicial` | DecimalField(10,2) | Obligatorio ≥ 0 — default 0 (stock de partida o ajuste manual) |

**Propiedades calculadas (no son columnas):**

- `estado_display` — texto legible del estado (`"Activo"` / `"Inactivo"`),
  incluido en todas las respuestas de la API.
- `stock_descartado` — suma de las cantidades de las líneas de descartes de
  categoría **Stock** y estado **Finalizado** de esa materia prima (ver
  `docs-descartes.md`). Los descartes de galpón no cuentan.
- `stock_compras` — suma de las cantidades de las líneas de compras de materias
  primas **finalizadas** (ver `docs-compras.md`). Las pendientes no cuentan.
- `stock_actual` — `stock_inicial + stock_compras − stock_descartado −
  stock_entradas`.

---

## 5. Endpoints

| Caso de uso | Método | Ruta | Rol |
|---|---|---|---|
| CU55 | GET | `/api/materias-primas/` | autenticado |
| CU55 (detalle) | GET | `/api/materias-primas/{id}/` | autenticado |
| CU56 | POST | `/api/materias-primas/` | Administrador |
| CU57 | PATCH | `/api/materias-primas/{id}/` | Administrador |
| CU58 | DELETE | `/api/materias-primas/{id}/` | Administrador |
| CU59 | POST | `/api/materias-primas/{id}/activar/` | Administrador |
| CU60 | POST | `/api/materias-primas/{id}/desactivar/` | Administrador |
| — | GET | `/api/materias-primas/similares/?nombre=…[&excluir=ID]` | autenticado |

**Filtros de CU55:** `?search=` (nombre o descripción), `?estado=A|I`

### 5.1 Validaciones de nombre y unidad

- **Nombre único sin distinguir mayúsculas ni tildes:** `Maíz`, `maíz`, `MAIZ` y
  `Máiz` se consideran el mismo nombre. Los espacios de los bordes se descartan
  y los repetidos se colapsan. Si ya existe, responde 400 indicando cuál
  (`Ya existe una materia prima con ese nombre ("Maíz").`). Al modificar, se
  excluye la propia materia prima, así que puede cambiar solo su capitalización.
  La comparación se hace en la capa de serializer (no es una restricción de la
  base de datos) usando `normalizacion.normalizar_nombre()`.
- **Unidad de medida:** solo se aceptan las opciones del combo del formulario
  (`UNIDADES_VALIDAS` en `serializers.py`: kg, g, L, mL, unid., dosis, bolsa,
  saco). Cualquier otro valor responde 400. Si una materia prima ya tuviera
  guardada otra unidad, puede conservarla al editarla. La validación está en el
  serializer, por lo que no requiere migración.
- **Aviso de similares:** `GET /api/materias-primas/similares/?nombre=maiz`
  devuelve hasta 5 materias primas con nombre igual (`exacta: true`) o parecido
  (uno contiene al otro, `exacta: false`), ignorando mayúsculas y tildes.
  `?excluir=ID` omite una materia prima (se usa al editar). El formulario lo
  consulta mientras se escribe (con 300 ms de espera): si hay coincidencia
  exacta muestra un error en rojo, y si solo hay parecidas, un aviso suave. El
  backend vuelve a validar al guardar.

**Respuesta de ejemplo (CU55):**

```json
{
  "count": 1,
  "results": [
    {
      "id_materia_prima": 1,
      "materia_prima": "Balanceado postura",
      "descripcion": "Alimento balanceado para gallinas en etapa de postura.",
      "unidad": "kg",
      "estado": "A",
      "estado_display": "Activo",
      "stock_minimo": "200.00",
      "stock_inicial": "500.00",
      "stock_descartado": "20.00",
      "stock_actual": "480.00"
    }
  ]
}
```

**Campo `estado` (solo lectura vía `PATCH`):** se incluye en las respuestas
pero modificarlo con `PATCH` no tiene efecto; los cambios de estado solo
ocurren a través de `activar`/`desactivar`.

**Campos `stock_minimo` y `stock_inicial` (editables):** `DecimalField` con
dos decimales; un valor negativo devuelve `400`.

**Campos `stock_descartado` y `stock_actual` (solo lectura):** se calculan;
enviarlos en un `POST`/`PATCH` no tiene efecto. El listado obtiene
`stock_descartado` con una subconsulta (`anotar_descartado`), sin una consulta
por materia prima. Solo restan los descartes de stock en estado Finalizado.

---

### Paginación del listado

`GET /api/materias-primas/` devuelve los resultados paginados de a **16 registros**
(`?page=N`), con la forma `count`, `next`, `previous` y `results`. Se puede pedir
otro tamaño con `?page_size=` (máximo 100) y los filtros y la búsqueda se aplican
**antes** de paginar. Usa `PaginacionListado` (`backend/config/pagination.py`), la
misma clase que Recolecciones.

Las tarjetas se paginan y la barra de paginación queda debajo de la grilla (`src/pages/MateriaPrimasPage.jsx`): "Mostrando X–Y de N", Anterior / Siguiente, números de
página clickeables y selector de elementos por página (la barra se muestra siempre, también con una sola página), que se recuerda en el
navegador (`useTamanoPagina("materias-primas")`). Al cambiar un filtro o la búsqueda se vuelve
a la página 1, y si al eliminar un registro la página queda vacía se retrocede a
la anterior. Los desplegables que usan materias primas activas (Entradas, Compras, Descartes) las traen con `traerTodas`.

Tests: `PaginacionMateriasPrimasTests` en `backend/config/tests_pagination.py` (7 tests: 16 por página,
última página con el resto, `page_size`, páginas sin repetidos, página inexistente
→ 404 y filtro aplicado antes de paginar).

## 6. Tests automatizados

Los tests viven en `backend/materias_primas/tests.py`. Se organizan en diez
clases independientes.

### Estructura

| Clase | Tests | Qué cubre |
|---|:---:|---|
| `BuscarMateriaPrimaTests` | 6 | CU55: listado, búsqueda por nombre y descripción, filtros por estado |
| `NuevaMateriaPrimaTests` | 6 | CU56: alta válida, estado por defecto, descripción opcional, nombre duplicado (400), decimales en stock |
| `ModificarMateriaPrimaTests` | 4 | CU57: modificación parcial, inmutabilidad del estado vía `PATCH`, materia prima inexistente |
| `BorrarMateriaPrimaTests` | 2 | CU58: borrado físico, materia prima inexistente |
| `ActivarMateriaPrimaTests` | 4 | CU59: alta (activación), persistencia, idempotencia (409), materia prima inexistente |
| `DesactivarMateriaPrimaTests` | 4 | CU60: baja (desactivación), persistencia, idempotencia (409), materia prima inexistente |
| `PermisosMateriaPrimaTests` | 14 | Matriz rol × operación (Admin / Operario / Consulta / sin token) |
| `StockMateriaPrimaTests` | 4 | `stock_minimo` y `stock_inicial` al crear y vía `PATCH`, rechazo de negativos, `stock_actual` de solo lectura |
| `NombreUnidadValidacionTests` | 8 | Nombre duplicado ignorando mayúsculas y tildes, espacios, edición del propio nombre o al de otra, unidad fuera del combo, todas las unidades del combo |
| `SimilaresTests` | 6 | Endpoint `similares`: exacta con tildes/mayúsculas, parecidas, sin coincidencias, nombre vacío, `excluir`, requiere autenticación |
| **Total** | **58** | |

### Cómo correrlos

```bash
cd backend
python manage.py test materias_primas
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
└── materias_primas/
    ├── models.py         MateriaPrima
    ├── serializers.py    MateriaPrimaSerializer (estado read-only, stock_actual calculado)
    ├── views.py          MateriaPrimaViewSet con activar/desactivar
    ├── urls.py           router DefaultRouter
    ├── admin.py          MateriaPrimaAdmin
    ├── migrations/
    │   └── 0001_initial.py
    └── tests.py          58 tests en 10 clases
```

### Frontend

```
frontend/src/
├── api/materias-primas.js              listMateriasPrimas, getMateriaPrima,
│                                        createMateriaPrima, updateMateriaPrima,
│                                        deleteMateriaPrima, activarMateriaPrima,
│                                        desactivarMateriaPrima
├── pages/MateriaPrimasPage.jsx         tarjetas (galpon-card) + panel de detalle
│                                        con alerta de stock bajo
└── components/MateriaPrimaFormModal.jsx  formulario: nombre, descripción, unidad,
                                          stock mínimo, stock inicial
```

### Raíz del repo

```
seed_materias_primas.py   script standalone psycopg2 con 18 materias primas de ejemplo
```

---

## 8. Decisiones de diseño

### 8.1 Reutilización del permiso de Galpones y Productos

`LecturaAutenticados_EscrituraAdministrador` ya estaba definido en
`usuarios/permissions.py`. Esta feature lo reutiliza sin duplicarlo, siguiendo
el mismo patrón que Productos.

### 8.2 Activar/desactivar como acciones POST, no PATCH

Igual que Galpones y Productos, activar y desactivar son transiciones de estado
con nombre, con validación de idempotencia (409) y significado de negocio
específico. Se exponen como `POST /materias-primas/{id}/activar/` y
`POST /materias-primas/{id}/desactivar/`, y `estado` queda `read_only` en el
serializer.

### 8.3 DecimalField en lugar de PositiveIntegerField

A diferencia de Productos (que usa enteros para el stock de huevos), las
materias primas se miden en unidades continuas (kg, mL, g). Se eligió
`DecimalField(max_digits=10, decimal_places=2)` para cubrir tanto insumos
medidos con precisión (como vitaminas en gramos) como materiales a granel
(como alimento en kilogramos). El frontend usa `step="0.01"` en los inputs
numéricos del formulario.

### 8.4 stock_actual como campo calculado

El dominio describe el stock disponible como un valor dinámico
(`stock_inicial + compras − descartes`). Se eligió exponer `stock_actual` como
`SerializerMethodField` desde el principio, para que el frontend y los tests ya
consumieran la interfaz definitiva. Al construirse Descartes solo cambió la
implementación del método, sin romper ningún contrato de API: ahora devuelve
`stock_inicial − stock_descartado`, donde `stock_descartado` suma los descartes
de categoría Stock finalizados. Con Compras se le suma además lo comprado en compras finalizadas.

`materias_primas` no importa `descartes` a nivel de módulo (es `descartes` la
que depende de ella); el cálculo usa imports diferidos en la vista y el
serializer. Los tests que combinan ambos módulos viven en `descartes/tests.py`
(`FinalizarStockTests`).

### 8.5 Alerta de stock mínimo en la UI

La tarjeta de cada materia prima compara `stock_actual` con `stock_minimo` y
muestra una fila roja con ícono de advertencia cuando el stock está por debajo.
El panel de detalle repite el aviso como banner rojo visible arriba del cuerpo.
La comparación se hace con `Number()` en el frontend para evitar comparaciones
de strings (`"200.00" < "500.00"` sería falsa).

### 8.6 Misma grilla visual que Galpones

El primer diseño de la tarjeta usó estilos personalizados que resultaron
visualmente inconsistentes con el resto de la app. Se migró a las clases
`galpon-card`, `gc-top`, `gc-name`, `gc-stats` y `gc-stat`, que ya están
definidas en `index.css` y son las mismas que usa GalponesPage. El nombre
lleva `fontWeight: 600` y `color: var(--gray-900)` para que destaque sin
romper la paleta del sistema.

---

## 9. Verificación realizada

**Backend**

- 58 tests del módulo en verde.
- Suite completa del proyecto en verde (331 tests).
- Los tres roles pueden listar y ver el detalle de materias primas.
- Operario recibe 403 al intentar crear, modificar, borrar o cambiar el estado.
- Sin token, la API responde 401.
- Activar y desactivar devuelven 409 si la materia prima ya está en el estado
  solicitado.
- Un nombre duplicado devuelve 400, aunque difiera en mayúsculas o tildes.
- Una unidad fuera de las opciones del combo devuelve 400.
- Un `stock_minimo` o `stock_inicial` negativo devuelve 400.
- `stock_actual` resta los descartes de stock finalizados; los pendientes y los
  de galpón no restan.

**Frontend**

- El botón "Nueva materia prima" y las acciones del panel de detalle (Editar,
  Dar de alta/baja, Eliminar) no aparecen para Operario ni Consulta.
- La alerta de stock bajo aparece en la tarjeta y en el panel de detalle cuando
  corresponde.
- El formulario avisa mientras se escribe el nombre si ya existe uno igual
  (error) o parecido (aviso), sin distinguir mayúsculas ni tildes.
- El formulario incluye selector de unidad (kg, g, L, mL, unid., dosis, bolsa, saco)
  y campos decimales para stock mínimo e inicial.

---

## 10. Pendientes

- *Resuelto (F-12):* compras recientes de cada materia prima en el detalle.
- *Resuelto con Compras:* el borrado de una materia prima con compras, entradas o
  descartes asociados devuelve `409` con un mensaje claro (`ProtectedError`
  capturado en la vista).
