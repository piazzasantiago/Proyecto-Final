# Descartes — documentación de la feature

**Rama:** `feature/descartes`
**Casos de uso cubiertos:** CU15 a CU19 (cabecera) y sus líneas (CU20 a CU23)

---

## Casos de uso implementados

Un **descarte** registra algo que se tiró o se perdió en la granja: una gallina
que murió, alimento que se pudrió, huevos rotos, un nidal roto, etc. Siguen el
patrón **cabecera + líneas** de Recolecciones: el descarte (cabecera) tiene una o
más líneas, y cada línea indica qué ítem se descartó, cuánto y por qué motivo.

Las líneas no tienen endpoints propios: se leen y se modifican siempre a través
del descarte al que pertenecen, igual que en Recolecciones.

### Categorías

Cada descarte tiene una **categoría**, que se elige al crearlo y no se puede
cambiar después. Define de dónde sale lo descartado y qué efecto tiene:

| | Galpón (`G`) | Stock (`S`) |
|---|---|---|
| Qué es | Algo que ocurre dentro de un galpón | Baja de lo que ya está almacenado |
| Ejemplos | Gallina muerta o que dejó de producir, alimento servido que se pudrió, nidal roto, huevos rotos encontrados | Huevos ya recolectados que se descartan, materia prima lista para consumir que se vence |
| Galpón | Obligatorio | No lleva (debe quedar vacío) |
| Ítems admitidos | Gallinas de un lote, productos, materias primas | Productos y materias primas |
| Efecto al finalizar | **Estadístico.** No toca el stock. Solo las líneas de gallinas bajan `cantidad_actual` del lote | **Baja el stock actual** de cada producto y materia prima descartados |

### CU15 – Buscar Descarte

**Actor:** cualquier usuario autenticado (Administrador, Operario y Consulta).

Lista los descartes con sus líneas, galpón y usuario que los cargó, ordenados del
más reciente al más antiguo. No hay buscador de texto: se filtra con tres
criterios, que se pueden combinar:

- **Fechas:** `?fecha_desde=AAAA-MM-DD` y `?fecha_hasta=AAAA-MM-DD`, ambas
  inclusivas. El día se toma en el horario local del sistema.
- **Categoría:** `?categoria=G|S`.
- **Estado:** `?estado=P|F`.

También acepta `?id_galpon=` (descartes de un galpón en particular). Una fecha
con formato inválido devuelve 400. El detalle se obtiene con
`GET /api/descartes/{id}/`.

### CU16 – Nuevo Descarte

**Actor:** Administrador, Operario.

Registra un descarte con su categoría, fecha y hora, observaciones opcionales y
al menos una línea. El sistema completa solo el usuario que lo carga
(`id_usuario`) y lo crea en estado **Pendiente**. Se rechaza con 400 si:

- falta la categoría;
- la fecha y hora son futuras;
- no hay líneas;
- las observaciones superan los 500 caracteres;
- una línea no tiene ítem, o tiene más de uno;
- la cantidad es cero o negativa, o el motivo está vacío;
- un producto o gallinas llevan cantidad con decimales (solo las materias primas
  admiten decimales);
- **Categoría Galpón:** falta el galpón, el galpón está inactivo, el lote no
  pertenece a ese galpón, el lote está finalizado, o se quieren descartar más
  gallinas de las que tiene el lote (si el mismo lote aparece en varias líneas,
  se suman);
- **Categoría Stock:** se envía un galpón, se incluye una línea de gallinas, o
  alguna cantidad supera el stock disponible (si el mismo ítem aparece en varias
  líneas, se suman).

### CU17 – Modificar Descarte

**Actor:** Administrador, Operario.

Modifica la fecha, las observaciones y/o las líneas de un descarte **Pendiente**.
Un descarte Finalizado no se puede modificar. La categoría y el galpón no
cambian una vez creado el descarte, y tampoco el usuario que lo cargó (quien
edita no lo reemplaza). Las validaciones de líneas, y las de stock en los
descartes de stock, son las mismas que en CU16.

### CU18 – Borrar Descarte

**Actor:** Administrador, Operario.

Elimina físicamente un descarte **Pendiente** y, en cascada, sus líneas. Un
descarte Finalizado no se puede eliminar (409): ya bajó gallinas del lote o stock,
y borrarlo dejaría esos números sin el registro que los respalda.

### CU19 – Finalizar Descarte

**Actor:** Administrador, Operario.

`POST /api/descartes/{id}/finalizar/` pasa el descarte de Pendiente (`P`) a
Finalizado (`F`) y aplica su efecto:

