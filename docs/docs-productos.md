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
- Campo `stock_actual`: carga manual del stock disponible, editable por el
  Administrador.
- Acceso de solo lectura para el rol Consulta.
- Tests automatizados del módulo (43 tests en 8 clases).
- Interfaz React con tarjetas compactas y panel de detalle; botones de acción
  visibles solo para el rol Administrador.

### Qué no incluye

- El cálculo automático del stock a partir de recolecciones y salidas. La
  Educción de requisitos describe el stock disponible como "recolecciones
  menos salidas", pero ninguno de esos dos módulos existe todavía. Mientras
  tanto, `stock_actual` es un campo que carga el Administrador a mano (ver
  sección 10, Pendientes).
- La asignación de un producto a una línea de recolección. Eso se modela en
  `feature/gestion-recolecciones`, que consumirá los productos activos de
  este módulo.

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
| `stock_actual` | INTEGER | Obligatorio ≥ 0 — default 0 |

**Propiedad calculada (no es columna):**

- `estado_display` — texto legible del estado (`"Activo"` / `"Inactivo"`),
  incluido en todas las respuestas de la API.

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
      "stock_actual": 150
    }
  ]
}
```

**Campo `estado` (solo lectura vía `PATCH`):** se incluye en las respuestas
pero modificarlo con `PATCH` no tiene efecto; los cambios de estado solo
ocurren a través de `activar`/`desactivar`.

**Campo `stock_actual` (editable):** a diferencia de `estado`, se puede
escribir tanto al crear como al modificar. Es un entero sin signo
(`PositiveIntegerField`); un valor negativo devuelve `400`.

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
| `StockActualProductoTests` | 4 | Carga de stock al crear, modificación vía `PATCH`, rechazo de valores negativos, aislamiento de otros campos |
| **Total** | **43** | |

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
    │   └── 0002_producto_stock_actual.py
    └── tests.py          43 tests en 8 clases
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

### 8.4 `stock_actual` como carga manual

El dominio describe el stock disponible como un valor calculado
(recolecciones acumuladas menos salidas), pero ninguno de esos dos módulos
existe todavía. En lugar de esperar a tenerlos para mostrar algo en esta
pantalla, se agregó `stock_actual` como un campo más que el Administrador
edita a mano, dejando aclarado en el modelo y en la vista que es temporal
(ver sección 10, Pendientes).

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

- 43 tests en verde; suite completa del proyecto (`galpones`, `lotes`,
  `productos`, `usuarios`) en 197/197.
- Los tres roles pueden listar y ver el detalle de productos.
- Operario y Consulta reciben 403 al intentar crear, modificar, borrar o
  cambiar el estado de un producto.
- Sin token, la API responde 401.
- Activar y desactivar devuelven 409 si el producto ya está en el estado
  solicitado.
- Un nombre duplicado devuelve 400.
- Un `stock_actual` negativo devuelve 400 y no modifica el valor en base.

**Frontend**

- El botón "Nuevo producto" y las acciones del panel de detalle (Editar,
  Activar/Desactivar, Eliminar) no aparecen para Operario ni Consulta.
- Consulta ve la sección en el menú y puede navegar a `/app/productos` en
  solo lectura.
- El formulario incluye el campo de stock con una aclaración de que es
  carga manual.
- Cada tarjeta muestra el stock actual en grande junto con el nombre.

---

## 10. Pendientes

- **Cálculo automático de stock:** cuando existan `feature/gestion-recolecciones`
  y la sección de Salidas, `stock_actual` debería calcularse como
  recolecciones acumuladas menos salidas, en lugar de (o además de) la
  carga manual actual.
- **Relación con Línea de Recolección:** cada línea de recolección deberá
  referenciar un producto activo. Falta decidir si el borrado de un producto
  (CU53) debe bloquearse cuando tiene líneas asociadas, como ya ocurre con
  los galpones que tienen un lote activo.
