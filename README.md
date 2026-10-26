# AvíGest — Sistema Web de Gestión para una Granja Avícola Productora de Huevos

Proyecto Final de Ingeniería en Computación — FACET, UNT

**Integrantes:**
- Piazza, Santiago Nicolás
- Vargas, Antonio Jesús

**Tecnologías:** React · Django + Django REST Framework · PostgreSQL

---

## Estado actual

El sistema cuenta con **autenticación real y control de acceso por rol**, y once
módulos funcionales de punta a punta: **Usuarios**, **Galpones**, **Lotes de
Gallinas**, **Productos**, **Recolección diaria**, **Materias Primas**,
**Descartes**, **Entradas**, **Salidas**, **Proveedores** y **Compras**.

| Módulo | Casos de uso | Estado |
|---|---|---|
| Autenticación | CU01, CU02 | Funcional |
| Gestión de Usuarios | CU03 a CU08 | Funcional |
| Gestión de Galpones | CU09 a CU14 | Funcional |
| Gestión de Lotes | CU42 a CU48 | Funcional |
| Gestión de Productos | CU49 a CU54 | Funcional |
| Recolección diaria | CU24 a CU32 | Funcional |
| Gestión de Materias Primas | CU55 a CU60 | Funcional |
| Descartes | CU15 a CU23 | Funcional |
| Entradas a galpones | CU33 a CU41 | Funcional |
| Salidas de productos | CU76 a CU84 | Funcional |
| Gestión de Proveedores | CU70 a CU75 | Funcional |
| Gestión de Compras | — | Funcional |
| Informes e indicadores | CU85 a CU89 | Funcional |
| Dashboard | — | Solo vista previa |

Los módulos de Recolección diaria y Descartes registran además el **usuario
responsable de la carga** (`id_usuario`) en cada registro, visible como columna
"Cargado por" en la tabla y en el panel de detalle.

Los **Descartes** tienen dos categorías: *Galpón* (algo que ocurre dentro de un
galpón; es estadístico y solo las gallinas descuentan del lote) y *Stock* (baja de
productos y materias primas almacenados, que sí reduce su stock actual). El stock
de productos y de materias primas no se guarda: se calcula a partir de las
recolecciones, los descartes y las salidas finalizadas (productos) o de los
descartes, las entradas a galpones y las compras finalizadas (materias primas).

Las **Entradas** retiran materias primas del stock y las pasan a un galpón: al
finalizarlas descuentan el stock de cada materia prima.

Las **Salidas** registran los productos que dejan la granja (por ejemplo, un
camión que se lleva los huevos para la venta): al finalizarlas descuentan el
stock de cada producto.

Las **Compras** se le hacen a un proveedor y son de dos categorías: de *materias
primas* (al finalizarlas suman al stock de cada materia prima) o de *lotes de
gallinas* (al finalizarlas, el lote queda esperando que se lo asigne a un galpón:
Lotes de gallinas muestra un cartel rojo y el alta de un lote exige elegir uno de
esos lotes comprados). Solo el Administrador las gestiona; Consulta solo lee y el
Operario no ve la sección.

Las secciones marcadas como *vista previa* muestran el HTML del mockup aprobado
por el tutor: **no leen ni guardan datos**, y sus botones no realizan
operaciones. Sirven para presentar la aplicación completa mientras se
implementan los módulos restantes, uno por uno, siguiendo el mismo patrón que
los módulos ya funcionales.

### Acceso por rol

El sistema define tres roles con distintos niveles de acceso:

