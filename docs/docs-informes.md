# Informes e indicadores productivos — documentación de la feature

**Rama:** `feature/gestion-informes`
**Casos de uso cubiertos:** CU85, CU86, CU87, CU88 y CU89

Módulo de solo lectura que arma informes con lo que cargaron los demás módulos
(recolecciones, lotes, descartes, entradas y compras). No tiene modelos ni
migraciones propias. Cada informe se ve en pantalla y se puede exportar a **Excel
(.xlsx)** o **PDF**.

---

## 1. Alcance

### Qué incluye

- Cinco informes, uno por caso de uso, en una pantalla con pestañas.
- Filtros por rango de fechas (por defecto, los últimos 30 días; máximo 366),
  galpón, etapa del lote, materia prima y tipo de descarte, según el informe.
- Exportación de cada informe a Excel y a PDF con los filtros elegidos.
- Gráfica de indicadores contra un valor objetivo que escribe el usuario.
- Acceso para Administrador y Consulta; el Operario no ve la sección.
- 53 tests automatizados.

### Qué no incluye

- Objetivos guardados en la base: el valor objetivo se escribe en pantalla y no
  se persiste (así lo describe la Educción de requisitos).
- El Dashboard sigue siendo una vista previa.
- Consumo diario real de materias primas: el sistema no lo registra (ver
  *Decisiones de diseño*).

---

## 2. Casos de uso

### CU85 – Generar Informe de Producción

**Actor:** Administrador, Consulta.

Tabla por galpón y lote para un rango de fechas, con los huevos producidos, los
días con registro, el promedio diario y la postura promedio. Incluye una fila de
totales y el gráfico **Postura por galpón** (verde desde 85 %, dorado entre 70 % y
85 %, rojo por debajo de 70 %). Filtro opcional por galpón.

### CU86 – Generar Informe de Lotes

**Actor:** Administrador, Consulta.

Estado de los lotes a la fecha de hoy: lote, galpón, etapa (Transición,
Producción o Finalizado), fecha de ingreso, edad en semanas, gallinas iniciales y
actuales, y mortandad (cantidad y porcentaje). En un lote vaciado la edad se
cuenta hasta la fecha de vaciado. Filtros: galpón y etapa. No usa rango de fechas.

### CU87 – Generar Informe de Materias Primas

**Actor:** Administrador, Consulta.

Una fila por materia prima con lo consumido en el período, lo comprado, lo
descartado de stock, el stock actual y el stock mínimo. El stock actual por debajo
del mínimo se marca en rojo en pantalla. Filtro opcional por materia prima.

### CU88 – Generar Informe de Descartes

**Actor:** Administrador, Consulta.

Historial de líneas de descarte del período, de la más reciente a la más antigua:
fecha, origen (galpón o stock), galpón, tipo (gallinas, materia prima o producto),
qué se descartó, cantidad, unidad y motivo. Filtros: galpón y tipo. Muestra el
total de registros por tipo y dos gráficos: **Descartes por galpón** (dona) y
**Descartes por materia prima** (barras). Ambos cuentan registros de descarte,
no cantidades, porque las unidades se mezclan (gallinas, kg, dosis).

### CU89 – Visualizar Indicadores Productivos

**Actor:** Administrador, Consulta.

Serie diaria de un indicador a lo largo del período, con tarjetas de resumen
(postura promedio, huevos producidos, descartes registrados y mortandad). Los
indicadores son **postura** (%), **mortandad** (gallinas) y **consumo** de una
materia prima. El usuario puede escribir un **valor objetivo**: se dibuja como una
línea constante y se muestra cuánto se aleja el promedio del objetivo. Los días
sin dato (por ejemplo, sin recolección) cortan la línea en lugar de contarse como
cero.

---

## 3. Matriz rol × caso de uso

| CU | Informe | Administrador | Operario | Consulta |
|----|---------|:---:|:---:|:---:|
| CU85 | Producción | Sí | No | Sí |
| CU86 | Lotes | Sí | No | Sí |
| CU87 | Materias primas | Sí | No | Sí |
| CU88 | Descartes | Sí | No | Sí |
| CU89 | Indicadores | Sí | No | Sí |

Se usa el permiso `LecturaAdministradorYConsulta_EscrituraAdministrador`, y todos
los endpoints son de solo lectura (un `POST` devuelve 405).

---

## 4. Decisiones de diseño

- **Solo registros finalizados.** Las recolecciones, descartes, entradas y compras
  pendientes todavía no hicieron efecto y no cuentan.
- **Postura de un día** = huevos recolectados ese día / gallinas del lote ese día
  × 100. Las gallinas de un lote son su cantidad inicial menos las gallinas
  descartadas (descartes finalizados) hasta ese día inclusive. Así el porcentaje
  respeta la mortandad de cada fecha y no solo la cantidad actual.
