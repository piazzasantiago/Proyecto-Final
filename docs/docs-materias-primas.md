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
- `stock_actual` expuesto como campo calculado de solo lectura; por ahora
  equivale a `stock_inicial` (base para integración futura con Compras y
  Descartes).
- Alerta visual en la tarjeta y en el panel de detalle cuando
  `stock_actual < stock_minimo`.
- Acceso de solo lectura para los roles Operario y Consulta.
- Tests automatizados del módulo (44 tests en 8 clases).
- Interfaz React con tarjetas compactas y panel de detalle; botones de acción
  visibles solo para el rol Administrador.
- Script standalone `seed_materias_primas.py` (raíz del repo) para poblar la
  tabla con 18 materias primas de ejemplo.

### Qué no incluye

- Los incrementos de stock por Compras y los decrementos por Descartes. El
  stock actual hoy devuelve `stock_inicial`; cuando existan esos módulos
  bastará con sumar compras y restar descartes en el mismo campo calculado.

---

## 2. Casos de uso

### CU55 – Nueva Materia Prima

**Actor:** Administrador.

Crea una materia prima con nombre (único, hasta 100 caracteres), unidad de
medida, stock mínimo y stock inicial. La descripción es opcional. El estado
inicial siempre es Activo.

### CU56 – Buscar Materia Prima

**Actor:** cualquier usuario autenticado.

Lista las materias primas con búsqueda por nombre/descripción (`?search=`) y
filtro por estado (`?estado=A|I`).

### CU57 – Modificar Materia Prima

**Actor:** Administrador.

Modifica nombre, descripción, unidad, stock mínimo o stock inicial. El estado
no se puede cambiar por este medio.

### CU58 – Activar Materia Prima

**Actor:** Administrador.

Pasa una materia prima de Inactiva a Activa. Devuelve `409` si ya estaba
activa.

### CU59 – Desactivar Materia Prima

**Actor:** Administrador.

Pasa una materia prima de Activa a Inactiva. Devuelve `409` si ya estaba
inactiva. Desactivar no afecta los registros históricos ya asociados.

### CU60 – Borrar Materia Prima

**Actor:** Administrador.

Elimina la materia prima físicamente. Si tiene registros asociados (Compras,
Descartes), el borrado se rechaza con `409` y el mensaje indica que debe
desactivarse en su lugar.

---

## 3. Matriz rol × caso de uso

| Caso de uso | Administrador | Operario | Consulta |
|---|:---:|:---:|:---:|
| CU55 Nueva Materia Prima | Sí | No | No |
| CU56 Buscar Materia Prima | Sí | Sí | Sí |
| CU57 Modificar Materia Prima | Sí | No | No |
| CU58 Activar Materia Prima | Sí | No | No |
| CU59 Desactivar Materia Prima | Sí | No | No |
| CU60 Borrar Materia Prima | Sí | No | No |

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
| `materia_prima` | VARCHAR(100) | Obligatorio, único |
| `descripcion` | TEXT | Opcional |
| `unidad` | VARCHAR(20) | Obligatorio (kg, g, L, mL, unid., bolsa, saco, etc.) |
| `estado` | CHAR(1) | A (Activo), I (Inactivo) — default A |
| `stock_minimo` | DecimalField(10,2) | Obligatorio ≥ 0 — default 0 |
| `stock_inicial` | DecimalField(10,2) | Obligatorio ≥ 0 — default 0 (stock de partida o ajuste manual) |

**Propiedades calculadas (no son columnas):**

- `estado_display` — texto legible del estado (`"Activo"` / `"Inactivo"`),
  incluido en todas las respuestas de la API.
- `stock_actual` — por ahora devuelve `stock_inicial`. Cuando existan Compras
  y Descartes se calculará como `stock_inicial + compras − descartes`.

---

## 5. Endpoints

| Caso de uso | Método | Ruta | Rol |
|---|---|---|---|
| CU56 | GET | `/api/materias-primas/` | autenticado |
| CU56 (detalle) | GET | `/api/materias-primas/{id}/` | autenticado |
| CU55 | POST | `/api/materias-primas/` | Administrador |
| CU57 | PATCH | `/api/materias-primas/{id}/` | Administrador |
| CU60 | DELETE | `/api/materias-primas/{id}/` | Administrador |
| CU58 | POST | `/api/materias-primas/{id}/activar/` | Administrador |
| CU59 | POST | `/api/materias-primas/{id}/desactivar/` | Administrador |

