# Compras — documentación de la feature

**Rama:** `feature/gestion-compras`
**Casos de uso cubiertos:** CU61 a CU65 (cabecera) y sus líneas (CU66 a CU69)

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

### CU61 – Buscar Avanzado Compras

**Actor:** Administrador y Consulta (el Operario no ve la sección).

Lista las compras con proveedor, usuario que las cargó y líneas, de la más
reciente a la más antigua. Se filtran con criterios combinables:

- **Buscador:** `?search=` por **número de comprobante** (`12` o `00000012`; busca por los dígitos, sin importar los ceros a la izquierda).
- **Fechas:** `?fecha_desde=AAAA-MM-DD` y `?fecha_hasta=AAAA-MM-DD`, inclusivas.
- **Proveedor:** `?id_proveedor=`. Con `&page_size=4` alimenta "Compras recientes" del detalle del proveedor.
- **Materia prima:** `?id_materia_prima=`, compras que la incluyen en alguna línea (sin repetir la compra). Alimenta "Compras recientes" del detalle de la materia prima.
- **Categoría:** `?categoria=M|L`.
- **Estado:** `?estado=P|F`.

El detalle se obtiene con `GET /api/compras/{id}/` e incluye `total` (suma de los
subtotales de las líneas) e `items_count`.

### CU62 – Nueva Compra

**Actor:** Administrador.

Registra una compra con proveedor, categoría, forma de pago (`tipo`: Contado `C`,
Cuenta corriente `X`, Débito `D`, Crédito `R` u Otro `O`), fecha, observaciones
opcionales y al menos una línea. El sistema completa el usuario que la carga
(`id_usuario`, el del token), la crea en estado **Pendiente** y le asigna el
**número de comprobante** (`nro_comprobante`, autoincremental: el id de la compra con
8 dígitos, p. ej. `00000012`); ni el usuario, ni el estado, ni el comprobante se
toman de lo que envíe el cliente, y el comprobante tampoco se puede editar después.
La cabecera y sus líneas se guardan en **una sola transacción**: si algo falla, no
queda una compra sin líneas. Se rechaza con 400 si:

- el proveedor falta o está inactivo;
- la categoría no es `M` ni `L`;
- la forma de pago no es una de las cinco opciones;
- la fecha es futura;
- no hay líneas;
- las observaciones superan los 500 caracteres;
- en una compra de materias primas: una línea no tiene materia prima, la materia
  prima está repetida, inactiva o no existe;
- en una compra de lotes: una línea trae materia prima, o la cantidad de aves no es
  un número entero;
- la cantidad o el precio unitario son cero, negativos, tienen más de 2 decimales o
  superan el máximo (1.000.000 de cantidad, 10.000.000 de precio).

#### Formulario de la compra (frontend)

- **N° de comprobante:** campo de solo lectura. Al crear muestra el número con el que
  se guardaría la compra (lo pide a `GET /api/compras/proximo-comprobante/`; si no
  puede, dice "Se asigna al guardar"); al editar muestra el número de la compra.
  Es una estimación: si otra persona guarda una compra antes, el número final cambia.
- **Agregar proveedor:** botón junto al desplegable de proveedor. Abre el alta de un
  proveedor encima de la compra, sin cerrarla, y al guardarlo queda elegido.
- **Forma de pago:** desplegable con Contado, Cuenta corriente, Débito, Crédito y Otro.
- **Agregar materia prima:** en las compras de materias primas, el botón abre el
  formulario de alta de una materia prima **encima de la compra**, sin cerrarla, para
  no perder lo ya cargado. Al guardarla, la materia prima queda disponible en los
  desplegables y elegida en la primera línea sin materia prima (o en una línea nueva).
  El botón que suma una fila a la tabla se llama "Agregar línea".

### CU63 – Modificar Compra

**Actor:** Administrador.