- **Postura promedio**: en cada lote es el promedio de sus porcentajes diarios; en
  el total y en los indicadores es el promedio de la serie diaria, donde cada día
  suma los huevos y las gallinas de todos los lotes con recolección.
- **Consumo de materia prima** = lo enviado a los galpones en entradas finalizadas,
  porque el sistema no registra cuánto se consume cada día. Si más adelante se
  agrega ese registro, solo cambia este cálculo.
- **Descartado de stock** (informe de materias primas): solo cuentan los descartes
  de stock, que son los que restan del stock; los de galpón ya salieron de él al
  enviarse a los galpones. Así las columnas respetan la fórmula del stock actual.
- **Mortandad** = gallinas descartadas.
- **Valor objetivo en pantalla.** No toca el modelo de datos ni agrega un caso de
  uso de configuración que no está en la lista.
- **Exportación en el backend.** Con `?formato=xlsx|pdf` el mismo endpoint de cada
  informe devuelve el archivo; la pantalla lo descarga con el token. Excel con
  `openpyxl` y PDF con `reportlab` (nuevas dependencias en `requirements.txt`:
  hay que correr `pip install -r requirements.txt`).
- **Gráfica en SVG propio**, sin librerías de gráficos.
- **Tope de 366 días** por informe, para evitar consultas enormes por un error de
  tipeo.

---

## 5. Endpoints

Todos son `GET`, con permiso Administrador / Consulta. Cualquiera acepta
`?formato=json|xlsx|pdf` (por defecto `json`).

| Ruta | Informe | Parámetros |
|------|---------|------------|
| `/api/informes/produccion/` | CU85 | `fecha_desde`, `fecha_hasta`, `id_galpon` |
| `/api/informes/lotes/` | CU86 | `estado` (T, P o F), `id_galpon` |
| `/api/informes/materias-primas/` | CU87 | `fecha_desde`, `fecha_hasta`, `id_materia_prima` |
| `/api/informes/descartes/` | CU88 | `fecha_desde`, `fecha_hasta`, `id_galpon`, `tipo` (G, M o P) |
| `/api/informes/indicadores/` | CU89 | `indicador` (postura, mortandad o consumo), `fecha_desde`, `fecha_hasta`, `id_galpon`, `id_materia_prima` (obligatorio para el consumo) |

Las fechas van como `AAAA-MM-DD`. Un parámetro inválido o un id inexistente
devuelve 400 con el mensaje en español.

La respuesta JSON de los informes en tabla trae `titulo`, `periodo`, `filtros`,
`columnas`, `filas` y `totales`. La de indicadores agrega `serie` (fecha y valor
por día), `promedio`, `unidad` y `resumen`.

---

## 6. Interfaz

- `frontend/src/pages/InformesPage.jsx`: pestañas, filtros, tablas, tarjetas y
  botones de exportación. Reemplaza la vista estática.
- `frontend/src/components/GraficoIndicador.jsx`: gráfica de línea en SVG con la
  línea del valor objetivo.
- `frontend/src/components/GraficosInforme.jsx`: barras horizontales y dona de los
  informes en tabla. Se calculan en pantalla con las filas del informe ya cargado.
- `frontend/src/api/informes.js`: consulta de informes y descarga de archivos.
- Las pestañas usan estilos nuevos al final de `index.css`.

---

## 7. Tests

`python manage.py test informes` — 53 tests en 8 clases:

| Clase | Qué verifica |
|-------|--------------|
| `ParametrosInformeTests` | Fechas inválidas, período mayor a 366 días, ids inexistentes y formato inválido |
| `InformeProduccionTests` | Huevos por galpón y lote, postura con las gallinas de cada día, totales, filtros y rango |
| `InformeLotesTests` | Edad (hasta hoy o hasta el vaciado), mortandad y filtros |
| `InformeMateriasPrimasTests` | Consumido, comprado, descartado de stock y stock actual |
| `InformeDescartesTests` | Detalle de cada tipo, filtros, orden y resumen |
| `IndicadoresTests` | Serie diaria de postura, mortandad y consumo, y resumen |
| `ExportacionInformesTests` | Excel y PDF de cada informe, contenido, nombre del archivo y filtros |
| `PermisosInformesTests` | Administrador y Consulta ven todo, Operario 403, sin token 401 y solo lectura |

---

## 8. Archivos

```
backend/informes/{calculos,exportacion,views,urls,apps,tests}.py
backend/requirements.txt          (openpyxl y reportlab)
backend/config/{settings,urls}.py
frontend/src/{api/informes.js, components/GraficoIndicador.jsx, components/GraficosInforme.jsx,
              pages/InformesPage.jsx}
frontend/src/{App.jsx, index.css}
```

---

## 9. Pendientes

- Dashboard con datos reales (hoy es una vista previa).
- Registro del consumo diario de materias primas para un consumo real.
- Objetivos guardados por indicador, si se los quiere persistentes.
- El mockup `frontend/src/pages/static/raw/informes.html` ya no se usa y puede
  borrarse.
