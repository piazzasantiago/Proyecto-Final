# Gestión de Productos

**Rama:** `feature/gestion-productos`
**Casos de uso:** CU49, CU50, CU51, CU52, CU53, CU54

Módulo que administra el catálogo de productos que se obtienen de la
producción (en este caso, huevos clasificados por tamaño: Nº1, Nº2 y Nº3,
aunque el modelo es escalable a otros productos). Cada línea de recolección
de `feature/gestion-recolecciones` referenciará uno de estos productos.

---

## 1. Alcance

### Qué incluye

- CRUD completo de productos (nombre, descripción, estado).
- Activar / desactivar como acciones dedicadas (no vía `PATCH` del estado).
- Stock: `stock_inicial` (carga manual del Administrador) más lo recolectado en
  recolecciones finalizadas, menos lo descartado en descartes de stock
  finalizados. La API expone `stock_recolectado`, `stock_descartado` y
  `stock_actual` como campos calculados de solo lectura.
- Acceso de solo lectura para el rol Consulta.
- Tests automatizados del módulo (44 tests en 8 clases).
- Interfaz React con tarjetas compactas y panel de detalle; botones de acción
  visibles solo para el rol Administrador.

### Qué no incluye

- El descuento de stock por salidas. La Educción de requisitos describe el
  stock disponible como recolecciones menos descartes menos salidas; hoy se
  suman las recolecciones y se restan los descartes, pero Salidas todavía no
  existe (ver sección 10, Pendientes).
- La carga de las recolecciones. Eso se modela en `feature/gestion-recolecciones`
  (ver `docs-recolecciones.md`), que consume los productos activos de este
  módulo y aporta el stock recolectado.

---

## 2. Casos de uso

### CU49 – Nuevo Producto

**Actor:** Administrador.

Crea un producto con nombre (único, hasta 80 caracteres) y descripción
opcional. El estado inicial siempre es Activo y el stock inicial es 0 salvo
que se indique otro valor.

### CU50 – Buscar Producto

**Actor:** cualquier usuario autenticado.

Lista los productos con búsqueda por nombre/descripción (`?search=`) y
filtro por estado (`?estado=A|I`).

### CU51 – Activar Producto

**Actor:** Administrador.

Pasa un producto de Inactivo a Activo. Devuelve `409` si ya estaba activo.

### CU52 – Modificar Producto

**Actor:** Administrador.

Modifica nombre, descripción o stock actual. El estado no se puede cambiar
por este medio.

### CU53 – Borrar Producto

**Actor:** Administrador.

Elimina el producto físicamente. Si tiene líneas de recolección asociadas
(cuando ese módulo exista), el borrado deberá rechazarse — hoy no hay
ninguna relación que lo impida.

### CU54 – Desactivar Producto

**Actor:** Administrador.

Pasa un producto de Activo a Inactivo. Devuelve `409` si ya estaba inactivo.
Desactivar un producto no afecta las líneas de recolección ya registradas
con él (mismo criterio que con los operarios inactivos de un galpón).

---

## 3. Matriz rol × caso de uso

| Caso de uso | Administrador | Operario | Consulta |
|---|:---:|:---:|:---:|
| CU49 Nuevo Producto | Sí | No | No |
| CU50 Buscar Producto | Todos | No | Todos |
| CU51 Activar Producto | Sí | No | No |
| CU52 Modificar Producto | Sí | No | No |
| CU53 Borrar Producto | Sí | No | No |
| CU54 Desactivar Producto | Sí | No | No |

**Implementación:** el permiso `LecturaAutenticados_EscrituraAdministrador`
(definido en `usuarios/permissions.py` y reutilizado de Galpones) aplica a
todas las rutas del ViewSet: cualquier usuario autenticado puede leer
(`GET`), solo el Administrador puede escribir. El rol Operario no tiene
acceso porque el ítem de menú correspondiente no está habilitado para él
(`roles: ["A", "C"]` en `config/menu.js`); a nivel de API, un Operario
autenticado sí podría leer si llamara al endpoint directamente, igual que
sucede con Galpones.

---

## 4. Modelo de datos

### Tabla `Productos`

| Campo | Tipo | Restricciones |
|---|---|---|
| `idProducto` | AutoField | Clave primaria |
| `producto` | VARCHAR(80) | Obligatorio, único |
| `descripcion` | TEXT | Opcional |
| `estado` | CHAR(1) | A (Activo), I (Inactivo) — default A |
| `stock_inicial` | INTEGER | Obligatorio ≥ 0 — default 0 (stock de partida o ajuste manual) |

**Propiedad calculada (no es columna):**

- `estado_display` — texto legible del estado (`"Activo"` / `"Inactivo"`),
  incluido en todas las respuestas de la API.
- `stock_recolectado` — suma de las cantidades de las líneas de recolecciones
  **finalizadas** de ese producto.
- `stock_descartado` — suma de las cantidades de las líneas de descartes de
  categoría **Stock** y estado **Finalizado** de ese producto (ver
  `docs-descartes.md`). Los descartes de galpón no cuentan.
