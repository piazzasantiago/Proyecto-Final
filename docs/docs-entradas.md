# Entradas a galpones — documentación de la feature

**Rama:** `feature/gestion-entradas`
**Casos de uso cubiertos:** CU33 a CU37 (cabecera) y sus líneas (CU38 a CU41)

---

## Casos de uso implementados

Una **entrada** registra materias primas que se retiran del stock de la granja y
pasan a un galpón (por ejemplo, el balanceado que se carga en los comederos o la
cama que se repone). Sigue el patrón **cabecera + líneas** de Recolecciones y
Descartes: la entrada (cabecera) pertenece a un galpón y tiene una o más líneas,
y cada línea indica qué materia prima ingresa y en qué cantidad.

Las líneas no tienen endpoints propios: se leen y se modifican siempre a través
de la entrada a la que pertenecen.

**Efecto sobre el stock:** una entrada Pendiente no toca nada. Al
**finalizarla**, la cantidad de cada línea se descuenta del stock de la materia
prima. El stock no se guarda: se calcula (ver *Decisiones de diseño*).

### CU33 – Buscar Entrada (avanzado)

**Actor:** cualquier usuario autenticado (Administrador, Operario y Consulta).

Lista las entradas con sus líneas, galpón y usuario que las cargó, ordenadas de
la más reciente a la más antigua. Se filtra con criterios combinables:

- **Fechas:** `?fecha_desde=AAAA-MM-DD` y `?fecha_hasta=AAAA-MM-DD`, ambas
  inclusivas.
- **Estado:** `?estado=P|F`.
- **Galpón:** `?id_galpon=`.
- **Materia prima:** `?id_materia_prima=` (entradas que incluyen esa materia
  prima; una entrada nunca aparece duplicada).

Una fecha con formato inválido devuelve 400. El detalle se obtiene con
`GET /api/entradas/{id}/`.

### CU35 – Nueva Entrada

**Actor:** Administrador, Operario.

Registra una entrada con galpón, fecha y hora, observaciones opcionales y al
menos una línea. El sistema completa el usuario que la carga (`id_usuario`) y la
crea en estado **Pendiente**. Se rechaza con 400 si:

- falta el galpón o está inactivo;
- la fecha y hora son futuras;
- no hay líneas;
- las observaciones superan los 500 caracteres;
- una materia prima está repetida en dos líneas, está inactiva o no existe;
- la cantidad es cero, negativa, no es un número, tiene más de 2 decimales o
  supera 1.000.000;
- la cantidad supera el stock disponible de la materia prima.

### CU36 – Modificar Entrada

**Actor:** Administrador, Operario.