- **Galpón:** por cada lote con líneas de gallinas, vuelve a verificar que el
  lote no esté finalizado y que alcancen las gallinas (se suman las líneas del
  mismo lote) y resta la cantidad a `cantidad_actual`. Si no alcanzan devuelve
  400 y no cambia nada: el lote nunca se recorta a 0 en silencio. Las líneas de
  productos y materias primas no tocan el stock.
- **Stock:** vuelve a verificar que alcance el stock de cada ítem. Si no alcanza
  devuelve 400 y no cambia nada. Si alcanza, el stock se recalcula solo al quedar
  el descarte Finalizado.

Todo ocurre en una transacción, con la fila bloqueada: dos finalizaciones
simultáneas no descuentan dos veces. Si ya estaba finalizado devuelve 409.

### Líneas de descarte (CU20 a CU23)

Cada línea indica **exactamente uno** de estos ítems, más una cantidad y un
motivo (hasta 200 caracteres):

| Ítem | Campo | Cantidad | Categorías |
|---|---|---|---|
| Materia prima | `id_materia_prima` | Decimal (kg, L, etc.) | Galpón y Stock |
| Producto | `id_producto` | Entera | Galpón y Stock |
| Gallinas de un lote | `id_lote` | Entera | Solo Galpón |

Se listan en el campo `lineas` del descarte, y se agregan, modifican o quitan
enviando el listado completo de `lineas` al crear o editar (la API reemplaza las
líneas existentes por las recibidas). Un descarte no puede quedar sin líneas.

### Matriz rol × caso de uso

Según la matriz de permisos por rol del README:

| Caso de uso | Administrador | Operario | Consulta |
|---|:---:|:---:|:---:|
| CU15 Buscar Descarte | Sí | Sí | Sí |
| CU16 Nuevo Descarte | Sí | Sí | No |
| CU17 Modificar Descarte (Pendiente) | Sí | Sí | No |
| CU18 Borrar Descarte (Pendiente) | Sí | Sí | No |
| CU19 Finalizar Descarte | Sí | Sí | No |
| Líneas (CU20 a CU23) | Sí | Sí | Solo ver |

---

## Modelo de datos

### Campos de `Descarte`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_descarte` | PK | Identificador |
| `categoria` | CHAR(1) | `G` = Galpón, `S` = Stock — default `G` |
| `id_galpon` | FK → Galpon | Galpón del descarte. Nulo en los de categoría Stock |
| `id_usuario` | FK → Usuario | Usuario que cargó el descarte (ver decisión de diseño) |
| `fecha` | DateTimeField | Fecha y hora del descarte |
| `estado` | CHAR(1) | `P` = Pendiente, `F` = Finalizado |
| `observaciones` | TextField | Texto libre, opcional (máx. 500 en la API) |

### Campos de `LineaDescarte`

| Campo | Tipo | Descripción |
|---|---|---|
| `id_linea_descarte` | PK | Identificador |
| `id_descarte` | FK → Descarte | Cabecera a la que pertenece (borrado en cascada) |
| `id_galpon` | FK → Galpon | Galpón (propagado desde la cabecera al crear; nulo en Stock) |
| `id_materia_prima` | FK → MateriaPrima | Ítem descartado (uno de los tres) |
| `id_producto` | FK → Producto | Ítem descartado (uno de los tres) |
| `id_lote` | FK → Lote | Gallinas de ese lote (uno de los tres) |
| `cantidad` | DECIMAL(12,2) | Cantidad descartada |
| `motivo` | CHAR(200) | Por qué se descarta |

La exclusividad de los tres ítems no se fuerza en la base: la valida el
serializer.

---

## Decisiones de diseño

### Dos categorías en lugar de un solo tipo de descarte

La primera versión tenía el galpón siempre obligatorio y todos los descartes
bajaban stock. Pero en la granja hay dos situaciones distintas: lo que pasa
*dentro* de un galpón (una gallina que muere, un nidal roto), que sirve sobre
todo para estadísticas, y lo que se saca del *stock* ya almacenado (huevos ya
recolectados, materias primas listas para consumir). Mezclarlas hacía que un
huevo roto encontrado en el galpón restara stock que nunca se había sumado.

Con la categoría, cada caso tiene su regla: Galpón es estadístico (con la sola
excepción de las gallinas, que sí bajan el lote) y Stock descuenta stock.
Por eso `id_galpon` pasó a ser nulo.

### El stock se calcula, no se guarda

Igual que con las recolecciones, no se guarda ningún "stock actual":