- `stock_actual` — `stock_inicial + stock_recolectado − stock_descartado`. No se
  guarda: se calcula en cada consulta, así que no puede desfasarse (por ejemplo,
  si se borra una recolección finalizada, el stock baja solo).

---

## 5. Endpoints

| Caso de uso | Método | Ruta | Rol |
|---|---|---|---|
| CU50 | GET | `/api/productos/` | autenticado |
| CU50 (detalle) | GET | `/api/productos/{id}/` | autenticado |
| CU49 | POST | `/api/productos/` | Administrador |
| CU52 | PATCH | `/api/productos/{id}/` | Administrador |
| CU53 | DELETE | `/api/productos/{id}/` | Administrador |
| CU51 | POST | `/api/productos/{id}/activar/` | Administrador |
| CU54 | POST | `/api/productos/{id}/desactivar/` | Administrador |

**Filtros de CU50:** `?search=` (nombre o descripción), `?estado=A|I`,
`?ordering=producto`

**Respuesta de ejemplo (CU50):**

```json
{
  "count": 1,
  "results": [
    {
      "id_producto": 1,
      "producto": "Huevo Nº1 (grande)",
      "descripcion": "Huevos de más de 63 gramos",
      "estado": "A",
      "estado_display": "Activo",
      "stock_inicial": 50,
      "stock_recolectado": 100,
      "stock_descartado": 10,
      "stock_actual": 140
    }
  ]
}
```

**Campo `estado` (solo lectura vía `PATCH`):** se incluye en las respuestas
pero modificarlo con `PATCH` no tiene efecto; los cambios de estado solo
ocurren a través de `activar`/`desactivar`.

**Campo `stock_inicial` (editable):** se puede escribir al crear y al
modificar. Es un entero sin signo (`PositiveIntegerField`); un valor negativo
devuelve `400`.

**Campos `stock_recolectado`, `stock_descartado` y `stock_actual` (solo
lectura):** se calculan (ver sección 4). Enviarlos en un `POST`/`PATCH` no tiene
efecto. El listado los obtiene con una sola consulta (anotación en
`get_queryset`), sin una consulta por producto. Solo cuentan las recolecciones y
los descartes de stock en estado Finalizado; los pendientes no suman ni restan.
Como la anotación con `Sum` descarta el orden por defecto del modelo, el listado
fija `order_by("producto")` para que la paginación sea estable.

---

## 6. Tests automatizados

Los tests viven en `backend/productos/tests.py`. Se organizan en ocho clases
independientes; Django crea una base temporaria al principio y la destruye al
terminar.

### Estructura

| Clase | Tests | Qué cubre |
|---|:---:|---|
| `BuscarProductoTests` | 6 | CU50: listado, búsqueda por nombre y descripción, filtros por estado |
| `NuevoProductoTests` | 5 | CU49: alta válida, estado por defecto, descripción opcional, nombre duplicado (400), stock por defecto en 0 |
| `ModificarProductoTests` | 4 | CU52: modificación parcial, inmutabilidad del estado vía `PATCH`, producto inexistente |
| `BorrarProductoTests` | 2 | CU53: borrado físico, producto inexistente |
| `ActivarProductoTests` | 4 | CU51: activación, persistencia, idempotencia (409), producto inexistente |
| `DesactivarProductoTests` | 4 | CU54: desactivación, persistencia, idempotencia (409), producto inexistente |
| `PermisosProductosTests` | 14 | Matriz rol × operación (Admin / Operario / Consulta / sin token) |
| `StockActualProductoTests` | 5 | `stock_inicial` al crear y vía `PATCH`, rechazo de negativos, aislamiento de otros campos, `stock_actual` de solo lectura |
| **Total** | **44** | |

### Cómo correrlos

```bash
cd backend
python manage.py test productos
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
└── productos/
    ├── models.py         Producto
    ├── serializers.py    ProductoSerializer (estado read-only, stock_actual editable)
    ├── views.py          ProductoViewSet con activar/desactivar
    ├── urls.py           router DefaultRouter
    ├── admin.py          ProductoAdmin
    ├── migrations/
    │   ├── 0001_initial.py
    │   ├── 0002_producto_stock_actual.py
    │   └── 0003_rename_stock_actual_producto_stock_inicial.py
    └── tests.py          44 tests en 8 clases
```

### Frontend

```
frontend/src/
├── api/productos.js              listProductos, getProducto, createProducto,
│                                  updateProducto, deleteProducto, activarProducto,
│                                  desactivarProducto
├── pages/ProductosPage.jsx       tarjetas (producto-grid) + panel de detalle
└── components/ProductoFormModal.jsx  formulario: nombre, descripción, stock actual
```

---

## 8. Decisiones de diseño

### 8.1 Reutilización del permiso de Galpones

`LecturaAutenticados_EscrituraAdministrador` ya estaba definido en
`usuarios/permissions.py` para Galpones. Esta feature lo reutiliza sin
duplicarlo: cualquier módulo nuevo con la misma matriz de permisos (lectura
para todos los autenticados, escritura solo Administrador) puede sumarse al
mismo esquema.

### 8.2 Activar/desactivar como acciones POST, no PATCH

