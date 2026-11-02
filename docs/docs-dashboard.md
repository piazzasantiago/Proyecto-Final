# Panel principal y alertas — documentación de la feature

**Rama:** `feat/dashboard`
**Casos de uso cubiertos:** pendientes de numeración (el Dashboard no tiene
número de CU asignado todavía).

El Dashboard deja de ser una vista previa estática y pasa a mostrar datos
reales. Resume en una sola pantalla cómo viene el día: lo recolectado, la
postura, los galpones en producción, las **alertas** de los lotes, la producción
de la última semana y el stock de productos.

Junto con la pantalla se agrega el módulo de **alertas**, que es lo único de
esta feature con modelos y migraciones propias.

---

## 1. Alcance

### Qué incluye

- Pantalla `/app/dashboard` con datos reales, en una sola petición.
- Cuatro indicadores del día: huevos recolectados, postura promedio, galpones en
  producción y alertas activas; los tres primeros comparados contra ayer.
- Gráfico de barras con la producción de los últimos 7 días.
- Tarjeta de alertas recientes (pendientes y las resueltas de la última semana).
- Stock actual de productos con el reparto en un anillo.
- Accesos directos que abren el formulario de alta de la sección
  correspondiente, según el rol.
- Módulo de alertas: tablas `TiposAlerta` y `Alertas`, cuatro reglas,
  generación y resolución automáticas, y API de solo lectura.
- 53 tests automatizados.

### Qué no incluye

- Pantalla propia de alertas (hoy se ven en el panel; el endpoint
  `/api/alertas/` ya existe para cuando se agregue).
- Resolución manual de una alerta: las abre y las cierra el sistema.
- Alertas de stock de materias primas: el modelo relacional ata cada alerta a un
  lote.
- Tutoriales de uso de cada sección (quedan para la feature siguiente).

---

## 2. La pantalla

**Actor:** Administrador, Operario y Consulta (todos entran al panel).

| Bloque | Qué muestra |
|--------|-------------|
| Encabezado | Fecha de hoy en palabras. Al Operario le aclara que ve sus galpones asignados |
| Huevos recolectados hoy | Huevos de recolecciones finalizadas de hoy, y la variación contra ayer |
| Postura promedio de hoy | Postura del día; la variación va en **puntos** (de 70 % a 72 % son 2 puntos, no un 2,8 % más) |
| Galpones en producción | Galpones activos con un lote en producción, sobre el total de galpones activos |
| Alertas activas | Alertas pendientes; en verde cuando no hay ninguna |
| Producción — últimos 7 días | Una barra por día, la de hoy en dorado. El enlace al informe completo solo lo ven Administrador y Consulta |
| Accesos directos | *Nueva recolección* y *Registrar descarte* (Administrador y Operario), *Nueva compra* (solo Administrador) |
| Alertas recientes | Hasta 6 alertas: primero las pendientes, más graves y más nuevas arriba |
| Stock actual de productos | Una tarjeta por producto y un anillo con el reparto del stock total |

Cuando todavía no hay datos, cada bloque lo dice en lugar de mostrar ceros
sueltos ("Todavía no hay recolecciones finalizadas en los últimos siete días").

---

## 3. Las alertas

Una alerta avisa que un lote está en una situación que conviene mirar. **No la
carga nadie**: el sistema evalúa las reglas y mantiene la tabla al día.

### Tipos y reglas

| Tipo | Severidad | Cuándo se genera |
|------|:---:|------------------|
| Postura baja | Alta | Un lote en producción cuyo último día con recolección quedó por debajo del **70 %** de postura |
| Mortandad alta | Alta | Los descartes de gallinas del lote en los últimos 7 días superan el **1 %** del plantel inicial |
| Plan de transición por vencer | Media | A un lote en transición le quedan **3 días o menos** de plan |
| Sin recolecciones recientes | Media | Un lote en producción hace **más de 3 días** que no tiene una recolección finalizada |

Los umbrales están juntos y con nombre al principio de `alertas/reglas.py`, para
poder ajustarlos en un solo lugar cuando la granja los revise.

### Ciclo de vida

```
          aparece la situación            deja de cumplirse
   (sin alerta) ───────────────► Pendiente ───────────────► Resuelta
                                     │
                                     └── sigue: se actualiza la descripción
                                         ("termina en 2 días" → "termina mañana")
```

Un lote no acumula dos alertas pendientes del mismo tipo: lo garantiza la
restricción `alerta_pendiente_unica` en la base. Si la situación se resuelve y
más adelante vuelve a darse, se genera una alerta nueva, así queda el historial.

### Cuándo se evalúan