| Sección | Administrador | Operario | Consulta |
|---|:---:|:---:|:---:|
| Dashboard | Sí | Sí | Sí |
| Galpones | Sí (CRUD) | Sí (consulta) | Sí (consulta) |
| Lotes de Gallinas | Sí (CRUD) | Sí (consulta) | Sí (consulta) |
| Recolección diaria | Sí (CRUD) | Sí (CRUD) | Sí (consulta) |
| Descartes | Sí (CRUD) | Sí (CRUD) | Sí (consulta) |
| Salidas | Sí (CRUD) | Sí (CRUD) | Sí (consulta) |
| Entradas | Sí (CRUD) | Sí (CRUD) | Sí (consulta) |
| Materias Primas | Sí (CRUD) | Sí (consulta) | Sí (consulta) |
| Productos | Sí (CRUD) | No | Sí (consulta) |
| Compras | Sí (CRUD) | No | Sí (consulta) |
| Proveedores | Sí (CRUD) | No | Sí (consulta) |
| Informes | Sí | No | Sí |
| Usuarios | Sí (CRUD) | No | No |

> Los módulos sin backend real todavía muestran el mockup. Los permisos de
> escritura/lectura dentro de cada sección se aplicarán en el backend cuando
> cada módulo se implemente. El detalle completo está en `docs/docs-usuarios.md`.

---

## Estructura del proyecto

```
Proyecto-Final/
├── .github/
│   └── workflows/
│       └── tests.yml    CI: tests automáticos en cada push
├── docs/                Documentación del proyecto y de cada feature
├── backend/             Django + DRF + PostgreSQL — API REST
└── frontend/            React + Vite — interfaz web
```

### Backend

```
backend/
├── config/          configuración del proyecto y rutas raíz
├── usuarios/        modelo Usuario, autenticación JWT, permisos y tests
├── galpones/        módulo de Galpones
├── lotes/           módulo de Lotes de Gallinas
├── productos/       módulo de Productos
├── recolecciones/   módulo de Recolección diaria
├── materias_primas/ módulo de Materias Primas
├── descartes/       módulo de Descartes
├── entradas/        módulo de Entradas a galpones
├── salidas/         módulo de Salidas de productos
├── proveedores/     módulo de Proveedores
├── compras/         módulo de Compras (materias primas y lotes)
├── informes/        módulo de Informes (solo lectura, Excel y PDF)
├── poblar_datos.py  script que carga datos de ejemplo para probar el sistema
└── manage.py
```

### Frontend

```
frontend/src/
├── api/             cliente HTTP y funciones de la API, una por módulo
├── config/menu.js   matriz rol × sección — fuente única de verdad
├── context/         estado de la sesión (AuthContext)
├── components/      componentes reutilizables
├── pages/           una pantalla por módulo
│   └── static/      HTML de los módulos aún no implementados
└── index.css        estilos del sistema
```

---

## 1. Requisitos previos

Instalar una sola vez:

