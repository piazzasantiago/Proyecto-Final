# Gestión de Proveedores

**Rama:** `feature/gestion-proveedores`
**Casos de uso:** CU70, CU71, CU72, CU73, CU74, CU75

Módulo que administra los proveedores de la granja: quienes venden materias
primas y lotes de gallinas. Es la base del módulo de Compras, que necesita
saber a quién se le compra.

---

## 1. Alcance

### Qué incluye

- Buscar proveedores por texto (nombre, CUIT, email, teléfono y dirección),
  filtrar por estado y ordenar (CU70).
- Alta, modificación y borrado de proveedores (CU71, CU72, CU73).
- Dar de alta y de baja como acciones dedicadas, no vía `PATCH` del estado
  (CU74, CU75).
- Validaciones: nombre único (sin distinguir mayúsculas, tildes ni espacios de
  más), email con formato válido, teléfono argentino con característica, dirección con contenido, CUIT con dígito
  verificador y único.
- Aviso en el formulario mientras se escribe si ya existe un nombre igual o
  parecido (`GET /api/proveedores/similares/`).
- Interfaz React con tarjetas y panel de detalle; botones de acción solo para el
  Administrador.
- 61 tests automatizados.

### Qué no incluye

- El vínculo con Compras: la sección "Compras recientes" del detalle es un
  marcador de posición hasta que exista ese módulo.
- Manejo del borrado cuando haya compras asociadas: el endpoint ya devuelve 409
  ante un `ProtectedError`, pero la restricción `PROTECT` recién existirá cuando
  Compras referencie a Proveedores.

---

## 2. Casos de uso y permisos

| CU | Caso de uso | Administrador | Operario | Consulta |
|----|-------------|:---:|:---:|:---:|
| CU70 | Buscar proveedor | Sí | No | Sí |
| CU71 | Nuevo proveedor | Sí | No | No |
| CU72 | Modificar proveedor | Sí | No | No |
| CU73 | Borrar proveedor | Sí | No | No |
| CU74 | Dar de alta proveedor | Sí | No | No |
| CU75 | Dar de baja proveedor | Sí | No | No |

El Operario no tiene acceso a la sección (ni siquiera de lectura), igual que en
el menú. Se implementa con el permiso
`LecturaAdministradorYConsulta_EscrituraAdministrador` en `usuarios/permissions.py`.

---

## 3. Modelo de datos

Tabla `Proveedores`:

| Campo | Tipo | Notas |
|-------|------|-------|
| `idProveedor` | AutoField | PK |
| `nombre` | varchar(100) | **Agregado al diagrama.** Obligatorio y único |
| `cuit` | varchar(11) | **Agregado al diagrama.** Opcional; solo dígitos; único si no está vacío |
| `direccion` | varchar(150) | Opcional (en el diagrama era obligatoria) |
| `email` | varchar(150) | Obligatorio, se guarda en minúsculas |
| `telefono` | varchar(45) | Obligatorio |
| `estado` | char(1) | `A` activo / `I` inactivo; por defecto `A` |

El diagrama original no tenía forma de identificar a un proveedor por su nombre,
por eso se agregaron `nombre` y `cuit`. Ver `modelo-relacional/anotaciones.md`.

---

## 4. Decisiones de diseño

- **Nombre único** comparando con `normalizar_nombre` (sin tildes, mayúsculas ni
  espacios repetidos), igual que Materias Primas. Un proveedor dado de baja sigue
  ocupando su nombre.
- **CUIT opcional**, pero si se carga se valida: 11 dígitos y dígito verificador
  (módulo 11 de AFIP). Acepta guiones y espacios; se guarda solo con dígitos y
  se muestra como `XX-XXXXXXXX-X`. La unicidad es una restricción parcial en la
  base (`proveedor_cuit_unico`, solo cuando no está vacío).
- **Nombre**: al menos 2 caracteres alfanuméricos e incluir letras (rechaza ".", "123").
- **Teléfono argentino**: se normalizan +54, el 9 de celulares, el 0 inicial y el 15 intermedio; deben quedar 10 dígitos (característica + número) con característica que empiece con 11, 2 o 3, y no puede ser una repetición de dígitos ("0000000"). Se guarda como lo escribió el usuario.
- **Alta / baja** son acciones (`POST .../alta/` y `.../baja/`); repetirlas
  responde 409.
- **El estado no se envía** al crear ni al modificar.
- **Borrado**: un `ProtectedError` se traduce a 409 con mensaje en español.

---

## 5. Endpoints

| Método | Ruta | Descripción | Permiso |
|--------|------|-------------|---------|
| GET | `/api/proveedores/` | Listar (`?search=`, `?estado=`, `?ordering=`) | Adm. / Consulta |
| POST | `/api/proveedores/` | Crear proveedor | Adm. |
| GET | `/api/proveedores/{id}/` | Detalle | Adm. / Consulta |
| PATCH | `/api/proveedores/{id}/` | Modificar | Adm. |
| DELETE | `/api/proveedores/{id}/` | Borrar (409 si tiene registros asociados) | Adm. |
| POST | `/api/proveedores/{id}/alta/` | Dar de alta | Adm. |
| POST | `/api/proveedores/{id}/baja/` | Dar de baja | Adm. |
| GET | `/api/proveedores/similares/` | Nombres iguales o parecidos (`?nombre=&excluir=`) | Adm. / Consulta |

---

## 6. Interfaz

- `frontend/src/pages/ProveedoresPage.jsx`: tarjetas, búsqueda, filtro de estado
  y panel de detalle.
- `frontend/src/components/ProveedorFormModal.jsx`: alta y edición, con aviso de
  nombres parecidos.
- `frontend/src/api/proveedores.js`: llamadas a la API.
- La ruta `/app/proveedores` en `App.jsx` reemplaza la vista estática y conserva
  `RequireRol` (Administrador y Consulta).

---

## 7. Tests

`python manage.py test proveedores` — 61 tests en 8 clases: Buscar, Nuevo,
Modificar, Borrar, Alta/Baja, Similares, CUIT y Permisos.

---

## 8. Archivos

```
backend/proveedores/{models,serializers,views,urls,admin,apps,tests}.py
backend/proveedores/migrations/0001_initial.py
backend/usuarios/permissions.py   (nuevo permiso)
backend/config/{settings,urls}.py
frontend/src/{api/proveedores.js, components/ProveedorFormModal.jsx, pages/ProveedoresPage.jsx}
```

---

## 9. Pendientes

- Mostrar las compras recientes del proveedor cuando exista Compras.
- Cambiar `on_delete` de las FK de Compras a `PROTECT` y verificar el 409 real.
- Mejora futura: verificar la dirección con autocompletado y mapa (Georef AR para validar calles y localidades de Argentina, y Leaflet con OpenStreetMap para mostrar el pin). Requeriría agregar `latitud` y `longitud` opcionales al modelo y mantener la carga manual para direcciones rurales.
