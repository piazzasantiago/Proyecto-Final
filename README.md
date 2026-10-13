# AvíGest — Sistema Web de Gestión para una Granja Avícola Productora de Huevos

Proyecto Final de Ingeniería en Computación — FACET, UNT

**Integrantes:**
- Piazza, Santiago Nicolás
- Vargas, Antonio Jesús

**Tecnologías:** React · Django + Django REST Framework · PostgreSQL

---

## Estado actual

El sistema cuenta con **autenticación real y control de acceso por rol**, y seis
módulos funcionales de punta a punta: **Usuarios**, **Galpones**, **Lotes de
Gallinas**, **Productos** y **Recolección diaria**.

| Módulo | Casos de uso | Estado |
|---|---|---|
| Autenticación | CU01, CU02 | Funcional |
| Gestión de Usuarios | CU03 a CU08 | Funcional |
| Gestión de Galpones | CU09 a CU14 | Funcional |
| Gestión de Lotes | CU42 a CU48 | Funcional |
| Gestión de Productos | CU49 a CU54 | Funcional |
| Recolección diaria | CU24 a CU32 | Funcional |
| Descartes, Salidas, Entradas, Materias Primas, Compras, Proveedores, Informes, Dashboard | — | Solo vista previa |

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

## 5. Correr los tests

```bash
cd backend
python manage.py test --verbosity=2
```

Django crea automáticamente una base de datos temporaria, corre todos los tests
y la elimina al terminar. No toca la base de desarrollo.

```
Ran 254 tests in ~Xs
OK
```

Para correr solo un módulo:

```bash
python manage.py test usuarios
python manage.py test galpones
python manage.py test lotes
python manage.py test productos
python manage.py test recolecciones
```

---

## Endpoints principales

| Método | Ruta | Descripción | Rol |
|---|---|---|---|
| POST | `/api/auth/login/` | Iniciar sesión | — |
| GET | `/api/auth/me/` | Usuario autenticado | autenticado |
| POST | `/api/auth/logout/` | Cerrar sesión | autenticado |
| GET | `/api/galpones/` | Listar galpones (`?search=`, `?estado=`) | autenticado |
| POST | `/api/galpones/` | Crear galpón | Administrador |
| PATCH | `/api/galpones/{id}/` | Modificar galpón | Administrador |
| DELETE | `/api/galpones/{id}/` | Eliminar galpón | Administrador |
| POST | `/api/galpones/{id}/alta/` | Activar galpón | Administrador |
| POST | `/api/galpones/{id}/baja/` | Dar de baja galpón | Administrador |
| GET | `/api/usuarios/` | Listar usuarios (`?search=`, `?rol=`, `?estado=`) | Administrador |
| POST | `/api/usuarios/` | Crear usuario | Administrador |
| PATCH | `/api/usuarios/{id}/` | Modificar usuario | Administrador |
| DELETE | `/api/usuarios/{id}/` | Eliminar usuario | Administrador |
| POST | `/api/usuarios/{id}/alta/` | Dar de alta usuario | Administrador |
| POST | `/api/usuarios/{id}/baja/` | Dar de baja usuario | Administrador |
| POST | `/api/usuarios/{id}/restablecer-password/` | Restablecer contraseña | Administrador |
| GET | `/api/lotes/` | Listar lotes (`?estado=`, `?id_galpon=`) | autenticado |
| POST | `/api/lotes/` | Crear lote con plan de transición | Administrador |
| GET | `/api/lotes/{id}/` | Detalle del lote | autenticado |
| PATCH | `/api/lotes/{id}/` | Modificar lote o plan | Administrador |
| DELETE | `/api/lotes/{id}/` | Eliminar lote | Administrador |
| POST | `/api/lotes/{id}/iniciar-produccion/` | Transición → Producción | Administrador |
| POST | `/api/lotes/{id}/vaciar/` | Producción/Transición → Finalizado | Administrador |
| GET | `/api/recolecciones/` | Listar recolecciones (`?id_galpon=`, `?estado=`) | autenticado |
| POST | `/api/recolecciones/` | Crear recolección con líneas | Adm. / Operario |
| GET | `/api/recolecciones/{id}/` | Detalle de recolección | autenticado |
| PATCH | `/api/recolecciones/{id}/` | Modificar recolección PENDIENTE | Adm. / Operario |
| DELETE | `/api/recolecciones/{id}/` | Eliminar recolección | Administrador |
| POST | `/api/recolecciones/{id}/finalizar/` | Marcar recolección como Finalizada | Adm. / Operario |
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
| `docs-productos.md` | Gestión de productos, activar/desactivar, stock manual y tests (CU49 a CU54) |
| `docs-recolecciones.md` | Recolección diaria, estructura cabecera-líneas, FK a lote, estados y tests (CU24 a CU32) |
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

1. **`feature/descartes`** — Descartes (CU15 a CU23).

2. **`feature/salidas`** — Registro de salidas de productos de la granja
   (venta u otro destino). Mismo patrón cabecera-líneas que Recolección:
   una `Salida` con N `LineaSalida` (producto + cantidad). Depende de que
   existan Recolecciones y Descartes, ya que el stock real de cada producto
   se calcula como `recolecciones − descartes − salidas`.

3. Módulos de insumos: Entradas, Materias Primas, Compras y Proveedores.

4. **Informes e indicadores productivos** (CU85 a CU89).

Cada módulo se implementa con el mismo patrón: modelo y migración en el
backend, endpoints con DRF, permisos por rol, pantalla React, tests en
`backend/<app>/tests.py`, y documentación en `docs/docs-<feature>.md`.

### Pendientes transversales

Mejoras que aplican a múltiples módulos y conviene implementar cuando haya
dos o tres modelos funcionales, para aplicarlas de una vez y con consistencia:

**Registro de auditoría.** Agregar una clase base abstracta `ModeloAuditable`
en `backend/core/models.py` con los campos `creado_por`, `modificado_por`,
`fecha_creacion` y `fecha_modificacion`. Cada modelo la hereda con una sola
línea. Permite saber quién cargó cada recolección, quién modificó un lote,
quién dio de baja un galpón.

**Protección de ramas en GitHub.** El workflow de CI ya corre los tests y
reporta el resultado en cada push. Para que ese resultado sea bloqueante
(impedir el merge si los tests fallan), hay que activarlo en GitHub:
Settings → Branches → Branch protection rules → "Require status checks to
pass before merging" → seleccionar `Django Tests`. Aplicar en `develop` y
`main`.