- **Python 3.11 o superior** — [python.org/downloads](https://www.python.org/downloads/)
- **Node.js 18 o superior** — [nodejs.org](https://nodejs.org/)
- **PostgreSQL 14 o superior** — [postgresql.org/download](https://www.postgresql.org/download/)

Verificar la instalación:

```bash
python --version
node --version
psql --version
```

## 2. Crear la base de datos

Con PostgreSQL en ejecución:

```sql
CREATE DATABASE granja_avicola;
```

## 3. Backend

```bash
cd backend

python -m venv .venv
.venv\Scripts\activate           # Windows
source .venv/bin/activate        # Linux / macOS

pip install -r requirements.txt

copy .env.example .env           # Windows
cp .env.example .env             # Linux / macOS
```

Editar `.env` y completar `DB_PASSWORD` con la contraseña real de PostgreSQL.
Conviene generar también una `DJANGO_SECRET_KEY` propia:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Crear las tablas y el primer usuario administrador:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

`createsuperuser` solicita nombre de usuario, email, nombre, apellido, DNI y
contraseña. El usuario creado queda con rol **Administrador** y con acceso al
panel `/admin/`.

> **La base arranca vacía:** no hay usuarios ni galpones precargados. Todo se
> carga desde la aplicación o desde el panel de administración.

El backend queda disponible en `http://localhost:8000`.

## 4. Frontend

En otra terminal, con el backend en ejecución:

```bash
cd frontend
npm install

copy .env.example .env           # Windows
cp .env.example .env             # Linux / macOS

npm run dev
```

Abrir `http://localhost:5173` e iniciar sesión con el usuario creado en el paso
anterior.

### Cargar datos de ejemplo (opcional)

Para probar todas las funciones sin cargar todo a mano, el script
`backend/poblar_datos.py` llena la base con datos de ejemplo. Se corre desde la
carpeta `backend`, con el entorno virtual activo y las migraciones aplicadas:

```bash
python poblar_datos.py                 # carga los datos (si la base está vacía)
python poblar_datos.py --limpiar       # borra los datos de negocio y los vuelve a cargar
python poblar_datos.py --limpiar --si  # igual, sin pedir confirmación
python poblar_datos.py --dias 120      # historial más largo (por defecto 90 días)
python poblar_datos.py --semilla 7     # otra variante de los mismos datos
```

En Windows se usa `py` en lugar de `python`.

Genera usuarios de prueba, galpones, productos, materias primas, proveedores,
lotes en distintas etapas, y recolecciones, compras, entradas, descartes y
salidas de los últimos días (siempre relativos a la fecha de hoy). Las
cantidades se simulan día por día, así que el stock nunca queda negativo y se
respetan las reglas del sistema. También deja algunos registros pendientes, una
compra de lotes sin asignar y materias primas bajo el stock mínimo, para probar
los estados y las alertas.

Usuarios de prueba (todos con la clave `AviGest2026!`):

| Usuario | Rol |
|---------|-----|
| `admin.demo` | Administrador |
| `consulta.demo` | Consulta |
| `operario1`, `operario2`, `operario3` | Operario |

> **Cuidado con `--limpiar`:** borra los datos de negocio (galpones, lotes,
> compras, recolecciones, etc.) antes de cargar los de ejemplo. No usarlo sobre
> una base con datos reales.

## 5. Correr los tests

```bash
cd backend
python manage.py test --verbosity=2
```

Django crea automáticamente una base de datos temporaria, corre todos los tests
y la elimina al terminar. No toca la base de desarrollo.

```
Ran N tests in ~Xs
OK
```

Para correr solo un módulo:

```bash
python manage.py test usuarios
python manage.py test galpones
python manage.py test lotes
python manage.py test productos
python manage.py test recolecciones
python manage.py test materias_primas
python manage.py test descartes
python manage.py test entradas
python manage.py test salidas
python manage.py test proveedores
python manage.py test compras
python manage.py test informes
```

---

## Endpoints principales

| Método | Ruta | Descripción | Rol |
|---|---|---|---|
| POST | `/api/auth/login/` | Iniciar sesión | — |
| GET | `/api/auth/me/` | Usuario autenticado | autenticado |
| POST | `/api/auth/logout/` | Cerrar sesión | autenticado |
| GET | `/api/galpones/` | Listar galpones (`?search=`, `?estado=`, `?page=`, `?page_size=`), paginado de a 16 | autenticado |
| POST | `/api/galpones/` | Crear galpón | Administrador |
| PATCH | `/api/galpones/{id}/` | Modificar galpón | Administrador |
| DELETE | `/api/galpones/{id}/` | Eliminar galpón | Administrador |
| POST | `/api/galpones/{id}/alta/` | Activar galpón | Administrador |
| POST | `/api/galpones/{id}/baja/` | Dar de baja galpón | Administrador |
| GET | `/api/usuarios/` | Listar usuarios (`?search=`, `?rol=`, `?estado=`, `?page=`, `?page_size=`), paginado de a 16 | Administrador |
| POST | `/api/usuarios/` | Crear usuario | Administrador |
| PATCH | `/api/usuarios/{id}/` | Modificar usuario | Administrador |
| DELETE | `/api/usuarios/{id}/` | Eliminar usuario | Administrador |
| POST | `/api/usuarios/{id}/alta/` | Dar de alta usuario | Administrador |
| POST | `/api/usuarios/{id}/baja/` | Dar de baja usuario | Administrador |
| POST | `/api/usuarios/{id}/restablecer-password/` | Restablecer contraseña | Administrador |
| GET | `/api/lotes/` | Listar lotes (`?estado=`, `?id_galpon=`) | autenticado |
| POST | `/api/lotes/` | Crear lote con plan de transición; exige `id_linea_compra` (un lote comprado sin asignar) | Administrador |
| GET | `/api/lotes/{id}/` | Detalle del lote | autenticado |
| PATCH | `/api/lotes/{id}/` | Modificar lote o plan | Administrador |
| DELETE | `/api/lotes/{id}/` | Eliminar lote | Administrador |
| POST | `/api/lotes/{id}/iniciar-produccion/` | Transición → Producción | Administrador |
| POST | `/api/lotes/{id}/vaciar/` | Producción/Transición → Finalizado | Administrador |
| GET | `/api/recolecciones/` | Listar recolecciones, paginado de a 16 (`?id_galpon=`, `?id_lote=`, `?estado=`, `?fecha_desde=`, `?fecha_hasta=`, `?page=`) | autenticado |
| POST | `/api/recolecciones/` | Crear recolección con líneas | Adm. / Operario |
| GET | `/api/recolecciones/{id}/` | Detalle de recolección | autenticado |
| PATCH | `/api/recolecciones/{id}/` | Modificar recolección PENDIENTE | Adm. / Operario |
| DELETE | `/api/recolecciones/{id}/` | Eliminar recolección PENDIENTE (409 si está finalizada) | Administrador |
| POST | `/api/recolecciones/{id}/finalizar/` | Marcar recolección como Finalizada | Adm. / Operario |
| GET | `/api/materias-primas/` | Listar materias primas (`?search=`, `?estado=`, `?page=`, `?page_size=`), paginado de a 16 | autenticado |
| POST | `/api/materias-primas/` | Crear materia prima | Administrador |
| PATCH | `/api/materias-primas/{id}/` | Modificar materia prima | Administrador |
| DELETE | `/api/materias-primas/{id}/` | Eliminar materia prima | Administrador |
| POST | `/api/materias-primas/{id}/activar/` | Activar materia prima | Administrador |
| POST | `/api/materias-primas/{id}/desactivar/` | Desactivar materia prima | Administrador |
| GET | `/api/materias-primas/similares/` | Nombres iguales o parecidos (ayuda del formulario) | autenticado |
| GET | `/api/descartes/` | Listar descartes (`?fecha_desde=`, `?fecha_hasta=`, `?categoria=G\|S`, `?estado=`, `?id_galpon=`, `?page=`, `?page_size=`), paginado de a 16 | autenticado |
| POST | `/api/descartes/` | Crear descarte de galpón o de stock con líneas | Adm. / Operario |
| GET | `/api/descartes/{id}/` | Detalle de descarte | autenticado |
| PATCH | `/api/descartes/{id}/` | Modificar descarte PENDIENTE | Adm. / Operario |
| DELETE | `/api/descartes/{id}/` | Eliminar descarte PENDIENTE | Adm. / Operario |
| POST | `/api/descartes/{id}/finalizar/` | Finalizar y aplicar el efecto (lote o stock) | Adm. / Operario |
| GET | `/api/entradas/` | Listar entradas (`?fecha_desde=`, `?fecha_hasta=`, `?estado=`, `?id_galpon=`, `?id_materia_prima=`, `?page=`, `?page_size=`), paginado de a 16 | autenticado |
| POST | `/api/entradas/` | Crear entrada a un galpón con líneas | Adm. / Operario |
| GET | `/api/entradas/{id}/` | Detalle de entrada | autenticado |
| PATCH | `/api/entradas/{id}/` | Modificar entrada PENDIENTE | Adm. / Operario |
| DELETE | `/api/entradas/{id}/` | Eliminar entrada PENDIENTE | Adm. / Operario |
| POST | `/api/entradas/{id}/finalizar/` | Finalizar y descontar el stock de materias primas | Adm. / Operario |
| GET | `/api/salidas/` | Listar salidas (`?fecha_desde=`, `?fecha_hasta=`, `?estado=`, `?id_producto=`, `?page=`, `?page_size=`), paginado de a 16 | autenticado |
| POST | `/api/salidas/` | Crear salida de productos con líneas | Adm. / Operario |
| GET | `/api/salidas/{id}/` | Detalle de salida | autenticado |
| PATCH | `/api/salidas/{id}/` | Modificar salida PENDIENTE | Adm. / Operario |
| DELETE | `/api/salidas/{id}/` | Eliminar salida PENDIENTE | Adm. / Operario |
| POST | `/api/salidas/{id}/finalizar/` | Finalizar y descontar el stock de productos | Adm. / Operario |
| GET | `/api/proveedores/` | Listar proveedores (`?search=`, `?estado=`, `?page=`, `?page_size=`), paginado de a 16 | Adm. / Consulta |
| POST | `/api/proveedores/` | Crear proveedor | Adm. |
| GET | `/api/proveedores/{id}/` | Detalle de proveedor | Adm. / Consulta |
| PATCH | `/api/proveedores/{id}/` | Modificar proveedor | Adm. |
| DELETE | `/api/proveedores/{id}/` | Borrar proveedor (409 si tiene registros asociados) | Adm. |
| POST | `/api/proveedores/{id}/alta/` | Dar de alta | Adm. |
| POST | `/api/proveedores/{id}/baja/` | Dar de baja | Adm. |
| GET | `/api/proveedores/similares/` | Nombres iguales o parecidos | Adm. / Consulta |
| GET | `/api/compras/` | Listar compras (`?search=` por Nº de comprobante, `?categoria=M\|L`, `?estado=`, `?id_proveedor=`, `?fecha_desde=`, `?fecha_hasta=`, `?page=`, `?page_size=`), paginado de a 16 | Adm. / Consulta |
| POST | `/api/compras/` | Crear compra de materias primas o de lotes con líneas | Adm. |
| GET | `/api/compras/{id}/` | Detalle de compra | Adm. / Consulta |
| PATCH | `/api/compras/{id}/` | Modificar compra PENDIENTE | Adm. |
| DELETE | `/api/compras/{id}/` | Eliminar compra PENDIENTE (409 si está finalizada) | Adm. |
| POST | `/api/compras/{id}/finalizar/` | Finalizar: suma stock de materias primas o deja el lote por asignar | Adm. |
| GET | `/api/compras/lotes-pendientes/` | Lotes comprados esperando galpón | autenticado |
| GET | `/api/compras/proximo-comprobante/` | Número de comprobante con el que se guardaría la próxima compra | Adm. / Consulta |
| GET | `/api/informes/produccion/` | Informe de producción (`?fecha_desde=`, `?fecha_hasta=`, `?id_galpon=`) | Adm. / Consulta |
| GET | `/api/informes/lotes/` | Informe de lotes (`?estado=`, `?id_galpon=`) | Adm. / Consulta |
| GET | `/api/informes/materias-primas/` | Informe de materias primas (`?fecha_desde=`, `?fecha_hasta=`, `?id_materia_prima=`) | Adm. / Consulta |
| GET | `/api/informes/descartes/` | Informe de descartes (`?fecha_desde=`, `?fecha_hasta=`, `?id_galpon=`, `?tipo=`) | Adm. / Consulta |
| GET | `/api/informes/indicadores/` | Indicadores (`?indicador=postura\|mortandad\|consumo`, fechas, `?id_galpon=`, `?id_materia_prima=`) | Adm. / Consulta |
| GET | `/api/galpones/{id}/existencias/` | Existencia estimada de materias primas en el galpón | autenticado |
| — | `/admin/` | Panel de administración de Django | Administrador con `is_staff` |

Todas las peticiones, salvo el inicio de sesión, requieren el encabezado:

```
Authorization: Bearer <token>
```

---

## Integración continua (CI)

El proyecto usa **GitHub Actions** para correr los tests automáticamente.

El workflow (`.github/workflows/tests.yml`) se ejecuta en:

- Cualquier `push` a cualquier rama, excepto si los únicos archivos
  modificados son documentación (`docs/**` o `*.md`).
- Cualquier Pull Request hacia `develop` o `main` (siempre, sin excepción).

Cada ejecución levanta PostgreSQL como servicio Docker, instala las
dependencias, aplica las migraciones y corre `python manage.py test`. El
resultado aparece como ✅ o ❌ en la pestaña Actions de GitHub y en cada
commit.

**Protección de ramas:** el workflow reporta el resultado pero no bloquea
automáticamente el merge. Para hacerlo bloqueante hay que configurarlo en
GitHub (ver sección "Pendientes transversales" al final de este archivo).

**Agregar tests de una nueva feature:** crear `backend/<app>/tests.py` en la
rama correspondiente. El workflow los descubre y corre automáticamente junto
con los existentes — el archivo `tests.yml` no necesita modificarse.

---

## Flujo de trabajo con Git

- **`main`** — versión final del proyecto.
- **`develop`** — rama de integración; de acá se desprenden las features.
- **`feature/<nombre>`** o **`fix/<nombre>`** — una rama por funcionalidad.

En cada rama se programa, se prueba y se documenta la feature. La documentación
se agrega como `docs/docs-<feature>.md` e incluye los casos de uso cubiertos y
las decisiones de diseño tomadas. Al terminar, se integra a `develop` mediante
un Pull Request.

Los mensajes de commit siguen la convención **Conventional Commits**
(`tipo(alcance): descripción`). Ver `docs/convencion-commits.md`.

---

## Documentación

En `docs/`:

| Archivo | Contenido |
|---|---|
| `docs-usuarios.md` | Autenticación, gestión de usuarios, tests y permisos por rol (CU01 a CU08) |
| `docs-galpones.md` | Gestión de galpones, alta/baja lógica, operarios asignados y tests (CU09 a CU14) |
| `docs-lotes.md` | Gestión de lotes, ciclo de vida, plan de transición, vaciado sanitario y tests (CU42 a CU48) |
| `docs-productos.md` | Gestión de productos, activar/desactivar, stock calculado (recolecciones, descartes y salidas) y tests (CU49 a CU54) |
| `docs-recolecciones.md` | Recolección diaria, estructura cabecera-líneas, FK a lote, FK a usuario ("Cargado por"), estados y tests (CU24 a CU32) |
| `docs-materias-primas.md` | Gestión de materias primas, alerta de stock mínimo, stock calculado (descartes y entradas) y tests (CU55 a CU60) |
| `docs-descartes.md` | Descartes de galpón y de stock, finalización, impacto en lotes y stock, FK a usuario ("Cargado por") y tests (CU15 a CU23) |
| `docs-entradas.md` | Entradas de materias primas a galpones, finalización, stock de materias primas y tests (CU33 a CU41) |
| `docs-salidas.md` | Salidas de productos, finalización, stock de productos y tests (CU76 a CU84) |
| `docs-compras.md` | Compras de materias primas y de lotes, finalización, lotes pendientes de asignar a un galpón, stock de materias primas y tests |
| `docs-informes.md` | Informes de producción, lotes, materias primas y descartes, indicadores contra un objetivo, exportación a Excel y PDF, y tests (CU85 a CU89) |
| `docs-proveedores.md` | Gestión de proveedores, CUIT, teléfono argentino o internacional, nombres parecidos, permisos y tests (CU70 a CU75) |
| `convencion-commits.md` | Convención de mensajes de commit adoptada por el equipo |
| `modelo-relacional/` | Diagrama y documentación del modelo de datos |
| `Plan de Trabajo.pdf` | Plan de trabajo presentado a la facultad |
| `Anexo 1 Trabajo Final...docx` | Presentación de la idea de proyecto |
| `AviGest_Documentacion_Arquitectura.docx` | Documentación de arquitectura |

---

## Problemas frecuentes

**`UnicodeDecodeError: 'utf-8' codec can't decode byte 0xf3`**
No es un problema de codificación sino un fallo de conexión a la base de datos.
Cuando PostgreSQL está instalado en español, sus mensajes de error no son UTF-8
y ocultan la causa real. Verificar `DB_PASSWORD` en `.env` y que la base
`granja_avicola` exista.

**`"vite" no se reconoce como un comando`**
Faltan las dependencias del frontend: ejecutar `npm install` dentro de
`frontend/`.

**`ModuleNotFoundError` al ejecutar `manage.py`**
El entorno virtual no está activo. El prompt debe mostrar `(.venv)`.

**El frontend no carga datos**
Verificar que el backend esté en ejecución en el puerto 8000 y que el archivo
`frontend/.env` apunte a `http://localhost:8000`.

**Error de CORS en la consola del navegador**
El backend autoriza `http://localhost:5173` por defecto. Si el frontend corre en
otro puerto, agregarlo a `CORS_ALLOWED_ORIGINS` en `backend/.env`.

**Los tests fallan con error de conexión a la base**
Verificar que PostgreSQL esté corriendo y que `DB_HOST`, `DB_USER` y
`DB_PASSWORD` en `.env` sean correctos. Los tests usan la misma configuración
del `.env`, pero crean su propia base `test_granja_avicola` automáticamente.

---

## Próximos pasos

1. **Dashboard con alertas.** Es el único módulo que sigue como vista previa.
   Se desarrolla después de refinar lo ya construido.
2. **Fixes planificados**, a trabajar en ramas `fix/*` hacia `develop`:
   - **Recolecciones:** ocultar "Eliminar" en las finalizadas y agregar filtros
     por fecha desde, fecha hasta y lote.
   - **Paginación** en Recolecciones, Descartes, Salidas, Entradas y Compras
     (y evaluar si hace falta en las secciones de tarjetas: Galpones, Materias
     Primas, Proveedores, Usuarios y Productos).
   - **Lotes:** limitar la columna "Finalizado", impedir asignar un lote a un
     galpón cuya capacidad no alcanza y mostrar la capacidad del galpón en el
     formulario.
   - **Proveedores:** corregir el desborde visual del email largo y mostrar sus
     compras recientes en el detalle.
   - **Compras:** botón "Agregar materia prima" que lleve al alta de una nueva,
     más medios de pago (débito y crédito) y guardado atómico (transacción).
   - **Materias Primas:** mostrar las compras recientes en el detalle.
   - **Productos y Galpones:** responder 409 con un mensaje claro al eliminar
     registros con datos asociados.
   - **Registro de auditoría** (`ModeloAuditable`, ver más abajo).
   - **Limpieza de mockups** estáticos que ya no se usan.
3. **Despliegue.**

Cada módulo se implementa con el mismo patrón: modelo y migración en el
backend, endpoints con DRF, permisos por rol, pantalla React, tests en
`backend/<app>/tests.py`, y documentación en `docs/docs-<feature>.md`.

### Pendientes transversales

Mejoras que aplican a múltiples módulos y conviene implementar cuando haya
dos o tres modelos funcionales, para aplicarlas de una vez y con consistencia:

**Registro de auditoría.** Los módulos de Recolección, Descartes y Entradas ya registran el
usuario responsable de la carga en el campo `id_usuario`. Para los demás módulos,
una opción escalable es agregar una clase base abstracta `ModeloAuditable`
en `backend/core/models.py` con los campos `creado_por`, `modificado_por`,
`fecha_creacion` y `fecha_modificacion`. Cada modelo la hereda con una sola
línea. Permite saber quién modificó un lote, quién dio de baja un galpón, etc.

**Protección de ramas en GitHub.** El workflow de CI ya corre los tests y
reporta el resultado en cada push. Para que ese resultado sea bloqueante
(impedir el merge si los tests fallan), hay que activarlo en GitHub:
Settings → Branches → Branch protection rules → "Require status checks to
pass before merging" → seleccionar `Django Tests`. Aplicar en `develop` y
`main`.