**Filtros de CU56:** `?search=` (nombre o descripción), `?estado=A|I`

**Respuesta de ejemplo (CU56):**

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
      "stock_actual": "500.00"
    }
  ]
}
```

**Campo `estado` (solo lectura vía `PATCH`):** se incluye en las respuestas
pero modificarlo con `PATCH` no tiene efecto; los cambios de estado solo
ocurren a través de `activar`/`desactivar`.

**Campos `stock_minimo` y `stock_inicial` (editables):** `DecimalField` con
dos decimales; un valor negativo devuelve `400`.

**Campo `stock_actual` (solo lectura):** se calcula en el serializer; enviarlo
en un `POST`/`PATCH` no tiene efecto.

---

## 6. Tests automatizados

Los tests viven en `backend/materias_primas/tests.py`. Se organizan en ocho
clases independientes.

### Estructura

| Clase | Tests | Qué cubre |
|---|:---:|---|
| `BuscarMateriaPrimaTests` | 6 | CU56: listado, búsqueda por nombre y descripción, filtros por estado |
| `NuevaMateriaPrimaTests` | 6 | CU55: alta válida, estado por defecto, descripción opcional, nombre duplicado (400), decimales en stock |
| `ModificarMateriaPrimaTests` | 4 | CU57: modificación parcial, inmutabilidad del estado vía `PATCH`, materia prima inexistente |
| `BorrarMateriaPrimaTests` | 2 | CU60: borrado físico, materia prima inexistente |
| `ActivarMateriaPrimaTests` | 4 | CU58: activación, persistencia, idempotencia (409), materia prima inexistente |
| `DesactivarMateriaPrimaTests` | 4 | CU59: desactivación, persistencia, idempotencia (409), materia prima inexistente |
| `PermisosMateriaPrimaTests` | 14 | Matriz rol × operación (Admin / Operario / Consulta / sin token) |
| `StockMateriaPrimaTests` | 4 | `stock_minimo` y `stock_inicial` al crear y vía `PATCH`, rechazo de negativos, `stock_actual` de solo lectura |
| **Total** | **44** | |

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
    └── tests.py          44 tests en 8 clases
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

### 8.4 stock_actual como campo calculado provisional

El dominio describe el stock disponible como un valor dinámico
(`stock_inicial + compras − descartes`). Hoy solo existe `stock_inicial`
porque Compras y Descartes aún no están implementados. Se eligió exponer
`stock_actual` como `SerializerMethodField` desde el principio — devolviendo
`stock_inicial` por ahora — para que el frontend y los tests ya consuman la
interfaz definitiva. Cuando se agreguen los módulos dependientes, solo cambia
la implementación del método, sin romper ningún contrato de API.

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

- 44 tests del módulo en verde.
- Suite completa del proyecto en verde (321 tests).
- Los tres roles pueden listar y ver el detalle de materias primas.
- Operario recibe 403 al intentar crear, modificar, borrar o cambiar el estado.
- Sin token, la API responde 401.
- Activar y desactivar devuelven 409 si la materia prima ya está en el estado
  solicitado.
- Un nombre duplicado devuelve 400.
- Un `stock_minimo` o `stock_inicial` negativo devuelve 400.

**Frontend**

- El botón "Nueva materia prima" y las acciones del panel de detalle (Editar,
  Dar de alta/baja, Eliminar) no aparecen para Operario ni Consulta.
- La alerta de stock bajo aparece en la tarjeta y en el panel de detalle cuando
  corresponde.
- El formulario incluye selector de unidad (kg, g, L, mL, unid., bolsa, saco)
  y campos decimales para stock mínimo e inicial.

---

## 10. Pendientes

- **Compras:** cuando el módulo exista, `stock_actual` debe sumar el total de
  compras registradas para la materia prima.
- **Descartes:** cuando el módulo exista, `stock_actual` debe restar los
  descartes asociados.
- **Relación con Descartes:** el borrado de una materia prima (CU60) deberá
  bloquearse cuando tenga descartes asociados, igual que el borrado de un
  galpón con lotes. El backend ya devuelve error en ese caso; el mensaje en el
  frontend indica desactivar como alternativa.
