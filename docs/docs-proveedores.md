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
  más), email con formato válido, teléfono argentino con característica o
  internacional (con `+` y código de país), dirección con contenido, CUIT con
  dígito verificador y único.
- Aviso en el formulario mientras se escribe si ya existe un nombre igual o
  parecido (`GET /api/proveedores/similares/`).
- Interfaz React con tarjetas y panel de detalle; botones de acción solo para el
  Administrador.
- 64 tests automatizados.

### Qué no incluye

- La sección "Compras recientes" del detalle sigue siendo un marcador de
  posición (el módulo de Compras ya existe; falta listarlas acá).

---

## 2. Casos de uso

### CU70 – Buscar Proveedor

**Actor:** Administrador, Consulta.

Lista los proveedores con búsqueda de texto (`?search=`) sobre nombre, CUIT,
email, teléfono y dirección, filtro por estado (`?estado=A|I`) y orden
(`?ordering=`, por defecto por nombre). También permite ver el detalle de uno.

### CU71 – Nuevo Proveedor

**Actor:** Administrador.

Crea un proveedor con nombre (obligatorio y único), email y teléfono
(obligatorios; el teléfono puede ser argentino o de otro país), y CUIT y
dirección opcionales. El nombre, el teléfono, la
dirección y el CUIT se validan como se explica en la sección de decisiones de
diseño. El estado inicial siempre es Activo. Mientras se escribe el nombre, el
formulario avisa si ya existe uno igual o parecido.

### CU72 – Modificar Proveedor

**Actor:** Administrador.

Modifica cualquier dato del proveedor, con las mismas validaciones que al
crearlo. Reenviar el propio nombre o CUIT no cuenta como duplicado. Se puede
borrar el CUIT y la dirección. El estado no se puede cambiar por este medio.

### CU73 – Borrar Proveedor

**Actor:** Administrador.

Elimina el proveedor físicamente. Si tiene compras asociadas, el borrado se rechaza con `409` y el mensaje indica
que debe darse de baja en su lugar.

### CU74 – Dar de Alta Proveedor

**Actor:** Administrador.

Pasa un proveedor de Inactivo a Activo. Devuelve `409` si ya estaba activo.

### CU75 – Dar de Baja Proveedor

**Actor:** Administrador.

Pasa un proveedor de Activo a Inactivo. Devuelve `409` si ya estaba inactivo.
La baja conserva todos sus datos y no afecta los registros históricos; su
nombre sigue ocupado.

---

## 3. Matriz rol × caso de uso

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

## 4. Modelo de datos

Tabla `Proveedores`:

| Campo | Tipo | Notas |
|-------|------|-------|
| `idProveedor` | AutoField | PK |
| `nombre` | varchar(100) | **Agregado al diagrama.** Obligatorio y único |
| `cuit` | varchar(11) | **Agregado al diagrama.** Opcional; solo dígitos; único si no está vacío |
| `direccion` | varchar(150) | Opcional (en el diagrama era obligatoria) |
| `email` | varchar(150) | Obligatorio, se guarda en minúsculas |
| `telefono` | varchar(45) | Obligatorio; argentino con característica o internacional con `+` (ver sección 5) |
| `estado` | char(1) | `A` activo / `I` inactivo; por defecto `A` |

El diagrama original no tenía forma de identificar a un proveedor por su nombre,
por eso se agregaron `nombre` y `cuit`. Ver `modelo-relacional/anotaciones.md`.

---

## 5. Decisiones de diseño

- **Nombre único** comparando con `normalizar_nombre` (sin tildes, mayúsculas ni
  espacios repetidos), igual que Materias Primas. Un proveedor dado de baja sigue
  ocupando su nombre.
- **CUIT opcional**, pero si se carga se valida: 11 dígitos y dígito verificador
  (módulo 11 de AFIP). Acepta guiones y espacios; se guarda solo con dígitos y
  se muestra como `XX-XXXXXXXX-X`. La unicidad es una restricción parcial en la
  base (`proveedor_cuit_unico`, solo cuando no está vacío).
