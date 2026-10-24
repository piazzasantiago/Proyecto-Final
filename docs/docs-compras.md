# Compras — documentación de la feature

**Rama:** `feature/gestion-compras`
**Casos de uso cubiertos:** buscar, nueva, modificar, borrar y finalizar compra, y
gestión de sus líneas (la numeración CU de este módulo todavía no está confirmada
en esta documentación).

---

## Casos de uso implementados

Una **compra** registra lo que la granja le compra a un proveedor. Sigue el patrón
**cabecera + líneas** de Recolecciones, Descartes, Entradas y Salidas: la compra
(cabecera) pertenece a un proveedor y tiene una o más líneas. Las líneas no tienen
endpoints propios: se leen y modifican siempre a través de su compra.

Hay **dos categorías** de compra, que no se pueden mezclar ni cambiar después de
crearla:

- **Materias primas (`M`):** cada línea indica qué materia prima se compró, la
  cantidad y el precio unitario. La materia prima tiene que existir y estar activa;
  si no existe, se crea primero desde la sección *Materias primas* y después se
  registra la compra. Al **finalizar** la compra, la cantidad suma al stock de cada
  materia prima.
- **Lotes (`L`):** cada línea es un lote de gallinas comprado (cantidad de aves y
  precio por ave). No toca el stock de materias primas. Al **finalizar** la compra,
  el lote queda **esperando ser asignado a un galpón** (ver *Lotes comprados*).

Una compra tiene dos estados: **Pendiente** y **Finalizada**. Mientras está
pendiente se puede editar, finalizar y eliminar. Una compra finalizada ya hizo
efecto: queda de solo lectura y no se puede eliminar.

### Buscar compras

**Actor:** Administrador y Consulta (el Operario no ve la sección).

Lista las compras con proveedor, usuario que las cargó y líneas, de la más
reciente a la más antigua. Se filtran con criterios combinables:

- **Buscador:** `?search=` por **número de factura**.
- **Fechas:** `?fecha_desde=AAAA-MM-DD` y `?fecha_hasta=AAAA-MM-DD`, inclusivas.
- **Proveedor:** `?id_proveedor=`.
- **Categoría:** `?categoria=M|L`.
- **Estado:** `?estado=P|F`.

El detalle se obtiene con `GET /api/compras/{id}/` e incluye `total` (suma de los
subtotales de las líneas) e `items_count`.

### Nueva compra

**Actor:** Administrador.

Registra una compra con proveedor, categoría, tipo (Contado / Cuenta corriente),
número de factura, fecha, observaciones opcionales y al menos una línea. El sistema
completa el usuario que la carga (`id_usuario`, el del token) y la crea en estado
**Pendiente**; ni el usuario ni el estado se toman de lo que envíe el cliente. Se
rechaza con 400 si:

- el proveedor falta o está inactivo;
- la categoría no es `M` ni `L`;
- el número de factura no tiene el formato `0001-00004521` (se acepta sin guion y se
  normaliza) o el proveedor ya tiene otra compra con esa factura;
- la fecha es futura;
- no hay líneas;
- las observaciones superan los 500 caracteres;
- en una compra de materias primas: una línea no tiene materia prima, la materia
  prima está repetida, inactiva o no existe;
- en una compra de lotes: una línea trae materia prima, o la cantidad de aves no es
  un número entero;
- la cantidad o el precio unitario son cero, negativos, tienen más de 2 decimales o
  superan el máximo (1.000.000 de cantidad, 10.000.000 de precio).

### Modificar compra

**Actor:** Administrador.