Modifica la fecha, las observaciones y/o las líneas de una entrada **Pendiente**.
Una entrada Finalizada no se puede modificar (400, *"Entrada finalizada. No se
puede editar."*). El galpón no se puede cambiar una vez creada la entrada, y
tampoco el estado ni el usuario que la cargó. Las validaciones de líneas son las
de CU35; una materia prima que ya estaba en la entrada y se dio de baja después
se conserva, pero no se puede agregar una inactiva nueva.

### CU34 – Borrar Entrada

**Actor:** Administrador, Operario.

Elimina físicamente una entrada **Pendiente** y, en cascada, sus líneas. Una
entrada Finalizada no se puede eliminar (409): ya descontó stock y borrarla lo
dejaría sin el registro que lo respalda.

### CU37 – Finalizar Entrada

**Actor:** Administrador, Operario.

`POST /api/entradas/{id}/finalizar/` pasa la entrada de Pendiente (`P`) a
Finalizada (`F`). Antes de hacerlo vuelve a verificar que alcance el stock de cada
materia prima; si no alcanza devuelve 400 y no cambia nada. Todo ocurre en una
transacción, con la entrada y las materias primas bloqueadas, de modo que dos
finalizaciones simultáneas no descuentan dos veces ni dejan el stock en negativo.
Si ya estaba finalizada devuelve 409.

### Líneas de entrada (CU38 a CU41)

| Caso de uso | Cómo se hace |
|---|---|
| CU38 Listar líneas | En el campo `lineas` de la entrada |
| CU39 Nueva línea | Se agrega al crear o modificar la entrada |
| CU40 Modificar línea | Se cambia la cantidad o la materia prima al modificar la entrada |
| CU41 Borrar línea | Se quita al modificar la entrada (siempre queda al menos una) |

Cada línea lleva `id_materia_prima` y `cantidad` (decimal, 2 decimales). La
respuesta incluye además `materia_prima_nombre` y `materia_prima_unidad`.

### Matriz rol × caso de uso

| Caso de uso | Administrador | Operario | Consulta |
|---|:---:|:---:|:---:|
| CU33 Buscar / ver | ✅ | ✅ | ✅ |
| CU35 Nueva | ✅ | ✅ | ❌ |
| CU36 Modificar | ✅ | ✅ | ❌ |
| CU34 Borrar | ✅ | ✅ | ❌ |
| CU37 Finalizar | ✅ | ✅ | ❌ |

Sin token, todas las operaciones devuelven 401.

---

## Modelo de datos

### Campos de `Entrada` (tabla `Entradas`)

| Campo | Tipo | Notas |
|---|---|---|
| `id_entrada` | AutoField | PK (`idEntrada`) |
| `id_galpon` | FK → Galpon | `PROTECT`; obligatorio, inmutable |
| `id_usuario` | FK → Usuario | `PROTECT`, nulo; quien la cargó (lo completa el sistema) |
| `fecha` | DateTimeField | No puede ser futura |
| `estado` | CharField(1) | `P` Pendiente (default) / `F` Finalizada |
| `observaciones` | TextField | Opcional, hasta 500 caracteres |

### Campos de `LineaEntrada` (tabla `LineasEntrada`)

| Campo | Tipo | Notas |
|---|---|---|
| `id_linea_entrada` | AutoField | PK |
| `id_entrada` | FK → Entrada | `CASCADE`; `related_name="lineas"` |
| `id_materia_prima` | FK → MateriaPrima | `PROTECT` |
| `cantidad` | Decimal(12,2) | Mayor que 0 |

---

## Decisiones de diseño

### El stock se calcula, no se guarda

El stock actual de una materia prima es:

```
stock_actual = stock_inicial − stock_descartado − stock_entradas
```

- `stock_descartado`: líneas de descartes de categoría Stock finalizados.
- `stock_entradas`: líneas de entradas a galpones finalizadas.

Así no hay un número que pueda desincronizarse: borrar o corregir un registro
siempre deja el stock coherente. Cuando exista Compras se le sumará
`+ compras`. El listado de materias primas obtiene `stock_entradas` con una
subconsulta (`anotar_ingresado`), sin una consulta por materia prima.

### Stock verificado dos veces

Al crear o modificar se verifica el stock para avisar temprano; al finalizar se
vuelve a verificar con las filas bloqueadas, porque entre una y otra pudo haber
otra entrada o un descarte que consumió el stock. Como el stock descontado por
descartes y entradas se resta del mismo total, ninguna de las dos operaciones
puede dejarlo en negativo. El mensaje nombra la acción: *"…en stock y se quieren
ingresar X"* (en Descartes: *"…se quieren descartar X"*).

### Los finalizados no se borran ni se editan

Igual que en Descartes: una entrada finalizada ya movió stock y queda como
registro de solo lectura.

### Una entrada, un galpón

Una entrada pertenece a un único galpón, que no cambia después de creada. Si se
cargó mal, se elimina (mientras esté Pendiente) y se crea otra.

### Imports diferidos

`entradas` importa `descartes` (resúmenes y verificación de stock) y
`descartes.stock` importa `entradas.stock` para sumar lo ingresado. Para evitar
dependencias circulares entre apps, esos imports se hacen dentro de las
funciones.

---

## Endpoints

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| GET | `/api/entradas/` | Listar entradas (`?fecha_desde=`, `?fecha_hasta=`, `?estado=`, `?id_galpon=`, `?id_materia_prima=`) | autenticado |
| POST | `/api/entradas/` | Crear entrada con líneas | Adm. / Operario |
| GET | `/api/entradas/{id}/` | Detalle de entrada | autenticado |
| PATCH | `/api/entradas/{id}/` | Modificar entrada PENDIENTE | Adm. / Operario |
| DELETE | `/api/entradas/{id}/` | Eliminar entrada PENDIENTE | Adm. / Operario |
| POST | `/api/entradas/{id}/finalizar/` | Finalizar y descontar el stock | Adm. / Operario |

### Ejemplo de payload

```json
{
  "id_galpon": 1,
  "fecha": "2026-08-09T10:00:00Z",
  "observaciones": "Carga semanal de comederos",
  "lineas": [
    { "id_materia_prima": 3, "cantidad": "120.00" },
    { "id_materia_prima": 7, "cantidad": "2.50" }
  ]
}
```

---

## Interfaz

Pantalla **Entradas** (`/app/entradas`), con el mismo diseño de lista y panel de
detalle que Descartes:

- Filtros por fechas, galpón, materia prima y estado.
- Formulario de alta y edición: galpón (solo activos; bloqueado al editar), fecha
  con máximo "ahora", observaciones con contador y líneas con la materia prima, su
  unidad y el stock disponible. La cantidad no puede superar ese stock.
- Mensajes de validación en español.
- Botones Editar / Finalizar / Eliminar solo para Administrador y Operario y solo
  con la entrada Pendiente; la Finalizada se muestra como de solo lectura.
- Al finalizar se recarga el stock de las materias primas.

---

## Tests

Se implementaron **65 tests** en `backend/entradas/tests.py`, organizados en 8
clases:

| Clase | Tests | Qué verifica |
|---|:---:|---|
| `BuscarEntradaTests` | 8 | Listar, filtros por galpón, estado, materia prima (sin duplicados) y rango de fechas, fecha inválida, detalle, 404 |
| `NuevaEntradaTests` | 17 | Alta, usuario y estado no tomados del cliente, el stock no cambia hasta finalizar, galpón faltante o inactivo, sin líneas, materia prima repetida, inactiva o inexistente, cantidad inválida, decimales, enorme, stock insuficiente, observaciones 500/501 |
| `FechaEntradaTests` | 4 | Fecha de mañana u hora futura → 400, fecha pasada válida, no se puede editar a una fecha futura |
| `ModificarEntradaTests` | 13 | Editar observaciones y líneas, agregar y quitar, nunca sin líneas, stock al editar, materia prima dada de baja conservada, galpón inmutable, estado y usuario no editables, finalizada → 400, 404 |
| `BorrarEntradaTests` | 3 | Pendiente con cascada a líneas, finalizada → 409, 404 |
| `FinalizarEntradaTests` | 9 | Finalizar, persistencia, baja de stock, doble finalización (409, sin descontar dos veces), stock insuficiente sin cambios, varias líneas, edición posterior bloqueada, 404 |
| `StockMateriaPrimaEntradaTests` | 8 | `stock_entradas` y `stock_actual`, pendientes no restan, entradas y descartes juntos, varias entradas, listado, cruce con Descartes en ambos sentidos |
| `PermisosEntradaTests` | 3 | Administrador y Operario con CRUD completo, Consulta solo lectura (403), sin token (401) |

Ejecutar:

```bash
python manage.py test entradas --verbosity=2
```

---

## Archivos modificados o creados

### Backend

```
backend/entradas/            app nueva: models, serializers, views, urls, stock,
                             admin, tests y migración 0001_initial
backend/config/settings.py   "entradas" en INSTALLED_APPS
backend/config/urls.py       rutas de /api/entradas/
backend/descartes/stock.py   stock_actual_materia_prima resta las entradas;
                             verificar_stock recibe la acción (descartar / ingresar)
backend/materias_primas/     campo stock_entradas y nuevo stock_actual
```

### Frontend

```
frontend/src/api/entradas.js
frontend/src/components/EntradaFormModal.jsx
frontend/src/pages/EntradasPage.jsx
frontend/src/App.jsx          la ruta /app/entradas deja de ser una vista previa
```

---

## Pendientes

- **Borrado de materias primas y galpones con entradas:** las líneas referencian la
  materia prima y el galpón con `PROTECT`, así que la base impide borrarlos, pero
  la vista de materias primas todavía no captura ese error para devolver un 409
  con mensaje claro (mismo pendiente que con Descartes y Recolecciones).
- **Compras:** cuando exista, `stock_actual` de materias primas sumará lo comprado.
