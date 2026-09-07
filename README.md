# AvíGest — Sistema Web de Gestión para una Granja Avícola Productora de Huevos

Proyecto Final de Ingeniería en Computación — FACET, UNT

**Integrantes:**
- Piazza, Santiago Nicolás
- Vargas, Antonio Jesús

**Tecnologías:** React · Django + Django REST Framework · PostgreSQL

---

## Estado actual

El sistema cuenta con **autenticación real y control de acceso por rol**, y dos
módulos funcionales de punta a punta: **Galpones** y **Usuarios**.

| Módulo | Casos de uso | Estado |
|---|---|---|
| Autenticación | CU01, CU02 | Funcional |
| Gestión de Usuarios | CU03 a CU08 | Funcional |
| Gestión de Galpones | CU09 a CU14 | Funcional (con permisos por rol) |
| Lotes, Recolección, Descartes, Salidas, Entradas, Materias Primas, Compras, Proveedores, Informes, Dashboard | — | Solo vista previa |

Las secciones marcadas como *vista previa* muestran el HTML del mockup aprobado
por el tutor: **no leen ni guardan datos**, y sus botones no realizan
operaciones. Sirven para presentar la aplicación completa mientras se
implementan los módulos restantes, uno por uno, siguiendo el mismo patrón que
Galpones y Usuarios.

### Acceso por rol

El sistema define tres roles, y cada uno accede a un conjunto distinto de
secciones y operaciones:

- **Administrador:** acceso total, incluida la gestión de usuarios.
- **Operario:** carga y consulta de la operación diaria. No accede a Usuarios,
  Compras ni Proveedores.
- **Consulta:** solo lectura de la información productiva e informes.

El detalle completo está en `docs/docs-usuarios.md`.

---

## Estructura del proyecto

```
Proyecto-Final/
├── docs/        Documentación del proyecto y de cada feature
├── backend/     Django + DRF + PostgreSQL — API REST
└── frontend/    React + Vite — interfaz web
```

### Backend

```
backend/
├── config/          configuración del proyecto y rutas raíz
├── usuarios/        modelo Usuario, autenticación JWT y permisos por rol
├── galpones/        módulo de Galpones
└── manage.py
```

### Frontend

```
frontend/src/
├── api/         cliente HTTP y funciones de la API, una por caso de uso
├── config/      matriz rol × sección del menú
├── context/     estado de la sesión
├── components/  componentes reutilizables
├── pages/       una pantalla por módulo
│   └── static/  HTML de los módulos aún no implementados
└── index.css    estilos del sistema
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

---

## Endpoints principales

| Método | Ruta | Descripción | Rol |
|---|---|---|---|
| POST | `/api/auth/login/` | Iniciar sesión | — |
| GET | `/api/auth/me/` | Usuario autenticado | autenticado |
| POST | `/api/auth/logout/` | Cerrar sesión | autenticado |
| GET | `/api/galpones/` | Listar galpones (`?search=`, `?estado=`) | autenticado |
| POST · PATCH · DELETE | `/api/galpones/` | Alta, modificación y baja | Administrador |
| GET | `/api/usuarios/` | Listar usuarios (`?search=`, `?rol=`, `?estado=`) | Administrador |
| POST · PATCH · DELETE | `/api/usuarios/` | Alta, modificación y baja | Administrador |
| POST | `/api/usuarios/{id}/alta/` y `/baja/` | Alta y baja lógica | Administrador |
| POST | `/api/usuarios/{id}/restablecer-password/` | Restablecer contraseña | Administrador |
| — | `/admin/` | Panel de administración de Django | Administrador con `is_staff` |

Todas las peticiones, salvo el inicio de sesión, requieren el encabezado:

```
Authorization: Bearer <token>
```

---

## Flujo de trabajo con Git

- **`main`** — versión final del proyecto.
- **`develop`** — rama de integración; de acá se desprenden las features.
- **`feature/<nombre>`** o **`fix/<nombre>`** — una rama por funcionalidad.

En cada rama se programa, se prueba y se documenta la feature. La documentación
se agrega como `docs/docs-<feature>.md` e incluye los casos de uso cubiertos y
las decisiones de diseño tomadas. Al terminar, se integra a `develop` mediante
un Pull Request.

---

## Documentación

En `docs/`:

| Archivo | Contenido |
|---|---|
| `docs-usuarios.md` | Autenticación y gestión de usuarios (CU01 a CU08) |
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

---

## Próximos pasos

1. **Lotes de Gallinas** (CU42 a CU48), incluyendo el plan de transición y el
   vaciado sanitario.
2. **Recolección diaria** (CU24 a CU32), primer módulo con estructura de
   cabecera y líneas.
3. **Descartes** (CU15 a CU23).
4. Módulos de insumos: Entradas, Materias Primas, Compras y Proveedores.
5. **Informes e indicadores productivos** (CU85 a CU89).

Cada módulo se implementa con el mismo patrón: modelo y migración en el
backend, endpoints con DRF, permisos por rol, pantalla React, y documentación
en `docs/`.