Solo mientras está Pendiente (una finalizada devuelve 400 con *"Compra finalizada.
No se puede editar."*). Permite cambiar los datos de la cabecera y reemplazar las
líneas. La categoría no se puede cambiar. Si el proveedor o una materia prima de la
compra se dieron de baja después de cargarla, se conservan al editar.

### Borrar compra

**Actor:** Administrador.

Solo mientras está Pendiente: se elimina junto con sus líneas. Una compra
finalizada devuelve **409**.

### Finalizar compra

**Actor:** Administrador.

Pasa la compra a Finalizada dentro de una transacción con bloqueo de fila: finalizar
dos veces devuelve **409** y nunca duplica el efecto.

---

## Lotes comprados y asignación a galpones

Los lotes **ya no se crean "de la nada"**. Un lote de gallinas sale de una compra de
lotes finalizada:

1. Se registra y se **finaliza** una compra de categoría Lotes.
2. En *Lotes de gallinas* aparece un **cartel rojo** junto al botón *Nuevo lote*
   avisando cuántos lotes esperan ser asignados a un galpón.
3. En *Nuevo lote*, antes del galpón, hay un combo **Lotes a asignar** con los lotes
   comprados que todavía no se asignaron. Al elegir uno, la cantidad inicial sale de
   la compra (campo de solo lectura).
4. Si no hay lotes pendientes, el botón *Nuevo lote* queda deshabilitado y la API
   rechaza el alta con 400.

`GET /api/compras/lotes-pendientes/` devuelve la lista (sin paginar) de lotes
comprados sin asignar; es accesible para cualquier usuario autenticado.

En `POST /api/lotes/` el campo **`id_linea_compra`** es ahora obligatorio. Se rechaza
con 400 si falta, si la compra no está finalizada, si no es de lotes o si el lote ya
fue asignado. La cantidad inicial del lote es la comprada (lo que envíe el cliente
en `cantidad_inicial` se ignora) y editar la cantidad inicial de un lote que viene de
una compra devuelve 400. Los lotes cargados antes de que existiera Compras no tienen
compra asociada y siguen editándose como siempre.

---

## Permisos

| Rol | Acceso |
|---|---|
| Administrador | CRUD completo y finalizar |
| Consulta | Solo lectura (403 al escribir) |
| Operario | No ve la sección (403) |

`lotes-pendientes` es la excepción: lo consulta cualquier usuario autenticado
(`IsAuthenticated`).

---

## Decisiones de diseño

- **Precio unitario por línea.** El mockup mostraba el total de la línea como
  "precio". Se guarda el precio **unitario** y se calculan `subtotal` (cantidad ×
  precio) y `total` de la compra al leer, así no hay valores que se desincronicen.
- **Factura única por proveedor.** `UniqueConstraint(id_proveedor, nro_factura)`;
  dos proveedores distintos pueden repetir el número. Formato `PPPP-NNNNNNNN`.
- **Fecha, no fecha y hora.** Una factura tiene fecha; no puede ser futura.
- **Tipo de compra.** Se conserva la columna *Tipo* del mockup (Contado / Cuenta
  corriente).
- **Stock calculado, no guardado.** `stock_actual` de una materia prima es
  `stock_inicial + comprado − descartado − entradas`. `comprado` suma las líneas de
  compras de materias primas **finalizadas** (`compras/stock.py`). Una anotación con
  subconsulta (`anotar_comprado`) evita una consulta por materia prima en el listado.
  Los imports entre apps son diferidos para no crear dependencias circulares.
- **Lote pendiente = línea sin lote.** No se tocó el modelo `Lote`: el "lote
  esperando galpón" es la línea de una compra de lotes finalizada con `id_lote`
  vacío. Al crear el lote, la línea queda apuntando a él (`OneToOneField`, con
  `SET_NULL`: si el lote se elimina, la línea vuelve a quedar pendiente). La
  asignación bloquea la línea (`select_for_update`) para que dos altas simultáneas no
  asignen el mismo lote.
- **Borrados protegidos.** Un proveedor o una materia prima con compras no se puede
  eliminar (`PROTECT`): devuelve **409** con un mensaje que indica darlo de baja. Con
  esto quedó resuelto el pendiente de `ProtectedError` en materias primas.

---

### Paginación del listado

`GET /api/compras/` devuelve los resultados paginados de a **16 registros**
(`?page=N`), con la forma `count`, `next`, `previous` y `results`. Se puede pedir
otro tamaño con `?page_size=` (máximo 100) y los filtros y la búsqueda se aplican
**antes** de paginar. Usa `PaginacionListado` (`backend/config/pagination.py`), la
misma clase que Recolecciones.

La tabla muestra la barra de paginación debajo del listado (`src/pages/ComprasPage.jsx`): "Mostrando X–Y de N", Anterior / Siguiente, números de
página clickeables y selector de elementos por página (la barra se muestra siempre, también con una sola página), que se recuerda en el
navegador (`useTamanoPagina("compras")`). Al cambiar un filtro o la búsqueda se vuelve
a la página 1, y si al eliminar un registro la página queda vacía se retrocede a
la anterior. Los desplegables de proveedores y materias primas se cargan con `traerTodas`.

Tests: `PaginacionComprasTests` en `backend/config/tests_pagination.py` (7 tests: 16 por página,
última página con el resto, `page_size`, páginas sin repetidos, página inexistente
→ 404 y filtro aplicado antes de paginar).

## Tests

Se implementaron **54 tests** en `backend/compras/tests.py` y se actualizó
`backend/lotes/tests.py` (53 tests):

| Clase | Tests | Qué verifica |
|---|:---:|---|
| `ListarCompraTests` | 8 | Listar, búsqueda por factura, filtros por categoría, estado, proveedor y fechas, detalle con líneas y total, orden |
| `NuevaCompraTests` | 17 | Alta de ambas categorías, usuario y estado no tomados del cliente, normalización y formato de factura, factura repetida por proveedor, proveedor inactivo, fecha futura, sin líneas, materia prima repetida / inactiva / faltante, cantidad y precio inválidos, aves no enteras, categoría inválida |
| `ModificarBorrarTests` | 7 | Editar pendiente, edición parcial, finalizada → 400, categoría inmutable, borrar pendiente con cascada, finalizada → 409, 404 |
| `FinalizarCompraTests` | 6 | Finalizar, doble finalización (409), pendiente no suma stock, finalizada suma, stock calculado, las compras de lotes no tocan el stock |
| `LotesPendientesTests` | 6 | Lista vacía, pendiente no aparece, finalizada sí, materias primas no, asignado no, vuelve si se borra el lote |
| `RelacionesTests` | 3 | Proveedor y materia prima con compras → 409; sin compras se eliminan |
| `PermisosComprasTests` | 7 | Sin token 401, Administrador crea, Consulta lee y no escribe, Operario sin acceso (pero sí a `lotes-pendientes`) |

En Lotes se agregaron 4 tests (cantidad inicial desde la compra, alta sin lote
comprado, vínculo de la línea, lote no disponible / ya asignado) y se reemplazó el de
cantidad inicial en cero. Los helpers `payload_lote` y `crear_lote_comprado` crean la
compra finalizada necesaria.

Ejecutar:

```bash
python manage.py test compras lotes --verbosity=2
```

> La base de tests de CI es PostgreSQL; el bloqueo `select_for_update` solo tiene
> efecto real allí.

---

## Archivos modificados o creados

### Backend

```
backend/compras/                app nueva: models, serializers, views, urls, stock,
                                admin, tests y migración 0001_initial
backend/config/settings.py      "compras" en INSTALLED_APPS
backend/config/urls.py          rutas de /api/compras/
backend/lotes/                  el alta exige id_linea_compra; cantidad inicial desde
                                la compra; campo de lectura "compra"; tests
backend/materias_primas/        campo stock_compras, nuevo stock_actual y 409 al borrar
backend/descartes/stock.py      stock_actual_materia_prima suma las compras
```

### Frontend

```
frontend/src/api/compras.js
frontend/src/components/CompraFormModal.jsx
frontend/src/pages/ComprasPage.jsx
frontend/src/pages/LotesPage.jsx            cartel rojo y botón Nuevo lote condicionado
frontend/src/components/LoteFormModal.jsx   combo "Lotes a asignar"
frontend/src/pages/MateriaPrimasPage.jsx    "Comprado" en el detalle
frontend/src/App.jsx                        /app/compras deja de ser una vista previa
```

La migración se aplica con `python manage.py migrate`.

---

## Pendientes

- Mostrar las compras recientes de cada proveedor y de cada materia prima.
- El archivo `frontend/src/pages/static/raw/compras.html` (el mockup) ya no se usa y
  puede borrarse.
- Confirmar la numeración de casos de uso de Compras y completarla en esta
  documentación y en el README.
- Informes e indicadores productivos.