No hay tarea programada. `generar_alertas()` corre antes de resolver cada
consulta de alertas y del panel, igual que la transición automática de los lotes
(`lotes/transiciones.py`), así el estado siempre está al día. Es idempotente:
ejecutarla dos veces seguidas no cambia nada.

Lo primero que hace es poner al día los lotes
(`pasar_a_produccion_vencidos()`), porque las reglas dependen de su etapa.

---

## 4. Matriz rol × sección

| Qué | Administrador | Operario | Consulta |
|-----|:---:|:---:|:---:|
| Ver el panel | Sí | Sí | Sí |
| Ver las alertas | Sí | Solo las de sus galpones | Sí |
| Acceso directo a nueva recolección / descarte | Sí | Sí | No |
| Acceso directo a nueva compra | Sí | No | No |
| Enlace al informe de producción | Sí | No | Sí |

Los accesos directos se muestran según el rol, pero quien decide es el backend:
cada sección valida sus permisos como siempre.

---

## 5. Decisiones de diseño

- **Las mismas definiciones que los informes.** La postura y los huevos del día
  salen de `informes/calculos.py` (`serie_postura`, `huevos_por_lote_y_dia`), que
  pasaron a ser funciones públicas y aceptan un conjunto de galpones. Si mañana
  cambia la definición de postura, cambia en un solo lugar.
- **Solo registros finalizados**, como en los informes y en el stock: una
  recolección pendiente todavía no hizo efecto. Por eso el gráfico lo aclara
  abajo del título ("Huevos de recolecciones finalizadas").
- **Una sola petición.** El panel es la primera pantalla que se abre al entrar;
  pedir cinco cosas por separado se notaría. Todo se calcula en el backend y la
  pantalla solo da formato.
- **La postura del día, no el promedio de la semana.** Es el mismo número con el
  que se evalúa la alerta de postura baja: si el panel dijera una cosa y la
  alerta otra, no se entendería.
- **La alerta mira el último día con recolección**, no estrictamente hoy: a la
  mañana todavía no hay nada cargado y el lote no tendría por qué dejar de estar
  en alerta.
- **El stock de productos es el de toda la granja**, también para el Operario:
  el stock no pertenece a un galpón, y el Operario ya lo ve al registrar una
  salida. El resto de los datos sí se limita a sus galpones asignados (F-32).
- **Se muestran los productos activos y los inactivos que todavía tienen
  existencias.** Esconder un producto dado de baja con stock haría que el total
  no cierre; la tarjeta lo marca como inactivo.
- **Las alertas no son auditables.** `Alerta` no hereda de `ModeloAuditable`
  porque no hay un usuario que las haya creado ni editado: las genera el
  sistema. Por eso tampoco tienen "ojito".
- **El tipo de alerta es una tabla** (`TiposAlerta`, como en el modelo
  relacional) y sus filas las crea una migración de datos, no la aplicación: un
  tipo existe porque hay una regla que lo detecta.
- **Dos columnas agregadas al modelo relacional**: `clave` en `TiposAlerta`
  (identifica el tipo en el código y en la pantalla; el nombre es un texto que
  puede cambiar) y `fecha_resolucion` en `Alertas` (para mostrar el historial).
- **Los accesos directos navegan con estado**, no con un parámetro en la URL: la
  sección abre el formulario de alta y limpia el estado enseguida, así volver
  con el botón «atrás» o refrescar no lo abre de nuevo
  (`components/useAtajoAlta.js`).
- **El anillo es CSS**, un `conic-gradient` armado con los porcentajes, sin
  librerías de gráficos (igual que las gráficas de los informes).
- **La fórmula del stock quedó en un solo lugar** (`productos/stock.py`), que
  ahora usan el listado de productos y el panel.

---

## 6. Endpoints

| Método | Ruta | Qué hace | Permiso |
|--------|------|----------|---------|
| GET | `/api/dashboard/resumen/` | Todo el panel en una respuesta | Autenticado |
| GET | `/api/alertas/` | Listado paginado (`?estado=P\|R`, `?id_lote=`, `?id_galpon=`) | Autenticado |
| GET | `/api/alertas/{id}/` | Detalle de una alerta | Autenticado |

Las alertas son de solo lectura: un `POST` o un `DELETE` devuelven 405. Una
alerta de otro galpón devuelve 404 para el Operario (no se revela que existe).

### Respuesta de `/api/dashboard/resumen/`