- **Nombre**: al menos 2 caracteres alfanuméricos e incluir letras (rechaza ".", "123").
- **Teléfono: argentino o internacional.** Para admitir proveedores de otros
  países, la validación depende de cómo empieza el número. Siempre se aceptan
  solo dígitos, espacios, guiones, paréntesis y un `+` al inicio, y se guarda
  tal como lo escribió el usuario.

  | Cómo empieza | Cómo se valida | Ejemplos válidos |
  |---|---|---|
  | Sin `+`, o con `+54` | **Argentino, estricto**: se normalizan +54, el 9 de celulares, el 0 inicial y el 15 intermedio; deben quedar 10 dígitos (característica + número), con característica que empiece con 11, 2 o 3, y no puede ser una repetición de dígitos | `381-455-0102`, `0381 15 455-0102`, `+54 9 381 455 0102`, `(011) 4555-1234` |
  | `+` y un código de país distinto de 54 | **Internacional, básico**: entre 8 y 15 dígitos en total (máximo de la norma E.164), que no empiece con 0 y que no sea una repetición de dígitos | `+598 99 123 456`, `+1 (415) 555-2671`, `+34 612 345 678`, `+55 11 91234-5678` |

  Del lado internacional solo se controla lo básico porque cada país tiene su
  propio plan de numeración y mantener esas reglas excede el alcance del módulo.
  Un número extranjero **sin** `+` se rechaza, porque se interpreta como
  argentino. Antes de este cambio el teléfono admitía únicamente números
  argentinos y un proveedor del exterior no se podía cargar.
- **El CUIT sigue siendo argentino.** Es un identificador propio de Argentina
  (dígito verificador de módulo 11, el mismo algoritmo que usa ARCA, ex AFIP).
  Como el campo es opcional, un proveedor extranjero se carga con el CUIT vacío.
  Si más adelante hace falta guardar su identificador fiscal, convendría sumar un
  campo aparte (país o identificador fiscal).
- **Alta / baja** son acciones (`POST .../alta/` y `.../baja/`); repetirlas
  responde 409.
- **El estado no se envía** al crear ni al modificar.
- **Borrado**: un `ProtectedError` se traduce a 409 con mensaje en español.

---

## 6. Endpoints

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

## 7. Interfaz

- `frontend/src/pages/ProveedoresPage.jsx`: tarjetas, búsqueda, filtro de estado
  y panel de detalle.
- `frontend/src/components/ProveedorFormModal.jsx`: alta y edición, con aviso de
  nombres parecidos. Bajo el teléfono se muestra una ayuda (formato argentino y
  cómo cargar uno de otro país); si el teléfono tiene un error, se reemplaza por
  el mensaje de error para no mostrar dos textos a la vez.
- En el panel de detalle, una dirección larga que ocupa varias líneas queda
  alineada a la derecha, como el resto de las filas, sin mover el título.
- `frontend/src/api/proveedores.js`: llamadas a la API.
- La ruta `/app/proveedores` en `App.jsx` reemplaza la vista estática y conserva
  `RequireRol` (Administrador y Consulta).

---

## 8. Tests

`python manage.py test proveedores` — 64 tests en 8 clases: Buscar, Nuevo,
Modificar, Borrar, Alta/Baja, Similares, CUIT y Permisos.

Sobre el teléfono hay pruebas de formatos argentinos válidos e inválidos y tres
específicas de la validación internacional:

- `test_telefono_internacional_valido`: acepta números con `+` y código de país
  distinto de 54 (Uruguay, Estados Unidos, España, Brasil, Chile).
- `test_telefono_internacional_invalido`: rechaza los demasiado cortos o largos,
  los que empiezan con 0, las repeticiones de dígitos, los que tienen letras y el
  número extranjero sin `+`.
- `test_telefono_con_codigo_54_sigue_validandose_como_argentino`: con `+54` se
  mantiene la validación estricta.

---

## 9. Archivos

```
backend/proveedores/{models,serializers,views,urls,admin,apps,tests}.py
backend/proveedores/migrations/0001_initial.py
backend/usuarios/permissions.py   (nuevo permiso)
backend/config/{settings,urls}.py
frontend/src/{api/proveedores.js, components/ProveedorFormModal.jsx, pages/ProveedoresPage.jsx}
```

---

## 10. Pendientes

- Mostrar las compras recientes del proveedor en su detalle.
- *Resuelto con Compras:* la FK de Compras a Proveedores es `PROTECT` y el 409 al
  eliminar un proveedor con compras está cubierto por tests.
- Mejora futura: verificar la dirección con autocompletado y mapa (Georef AR para validar calles y localidades de Argentina, y Leaflet con OpenStreetMap para mostrar el pin). Requeriría agregar `latitud` y `longitud` opcionales al modelo y mantener la carga manual para direcciones rurales.