Solo mientras está Pendiente (una finalizada devuelve 400 con *"Compra finalizada.
No se puede editar."*). Permite cambiar los datos de la cabecera y reemplazar las
líneas. La categoría no se puede cambiar. Si el proveedor o una materia prima de la
compra se dieron de baja después de cargarla, se conservan al editar.

### CU64 – Borrar Compra

**Actor:** Administrador.

Solo mientras está Pendiente: se elimina junto con sus líneas. Una compra
finalizada devuelve **409**.

### CU65 – Finalizar Compra

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

### Líneas de compra (CU66 a CU69)

| Caso de uso | Cómo se hace |
|---|---|
| CU66 Listar líneas de compra | En el campo `lineas` de la compra |
| CU67 Nueva línea de compra | Se agrega al crear o modificar la compra |
| CU68 Modificar línea de compra | Se cambia la cantidad, el precio o la materia prima al modificar la compra |
| CU69 Borrar línea de compra | Se quita al modificar la compra (siempre queda al menos una) |

---

## Permisos

| Rol | Acceso |
|---|---|
| Administrador | CRUD completo y finalizar |
| Consulta | Solo lectura (403 al escribir) |
| Operario | No ve la sección (403) |

### Matriz rol × caso de uso

| Caso de uso | Administrador | Consulta | Operario |
|---|:---:|:---:|:---:|
| CU61 Buscar / ver | ✅ | ✅ | ❌ |
| CU62 Nueva | ✅ | ❌ | ❌ |
| CU63 Modificar | ✅ | ❌ | ❌ |
| CU64 Borrar | ✅ | ❌ | ❌ |
| CU65 Finalizar | ✅ | ❌ | ❌ |
| CU66 Listar líneas | ✅ | ✅ | ❌ |
| CU67 a CU69 Nueva, modificar y borrar línea | ✅ | ❌ | ❌ |

`lotes-pendientes` es la excepción: lo consulta cualquier usuario autenticado
(`IsAuthenticated`).

`GET /api/compras/proximo-comprobante/` devuelve `{"nro_comprobante": "00000054"}`:
el número que recibiría la próxima compra. Es el siguiente valor del contador
autoincremental de la base (`Compra.proximo_nro_comprobante()`), no "el mayor + 1":
el número de una compra borrada no se reutiliza. Lo leen Administrador y Consulta
(el Operario no ve Compras). Se probó en SQLite y en PostgreSQL.

---

## Decisiones de diseño

- **Precio unitario por línea.** El mockup mostraba el total de la línea como
  "precio". Se guarda el precio **unitario** y se calculan `subtotal` (cantidad ×
  precio) y `total` de la compra al leer, así no hay valores que se desincronicen.
- **Comprobante autoincremental.** Antes se cargaba a mano el número de factura del
  proveedor (con unicidad por proveedor). Ahora el comprobante es general (no solo
  facturas) y lo genera el sistema: es una propiedad calculada del `id_compra`
  (`nro_comprobante`, 8 dígitos), por lo que no se puede editar ni repetir. La
  migración `0002` elimina la columna `nroFactura` y su restricción de unicidad: los
  números de factura que hubiera cargados se pierden.
- **Atomicidad.** `CompraSerializer.create` y `update` envuelven la cabecera y las
  líneas en `transaction.atomic()`. En la edición las líneas se reemplazan (se
  borran y se vuelven a crear): sin la transacción, una falla a mitad de camino
  dejaba la compra sin líneas.
- **Fecha, no fecha y hora.** Una compra tiene fecha; no puede ser futura.
- **Forma de pago.** La columna *Tipo* del mockup pasó a admitir Contado, Cuenta
  corriente, Débito, Crédito y Otro (códigos `C`, `X`, `D`, `R`, `O`). La etiqueta en
  pantalla es "Forma de pago".
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

Se implementaron **68 tests** en `backend/compras/tests.py` y se actualizó
`backend/lotes/tests.py` (53 tests):

| Clase | Tests | Qué verifica |
|---|:---:|---|
| `ListarCompraTests` | 9 | Listar, búsqueda por comprobante (y sin dígitos), filtros por categoría, estado, proveedor y fechas, detalle con líneas y total, orden |
| `NuevaCompraTests` | 20 | Alta de ambas categorías, usuario y estado no tomados del cliente, comprobante generado por el sistema, no enviable y correlativo, formas de pago (las cinco) y una inválida, proveedor inactivo, fecha futura, sin líneas, materia prima repetida / inactiva / faltante, cantidad y precio inválidos, aves no enteras, categoría inválida |
| `ModificarBorrarTests` | 8 | Editar pendiente, edición parcial, comprobante no editable, finalizada → 400, categoría inmutable, borrar pendiente con cascada, finalizada → 409, 404 |
| `AtomicidadTests` | 3 | Si falla el alta no queda compra ni líneas; si falla la edición se conservan las líneas originales; alta exitosa con varias líneas |
| `ProximoComprobanteTests` | 6 | Número de 8 dígitos, coincide con el de la compra que se guarda, avanza con cada compra, no reutiliza el de una compra borrada, permisos (Consulta sí, Operario 403, sin token 401) |
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
                                admin, tests y migraciones 0001_initial y
                                0002_comprobante_y_tipos_de_pago
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
- Informes e indicadores productivos.