Igual que el alta/baja de Galpones, activar y desactivar un producto son
transiciones de estado con nombre, con validación de idempotencia (409) y
un significado de negocio específico — no una edición cualquiera del campo
`estado`. Por eso se exponen como `POST /productos/{id}/activar/` y
`POST /productos/{id}/desactivar/`, y `estado` queda `read_only` en el
serializer.

### 8.3 Tarjetas sin `aspect-ratio` cuadrado

El primer diseño de `ProductosPage` reutilizó la clase `.galpon-card`
(`aspect-ratio:1`), pensada para Galpones porque tiene varias filas de datos
(capacidad, operarios, lote actual). Con Productos, que solo tiene nombre,
descripción corta y stock, esa tarjeta cuadrada quedaba con mucho espacio
vacío. Se creó una clase propia (`.producto-card`, sin `aspect-ratio`
forzado) con el nombre en tipografía grande (21px, peso 800) y un ícono
distintivo, en lugar de adaptar el estilo pensado para otra entidad.

### 8.4 Stock calculado, no guardado

El dominio describe el stock disponible como un valor calculado (recolecciones
menos descartes menos salidas). Primero se agregó `stock_actual` como un campo
manual mientras no existían esos módulos; al construirse Recolecciones se pasó a
calcularlo: el campo guardado se renombró a `stock_inicial` (stock de partida o
ajuste) y el stock que muestra la API es `stock_inicial` más lo recolectado en
recolecciones **finalizadas**.

Se eligió calcularlo en lugar de sumar al finalizar porque así no hay nada que
mantener sincronizado: borrar una recolección finalizada, o cualquier otro
cambio, se refleja solo, y los Descartes ya se restan en el mismo cálculo (las
Salidas se restarán igual cuando existan). Las recolecciones pendientes no
suman: solo la finalización confirma que los huevos están contados. Del mismo
modo, solo los descartes de **stock** finalizados restan.

Los descartes se suman con una subconsulta (`descartes/stock.py`) y no con un
segundo `JOIN`, para no multiplicar las filas del `Sum` de recolecciones.

Dependencia entre apps: `productos` no importa `recolecciones` a nivel de
módulo (es `recolecciones` la que depende de `productos`); el cálculo usa
imports diferidos dentro de `ProductoViewSet.get_queryset` y
`ProductoSerializer`, igual que `galpones` con `lotes`. Los tests que combinan
ambos módulos viven en `recolecciones/tests.py` (`StockDeProductosTests`); los
que combinan Productos con Descartes, en `descartes/tests.py`
(`FinalizarStockTests`). `productos` tampoco importa `descartes` a nivel de
módulo.

### 8.5 Consulta con acceso de solo lectura

A diferencia de Usuarios (exclusivo del Administrador), Productos sí tiene
sentido que lo vea el rol Consulta: es información de catálogo, no de
configuración del sistema. El backend ya permitía la lectura a cualquier
autenticado (mismo permiso que Galpones); solo faltaba habilitar la
visibilidad en el menú y en la ruta del frontend (`roles: ["A", "C"]`).
`ProductosPage` ya ocultaba los botones de escritura según `esAdministrador`,
así que no hizo falta ningún cambio adicional para que Consulta viera el
catálogo sin ninguna acción disponible.

---

## 9. Verificación realizada

**Backend**

- 44 tests en verde; suite completa del proyecto (`galpones`, `lotes`,
  `productos`, `recolecciones`, `usuarios`) en 272/272.
- Los tres roles pueden listar y ver el detalle de productos.
- Operario y Consulta reciben 403 al intentar crear, modificar, borrar o
  cambiar el estado de un producto.
- Sin token, la API responde 401.
- Activar y desactivar devuelven 409 si el producto ya está en el estado
  solicitado.
- Un nombre duplicado devuelve 400.
- Un `stock_inicial` negativo devuelve 400 y no modifica el valor en base.
- `stock_actual` suma lo recolectado en recolecciones finalizadas; las pendientes
  no suman, finalizar por la API lo hace subir y borrar una finalizada lo baja.
- `stock_actual` resta los descartes de stock finalizados; los pendientes y los
  de galpón no restan.

**Frontend**

- El botón "Nuevo producto" y las acciones del panel de detalle (Editar,
  Activar/Desactivar, Eliminar) no aparecen para Operario ni Consulta.
- Consulta ve la sección en el menú y puede navegar a `/app/productos` en
  solo lectura.
- El formulario incluye "Stock inicial / ajuste", con una aclaración de que el
  stock actual suma además lo recolectado.
- Cada tarjeta muestra el stock actual en grande junto con el nombre; el panel
  de detalle desglosa stock actual, stock inicial y recolectado.

---

## 10. Pendientes

- **Salidas:** cuando exista, el stock actual debe restar también las salidas
  (ver sección 8.4). Los descartes ya se restan.
- **Relación con Línea de Recolección:** cada línea de recolección deberá
  referenciar un producto activo. Falta decidir si el borrado de un producto
  (CU53) debe bloquearse cuando tiene líneas asociadas, como ya ocurre con
  los galpones que tienen un lote activo.
