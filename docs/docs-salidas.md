# Salidas de productos — documentación de la feature

**Rama:** `feature/gestion-salidas`
**Casos de uso cubiertos:** CU76 a CU80 (cabecera) y sus líneas (CU81 a CU84)

---

## Casos de uso implementados

Una **salida** registra productos que dejan la granja (por ejemplo, el camión que
se lleva los huevos destinados a la venta). Sigue el patrón **cabecera + líneas**
de Recolecciones, Descartes y Entradas: la salida (cabecera) tiene fecha y
observaciones, y una o más líneas con el producto y la cantidad. A diferencia de
las entradas, **no pertenece a un galpón**: el stock de productos es general.

Las líneas no tienen endpoints propios: se leen y se modifican siempre a través
de la salida a la que pertenecen.

**Efecto sobre el stock:** una salida Pendiente no toca nada. Al **finalizarla**,
la cantidad de cada línea se descuenta del stock del producto. El stock no se
guarda: se calcula (ver *Decisiones de diseño*).

### CU76 – Buscar Avanzado Salidas

**Actor:** cualquier usuario autenticado (Administrador, Operario y Consulta).

Lista las salidas con sus líneas y el usuario que las cargó, de la más reciente a
la más antigua. Se filtra con criterios combinables:

- **Fechas:** `?fecha_desde=AAAA-MM-DD` y `?fecha_hasta=AAAA-MM-DD`, ambas
  inclusivas.
- **Estado:** `?estado=P|F`.
- **Producto:** `?id_producto=` (salidas que incluyen ese producto; una salida
  nunca aparece duplicada).

No hay búsqueda por texto. Una fecha con formato inválido devuelve 400. El
detalle se obtiene con `GET /api/salidas/{id}/`.

### CU77 – Nueva Salida

**Actor:** Administrador, Operario.

Registra una salida con fecha y hora, observaciones opcionales y al menos una
línea. El sistema completa el usuario que la carga (`id_usuario`) y la crea en
estado **Pendiente**. Se rechaza con 400 si:

- la fecha y hora son futuras;
- no hay líneas;
- las observaciones superan los 500 caracteres;
- un producto está repetido en dos líneas, está inactivo o no existe;
- la cantidad es cero, negativa, no es un número entero o supera 1.000.000;
- la cantidad supera el stock disponible del producto.

### CU78 – Modificar Salida

**Actor:** Administrador, Operario.