```json
{
  "fecha": "2026-08-09",
  "huevos_hoy": 1842, "huevos_ayer": 1650, "variacion_huevos": 11.6,
  "postura_hoy": 87.4, "postura_ayer": 86.9, "variacion_postura": 0.5,
  "galpones_activos": 8, "galpones_en_produccion": 6,
  "alertas_pendientes": 3,
  "produccion": [{"fecha": "2026-08-03", "huevos": 1700}],
  "stock_productos": {
    "total": 10830,
    "items": [{"id_producto": 1, "producto": "Huevo Nº1", "descripcion": "Grande",
               "estado": "A", "stock": 3240, "porcentaje": 29.9}]
  },
  "alertas": [{"id_alerta": 1, "clave": "postura_baja", "tipo": "Postura baja",
               "severidad": "A", "lote": "L-2026-005", "galpon": "Galpón 3",
               "descripcion": "...", "estado": "P", "estado_display": "Pendiente",
               "fecha_generacion": "...", "fecha_resolucion": null}]
}
```

`postura_hoy`, `variacion_huevos` y `variacion_postura` son `null` cuando no hay
con qué comparar; la pantalla muestra «—» y no inventa un cero.

---

## 7. Modelo de datos

```
TiposAlerta                        Alertas
  idTipoAlerta  SMALLINT PK          idAlerta         INT PK
  clave         VARCHAR(40) UNIQUE   idLote           INT FK → Lotes (CASCADE)
  nombre        VARCHAR(100)         idTipoAlerta     SMALLINT FK → TiposAlerta
  severidad     CHAR(1)  A|M         descripcion      VARCHAR(255)
                                     estado           CHAR(1)  P|R
                                     fechaGeneracion  TIMESTAMP
                                     fechaResolucion  TIMESTAMP NULL
```

Restricción `alerta_pendiente_unica`: `(idLote, idTipoAlerta)` único mientras
`estado = 'P'`. Índice por `(estado, fechaGeneracion)`.

Las migraciones se aplican con `python manage.py migrate`; la 0002 carga los
cuatro tipos de alerta.

---

## 8. Interfaz

- `frontend/src/pages/DashboardPage.jsx`: la pantalla entera. Reemplaza la vista
  estática, que se elimina junto con `pages/static/`.
- `frontend/src/components/useAtajoAlta.js`: abre el formulario de alta cuando
  se llega desde un acceso directo.
- `frontend/src/api/dashboard.js`: resumen del panel y listado de alertas.
- Estilos nuevos al final de `index.css` (aclaración bajo el título de una
  tarjeta, barra de hoy, accesos directos como botones y tonos del stock). El
  resto ya existía del mockup.

---

## 9. Tests

`python manage.py test alertas dashboard` — 53 tests:

| Clase | Qué verifica |
|-------|--------------|
| `TiposAlertaTests` | La migración de datos deja los cuatro tipos cargados |
| `PosturaBajaTests` | Se genera, no se duplica, actualiza la descripción, se resuelve sola y vuelve a generarse |
| `TransicionPorVencerTests` | Aviso de los últimos días y resolución al pasar el lote a producción |
| `MortandadAltaTests` | Umbral, suma de la semana, descartes viejos y pendientes |
| `SinRecoleccionTests` | Plazo, lote recién pasado a producción y resolución al cargar |
| `ApiAlertasTests` | Listado, detalle, filtros, errores 400 y solo lectura |
| `ApiAlertasOperarioTests` | El Operario solo ve las de sus galpones (404 en las ajenas) |
| `ResumenVacioTests` | Una granja sin movimientos no rompe la pantalla |
| `ResumenTests` | Indicadores, variaciones, producción, stock y alertas |
| `ResumenOperarioTests` | Huevos, galpones y alertas limitados a sus galpones; stock general |
| `PermisosTests` | Los tres roles entran; sin sesión, 401 |

---

## 10. Archivos

```
backend/alertas/{models,reglas,generacion,serializers,views,urls,admin,apps,tests}.py
backend/alertas/migrations/{0001_initial,0002_tipos_alerta}.py
backend/dashboard/{calculos,views,urls,apps,tests}.py
backend/productos/stock.py        (fórmula del stock, antes en views.py)
backend/informes/calculos.py      (helpers públicos + filtro por varios galpones)
backend/config/{settings,urls}.py
frontend/src/{api/dashboard.js, components/useAtajoAlta.js, pages/DashboardPage.jsx}
frontend/src/{App.jsx, index.css}
frontend/src/pages/{ComprasPage,DescartesPage,RecoleccionesPage}.jsx
frontend/src/pages/static/        (eliminado: era el último mockup)
```

---

## 11. Pendientes

- Numerar los casos de uso del Dashboard.
- Pantalla propia de alertas, con historial y filtros.
- Tutoriales de uso de cada sección.
- Revisar los umbrales de las reglas con la granja.