```
producto:       stock_actual = stock_inicial + stock_recolectado − stock_descartado
materia prima:  stock_actual = stock_inicial − stock_descartado
```

`stock_descartado` suma las líneas de descartes de categoría **Stock** y estado
**Finalizado**. Los pendientes no restan (pueden editarse o borrarse) y los de
galpón nunca restan. Así no hay nada que mantener sincronizado.

El cálculo vive en `descartes/stock.py`. El listado de productos y de materias
primas obtiene `stock_descartado` con una **subconsulta** (`anotar_descartado`),
no con un segundo `JOIN`: en productos ya hay un `Sum` sobre las líneas de
recolección, y otro `JOIN` multiplicaría las filas e inflaría ambas sumas. Hay un
test que lo verifica (`test_listado_de_productos_no_infla_las_sumas`). Como
`Sum` descarta el orden por defecto del modelo, el listado de productos fija
`order_by("producto")` para que la paginación sea estable.

Dependencia entre apps: `productos` y `materias_primas` usan imports diferidos
dentro de `get_queryset` y del serializer, porque `descartes` depende de ellas y
no al revés.

### Stock verificado dos veces

Un descarte de stock se valida al **crear/modificar** (para avisar enseguida) y
otra vez al **finalizar**, porque entre una cosa y otra pudo cambiar el stock
(otro descarte finalizado, una recolección borrada). Al revés también se
cuida: no se puede borrar una recolección finalizada si lo recolectado ya se
descartó y el stock quedaría en negativo (409, ver `docs-recolecciones.md`). Así
el stock nunca queda negativo.

### Los finalizados no se borran

Eliminar un descarte finalizado haría "volver" gallinas al lote o stock al
inventario sin un registro que lo justifique. Solo se eliminan los pendientes.
Las gallinas descontadas de un lote no se restituyen automáticamente.

### FK `id_usuario` en `Descarte`

Igual que en Recolecciones, queda registrado quién cargó el descarte. El campo se
inyecta en `perform_create` del ViewSet con el usuario autenticado
(`request.user`); si el cliente envía uno, se ignora. Al modificar, el autor no
cambia. Es `nullable` para los descartes creados antes de esta migración, que
muestran `—`.

Se expone con el mismo `UsuarioResumenSerializer` de Recolecciones (`id_usuario`,
`nombre_completo`, `usuario`) como campo anidado de solo lectura `usuario`. En la
interfaz aparece la columna **"Cargado por"** en la tabla y en el panel de
detalle.

---

## Validaciones del backend

- **Categoría obligatoria** al crear; no se puede cambiar después (400).
- **Galpón:** obligatorio y activo en Galpón; debe estar vacío en Stock.
- **Líneas:** al menos una; cada una con exactamente un ítem, cantidad mayor que
  cero y motivo.
- **Cantidades enteras** para productos y gallinas; decimales solo en materias
  primas.
- **Gallinas:** el lote debe pertenecer al galpón, no estar finalizado y tener al
  menos esa cantidad de gallinas (`cantidad_actual`). Si el mismo lote aparece en
  varias líneas, se suman antes de comparar. Se verifica al crear, al modificar y
  otra vez al finalizar.
- **Stock:** no se puede descartar más de lo que hay; las líneas repetidas del
  mismo ítem se suman antes de comparar.
- **Fecha y hora no futura:** no puede ser posterior al momento actual, al
  crear ni al modificar (HTTP 400). El formulario también la limita al momento
  actual.
- **Observaciones:** máximo 500 caracteres.
- **Descarte finalizado:** no se puede modificar (400), ni eliminar (409), ni
  finalizar de nuevo (409).

---

## Permisos por rol

| Operación | Administrador | Operario | Consulta |
|---|:---:|:---:|:---:|
| Listar / ver detalle (CU15) | ✅ | ✅ | ✅ |
| Crear (CU16) | ✅ | ✅ | ❌ |
| Modificar PENDIENTE (CU17) | ✅ | ✅ | ❌ |
| Finalizar (CU19) | ✅ | ✅ | ❌ |
| Borrar PENDIENTE (CU18) | ✅ | ✅ | ❌ |

Sin token, todos los endpoints devuelven 401. Se usa `EsAdministradorOOperario`
para escribir e `IsAuthenticated` para leer (ver `get_permissions` en
`descartes/views.py`).

---

## Impacto en otros módulos

Los descartes de stock finalizados restan en:

- **Productos** (`stock_actual` y el nuevo campo `stock_descartado`).
- **Materias Primas** (`stock_actual` y `stock_descartado`).