Modifica la fecha, las observaciones y/o las líneas de una salida **Pendiente**.
Una salida Finalizada no se puede modificar (400, *"Salida finalizada. No se
puede editar."*). Tampoco se pueden cambiar el estado ni el usuario que la cargó.
Las validaciones de líneas son las de Nueva Salida; un producto que ya estaba en
la salida y se dio de baja después se conserva, pero no se puede agregar uno
inactivo nuevo.

### CU79 – Borrar Salida

**Actor:** Administrador, Operario.

Elimina físicamente una salida **Pendiente** y, en cascada, sus líneas. Una salida
Finalizada no se puede eliminar (409): ya descontó stock y borrarla lo dejaría sin
el registro que lo respalda.

### CU80 – Finalizar Salida

**Actor:** Administrador, Operario.

`POST /api/salidas/{id}/finalizar/` pasa la salida de Pendiente (`P`) a Finalizada
(`F`). Antes de hacerlo vuelve a verificar que alcance el stock de cada producto;
si no alcanza devuelve 400 y no cambia nada. Todo ocurre en una transacción, con la
salida y los productos bloqueados, de modo que dos finalizaciones simultáneas no
descuentan dos veces ni dejan el stock en negativo. Si ya estaba finalizada
devuelve 409.

### Líneas de salida (CU81 a CU84)

| Caso de uso | Cómo se hace |
|---|---|
| CU81 Listar líneas de salida | En el campo `lineas` de la salida |
| CU82 Nueva línea de salida | Se agrega al crear o modificar la salida |
| CU83 Modificar línea de salida | Se cambia la cantidad o el producto al modificar la salida |
| CU84 Borrar línea de salida | Se quita al modificar la salida (siempre queda al menos una) |

Cada línea lleva `id_producto` y `cantidad` (entero). La respuesta incluye además
`producto_nombre`.

### Matriz rol × caso de uso

| Caso de uso | Administrador | Operario | Consulta |
|---|:---:|:---:|:---:|
| CU76 Buscar / ver | ✅ | ✅ | ✅ |
| CU77 Nueva | ✅ | ✅ | ❌ |
| CU78 Modificar | ✅ | ✅ | ❌ |
| CU79 Borrar | ✅ | ✅ | ❌ |
| CU80 Finalizar | ✅ | ✅ | ❌ |

Sin token, todas las operaciones devuelven 401.

---

## Modelo de datos

### Campos de `Salida` (tabla `Salidas`)

| Campo | Tipo | Notas |
|---|---|---|
| `id_salida` | AutoField | PK (`idSalida`) |
| `id_usuario` | FK → Usuario | `PROTECT`, nulo; quien la cargó (lo completa el sistema) |
| `fecha` | DateTimeField | No puede ser futura |
| `estado` | CharField(1) | `P` Pendiente (default) / `F` Finalizada |
| `observaciones` | TextField | Opcional, hasta 500 caracteres |

### Campos de `LineaSalida` (tabla `LineasSalida`)

| Campo | Tipo | Notas |
|---|---|---|
| `id_linea_salida` | AutoField | PK |
| `id_salida` | FK → Salida | `CASCADE`; `related_name="lineas"` |
| `id_producto` | FK → Producto | `PROTECT` |
| `cantidad` | PositiveIntegerField | Mayor que 0 |

---

## Decisiones de diseño

### El stock se calcula, no se guarda

El stock actual de un producto es:

```
stock_actual = stock_inicial + stock_recolectado − stock_descartado − stock_salidas
```

- `stock_recolectado`: líneas de recolecciones finalizadas.
- `stock_descartado`: líneas de descartes de categoría Stock finalizados.
- `stock_salidas`: líneas de salidas finalizadas.

Así no hay un número que pueda desincronizarse: borrar o corregir un registro
siempre deja el stock coherente. El listado de productos obtiene `stock_salidas`
con una subconsulta (`anotar_egresado`), sin una consulta por producto y sin
multiplicar la suma de recolecciones.

### Stock verificado dos veces

Al crear o modificar se verifica el stock para avisar temprano; al finalizar se
vuelve a verificar con las filas bloqueadas, porque entre una y otra pudo haber
otra salida o un descarte que consumió el stock. El mensaje nombra la acción:
*"…en stock y se quieren despachar X"*.

### Los finalizados no se borran ni se editan

Igual que en Descartes y Entradas: una salida finalizada ya movió stock y queda
como registro de solo lectura.

### Imports diferidos

`descartes.stock` importa `salidas.stock` para restar lo despachado, y `salidas`
usa `descartes.stock.verificar_stock`. Para evitar dependencias circulares entre
apps, el import en `descartes/stock.py` se hace dentro de la función.

---

## Endpoints

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| GET | `/api/salidas/` | Listar salidas (`?fecha_desde=`, `?fecha_hasta=`, `?estado=`, `?id_producto=`) | autenticado |
| POST | `/api/salidas/` | Crear salida con líneas | Adm. / Operario |
| GET | `/api/salidas/{id}/` | Detalle de salida | autenticado |
| PATCH | `/api/salidas/{id}/` | Modificar salida PENDIENTE | Adm. / Operario |
| DELETE | `/api/salidas/{id}/` | Eliminar salida PENDIENTE | Adm. / Operario |
| POST | `/api/salidas/{id}/finalizar/` | Finalizar y descontar el stock | Adm. / Operario |

### Ejemplo de payload

```json
{
  "fecha": "2026-10-15T09:30:00Z",
  "observaciones": "Retira camión de Distribuidora Norte",
  "lineas": [
    { "id_producto": 1, "cantidad": 1200 },
    { "id_producto": 2, "cantidad": 300 }
  ]
}
```

---

## Interfaz

Pantalla **Salidas** (`/app/salidas`), con el mismo diseño de lista y panel de
detalle que Entradas y Descartes:

- Filtros por fecha desde / hasta, producto y estado, con botón "Limpiar".
- Tabla con fecha, estado, ítems, total de unidades y quién la cargó.
- Formulario de alta y edición: fecha con máximo "ahora", observaciones con
  contador y líneas con el producto (solo activos, con su stock) y la cantidad,
  que no puede superar ese stock.
- Mensajes de validación en español.
- Botones Editar / Finalizar / Eliminar solo para Administrador y Operario y solo
  con la salida Pendiente; la Finalizada se muestra como de solo lectura.
- Al finalizar se recarga el stock de los productos.
- El detalle de **Productos** ahora desglosa también lo descartado y las salidas.

---

### Paginación del listado

`GET /api/salidas/` devuelve los resultados paginados de a **16 registros**
(`?page=N`), con la forma `count`, `next`, `previous` y `results`. Se puede pedir
otro tamaño con `?page_size=` (máximo 100) y los filtros y la búsqueda se aplican
**antes** de paginar. Usa `PaginacionListado` (`backend/config/pagination.py`), la
misma clase que Recolecciones.

La tabla muestra la barra de paginación debajo del listado (`src/pages/SalidasPage.jsx`): "Mostrando X–Y de N", Anterior / Siguiente, números de
página clickeables y selector de elementos por página (la barra se muestra siempre, también con una sola página), que se recuerda en el
navegador (`useTamanoPagina("salidas")`). Al cambiar un filtro o la búsqueda se vuelve
a la página 1, y si al eliminar un registro la página queda vacía se retrocede a
la anterior. El desplegable de productos se carga con `traerTodas`.

Tests: `PaginacionSalidasTests` en `backend/config/tests_pagination.py` (7 tests: 16 por página,
última página con el resto, `page_size`, páginas sin repetidos, página inexistente
→ 404 y filtro aplicado antes de paginar).

## Tests

Se implementaron **72 tests** en `backend/salidas/tests.py`, organizados en 8
clases:

| Clase | Tests | Qué verifica |
|---|:---:|---|
| `BuscarSalidaTests` | 10 | Listar, filtros por estado, producto (sin duplicados) y rango de fechas, fecha inválida, detalle, 404 |
| `NuevaSalidaTests` | 16 | Alta, usuario y estado no tomados del cliente, el stock no cambia hasta finalizar, sin líneas, producto repetido, inactivo o inexistente, cantidad inválida, stock insuficiente, observaciones 500/501 |
| `FechaSalidaTests` | 5 | Fecha futura → 400, fecha pasada válida, no se puede editar a una fecha futura |
| `ModificarSalidaTests` | 12 | Editar observaciones y líneas, agregar y quitar, nunca sin líneas, stock al editar, producto dado de baja conservado, estado y usuario no editables, finalizada → 400, 404 |
| `BorrarSalidaTests` | 3 | Pendiente con cascada a líneas, finalizada → 409, 404 |
| `FinalizarSalidaTests` | 9 | Finalizar, persistencia, baja de stock, doble finalización (409), stock insuficiente sin cambios, varias líneas, edición posterior bloqueada, 404 |
| `StockProductoSalidaTests` | 10 | `stock_salidas` y `stock_actual`, pendientes no restan, fórmula completa con recolecciones y descartes, listado sin inflar sumas, cruce con Descartes |
| `PermisosSalidaTests` | 7 | Administrador y Operario con CRUD completo, Consulta solo lectura (403), sin token (401) |

Ejecutar:

```bash
python manage.py test salidas --verbosity=2
```

---

## Archivos modificados o creados

### Backend

```
backend/salidas/             app nueva: models, serializers, views, urls, stock,
                             admin, tests y migración 0001_initial
backend/config/settings.py   "salidas" en INSTALLED_APPS
backend/config/urls.py       rutas de /api/salidas/
backend/descartes/stock.py   stock_actual_producto resta las salidas
backend/productos/           campo stock_salidas y nuevo stock_actual
```

### Frontend

```
frontend/src/api/salidas.js
frontend/src/components/SalidaFormModal.jsx
frontend/src/pages/SalidasPage.jsx
frontend/src/App.jsx              la ruta /app/salidas deja de ser una vista previa
frontend/src/pages/ProductosPage.jsx   detalle con descartado y salidas
```

---

## Pendientes

- **Borrado de productos con salidas:** las líneas referencian el producto con
  `PROTECT`, así que la base impide borrarlo, pero la vista de productos todavía
  no captura ese error para devolver un 409 con mensaje claro (mismo pendiente que
  con Recolecciones y Descartes).
- **Destino / cliente:** hoy el destino se anota en las observaciones; cuando exista
  un módulo de clientes o ventas podría ser un campo propio.