Los descartes de gallinas finalizados restan de `cantidad_actual` del **Lote**.

Al finalizar un descarte de stock, la pantalla de Descartes refresca los
catálogos de productos y materias primas para que los stocks mostrados en el
formulario sean los vigentes.

---

## Endpoints

| CU | Método | Ruta | Descripción | Rol |
|---|---|---|---|---|
| CU15 | GET | `/api/descartes/` | Listar (`?fecha_desde=`, `?fecha_hasta=`, `?categoria=`, `?estado=`, `?id_galpon=`) | autenticado |
| CU15 | GET | `/api/descartes/{id}/` | Detalle | autenticado |
| CU16 | POST | `/api/descartes/` | Crear con líneas | Adm. / Operario |
| CU17 | PUT/PATCH | `/api/descartes/{id}/` | Editar, incluidas las líneas (solo PENDIENTE) | Adm. / Operario |
| CU18 | DELETE | `/api/descartes/{id}/` | Borrar (solo PENDIENTE) | Adm. / Operario |
| CU19 | POST | `/api/descartes/{id}/finalizar/` | Finalizar y aplicar el efecto | Adm. / Operario |

### Ejemplo de payload — descarte de galpón

```json
{
  "categoria": "G",
  "id_galpon": 1,
  "fecha": "2026-08-09T10:00:00Z",
  "observaciones": "Recorrida de la mañana.",
  "lineas": [
    { "id_lote": 3, "cantidad": "2", "motivo": "muerte natural" },
    { "id_producto": 1, "cantidad": "12", "motivo": "huevos rotos en el nidal" },
    { "id_materia_prima": 2, "cantidad": "1.50", "motivo": "balanceado húmedo" }
  ]
}
```

### Ejemplo de payload — descarte de stock

```json
{
  "categoria": "S",
  "fecha": "2026-08-09T10:00:00Z",
  "observaciones": "",
  "lineas": [
    { "id_producto": 1, "cantidad": "30", "motivo": "huevos vencidos" },
    { "id_materia_prima": 2, "cantidad": "5.00", "motivo": "vitaminas vencidas" }
  ]
}
```

No se envían `id_usuario` ni `estado`: la API los completa.

### Ejemplo de respuesta (descarte de stock)

```json
{
  "id_descarte": 12,
  "categoria": "S",
  "categoria_display": "Stock",
  "galpon": null,
  "usuario": {
    "id_usuario": 2,
    "nombre_completo": "Juan Pérez",
    "usuario": "jperez"
  },
  "fecha": "2026-08-09T10:00:00Z",
  "estado": "P",
  "estado_display": "Pendiente",
  "observaciones": "",
  "items_count": 1,
  "lineas": [
    {
      "id_linea_descarte": 31,
      "tipo": "producto",
      "id_producto": 1,
      "producto_nombre": "Huevo Nº1 (grande)",
      "cantidad": "30.00",
      "motivo": "huevos vencidos"
    }
  ]
}
```

(En las líneas se omiten, por brevedad, los campos que valen `null`.)

---

## Interfaz

- **Filtros:** rango de fechas (Desde / Hasta), categoría y estado, con un botón
  "Limpiar". No hay buscador.
- **Tabla:** fecha, categoría, galpón, estado, cantidad de ítems y "Cargado por".
- **Panel de detalle:** datos del descarte, quién lo cargó, observaciones, líneas
  y una nota con el efecto que tiene (o tendrá) en el stock o en el lote.
- **Formulario:** selector de categoría (Galpón / Stock). En Galpón pide el
  galpón y permite gallinas de sus lotes; en Stock muestra el stock disponible de
  cada ítem y limita la cantidad. La categoría y el galpón no se editan.
- **Acciones:** Editar, Finalizar y Eliminar solo sobre descartes pendientes y
  solo para Administrador y Operario. Consulta ve todo sin acciones.

---

## Tests

Se implementaron **101 tests** en `backend/descartes/tests.py`, organizados en 12
clases:

| Clase | Tests | Qué verifica |
|---|:---:|---|
| `BuscarDescarteTests` | 14 | Listar, filtros por categoría, estado, galpón y rango de fechas (inclusivo, invertido, inválido), filtros combinados, `items_count` |
| `NuevoDescarteGalponTests` | 21 | Alta con cada tipo de ítem, usuario registrado y no tomado del cliente, validaciones (sin líneas, sin ítem o con dos, cantidad, galpón faltante o inactivo, categoría faltante, lote de otro galpón o finalizado, gallinas de más, decimales), sin verificación de stock |
| `NuevoDescarteStockTests` | 10 | Alta con producto y materia prima, sin galpón, rechazo con galpón o con lote, stock insuficiente, cantidad igual al stock, líneas repetidas que se suman |
| `FinalizarDescarteTests` | 4 | Finalizar, persistencia, doble finalización (409), bloqueo de edición |
| `FinalizarStockTests` | 8 | El stock de productos y de materias primas baja al finalizar, el pendiente y el de galpón no lo bajan, stock insuficiente al finalizar, listados sin sumas infladas |
| `ModificarDescarteTests` | 7 | Editar observaciones y líneas, el autor no cambia, la categoría no cambia, edición de stock con validación, 404 |
| `EliminarDescarteTests` | 5 | Eliminar pendiente, cascada a líneas, finalizado no se elimina, descarte de stock, 404 |
| `LineasDescarteTests` | 4 | Los tres tipos en un descarte, cantidad negativa, motivo obligatorio, nombres legibles |
| `PermisosDescarteTests` | 14 | Matriz completa por rol, incluidos Operario con CRUD y Consulta solo lectura; sin token → 401 |
| `DescarteLoteTests` | 4 | Finalizar baja `cantidad_actual`, no finaliza si el lote ya no tiene las gallinas (400, sin recortar a 0), el pendiente y los de stock no tocan el lote |
| `GallinasPorLoteAcumuladasTests` | 5 | Un mismo lote en varias líneas se suma (al crear y al modificar), suma exacta válida, dos descartes que juntos superan el lote (el segundo falla al finalizar y queda Pendiente), lote finalizado antes de finalizar |
| `FechaDescarteTests` | 5 | Fecha de mañana o con hora futura → 400 (de galpón y de stock), fecha pasada válida, no se puede editar a una fecha futura |

Ejecutar:

```bash
python manage.py test descartes --verbosity=2
```

---

## Archivos modificados o creados

### Backend

| Archivo | Cambio |
|---|---|
| `descartes/models.py` | Nuevo: modelos `Descarte` y `LineaDescarte` |
| `descartes/migrations/0001_initial.py` | Migración inicial |
| `descartes/migrations/0002_categoria_y_galpon_opcional.py` | Agrega `categoria` y hace opcional `id_galpon` |
| `descartes/migrations/0003_descarte_id_usuario.py` | Agrega FK `id_usuario` |
| `descartes/stock.py` | Nuevo: cálculo del stock descartado y verificación de stock |
| `descartes/serializers.py` | Nuevo: serializers cabecera-líneas y validaciones por categoría |
| `descartes/views.py` | Nuevo: `DescarteViewSet` con filtros, `perform_create` (inyecta `id_usuario`) y acción `/finalizar/` |
| `descartes/admin.py`, `apps.py` | Registro en el panel de administración y configuración de la app |
| `descartes/tests.py` | Nuevo: 101 tests |
| `productos/serializers.py`, `productos/views.py` | Agregan `stock_descartado` y lo restan en `stock_actual`; orden explícito en el listado |
| `materias_primas/serializers.py`, `materias_primas/views.py` | Agregan `stock_descartado` y lo restan en `stock_actual` |
| `recolecciones/tests.py` | Fecha de prueba con zona horaria (elimina un `RuntimeWarning`) |
| `config/settings.py`, `config/urls.py` | Registran la app y sus rutas |

### Frontend

| Archivo | Cambio |
|---|---|
| `src/api/descartes.js` | Nuevo: listar, obtener, crear, modificar, eliminar y finalizar descartes |
| `src/pages/DescartesPage.jsx` | Nuevo: tabla, filtros, panel de detalle y acciones; incluye "Cargado por" |
| `src/components/DescarteFormModal.jsx` | Nuevo: alta y edición con categorías y líneas dinámicas |
| `src/App.jsx` | La ruta `descartes` usa la pantalla real en lugar del mockup |

---

## Pendientes

- **Salidas:** cuando exista el módulo, `stock_actual` de productos deberá restar
  también las salidas (`recolectado − descartado − salidas`).
- **Compras:** `stock_actual` de materias primas deberá sumar las compras.
- **Borrado de productos y materias primas con descartes:** hoy los descartes
  referencian productos y materias primas con `PROTECT`; falta revisar que
  eliminar uno que ya tiene descartes devuelva un mensaje claro en lugar de un
  error.
- **Estadísticas:** los descartes de galpón existen para alimentar los informes
  (CU85 a CU89); falta construir esas vistas.
- El mockup `descartes.html` en `frontend/src/pages/static/raw/` quedó sin uso y
  puede eliminarse.
