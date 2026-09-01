# AvíGest — Sistema Web de Gestión para una Granja Avícola Productora de Huevos

Proyecto Final de Ingeniería en Computación — FACET, UNT

**Integrantes:**
- Piazza, Santiago Nicolás
- Vargas, Antonio Jesús

**Tecnologías:** React · Django + Django REST Framework · PostgreSQL

---

## Estado actual

Primer módulo funcional del sistema: **Galpones**, con frontend real (React), backend real (Django + Django REST Framework) y base de datos real (PostgreSQL).

El resto de las pantallas (Lotes, Recolección, Descartes, Salidas, Entradas, Materias Primas, Compras, Proveedores, Usuarios, Informes, y el login) se ven exactamente igual que en el mockup aprobado por el tutor — usan el HTML/CSS real del mockup — pero **no tienen funcionalidad todavía**: no leen ni guardan nada en la base de datos, y sus botones no hacen nada. Es solo la cáscara visual, para que la app se sienta completa al mostrarla. Se van implementando de a uno, siguiendo el mismo patrón que Galpones.

## Estructura del proyecto

```
Proyecto-Final/
├── docs/        Documentación de la materia (anexo, plan de trabajo, arquitectura)
├── backend/     Django + DRF + PostgreSQL — API REST de Galpones
└── frontend/    React + Vite — app completa (shell + Galpones funcional + resto visual)
```

El modelo `Galpon` (`backend/galpones/models.py`) replica exactamente la tabla `Galpones` del modelo relacional: `idGalpon`, `galpon`, `latitud`, `longitud`, `superficie`, `capacidad`, `estado`, `descripcion`. No se agregó ni se inventó ningún campo.

### Cómo está armado el frontend

- `src/pages/LoginPage.jsx` y `src/pages/AppLayout.jsx` (sidebar): navegación real con `react-router-dom`, sin autenticación real todavía.
- `src/pages/GalponesPage.jsx`: la única pantalla conectada a la API real (`/api/galpones/`).
- `src/pages/static/raw/*.html`: el HTML exacto de cada pantalla del mockup (Lotes, Recolección, Descartes, Salidas, Entradas, Materias Primas, Compras, Proveedores, Usuarios, Informes, Dashboard), renderizado tal cual por `src/pages/static/StaticPage.jsx`. Cuando se implemente alguno de estos módulos, ese archivo se reemplaza por una página React real (como ya pasó con Galpones) y se lo conecta a su propio endpoint en el backend.

## 1. Requisitos previos

Instalar en tu computadora (una sola vez):

- **Python 3.10 o superior** — [python.org/downloads](https://www.python.org/downloads/)
- **Node.js 18 o superior** — [nodejs.org](https://nodejs.org/)
- **PostgreSQL 14 o superior** — [postgresql.org/download](https://www.postgresql.org/download/) (en Mac, la forma más simple es `brew install postgresql@16 && brew services start postgresql@16`)

Verificá que estén instalados:

```bash
python3 --version
node --version
psql --version
```

## 2. Crear la base de datos

Con PostgreSQL corriendo, creá la base y (opcionalmente) un usuario dedicado. Con el usuario `postgres` por defecto alcanza para desarrollo local:

```bash
createdb granja_avicola
```

Si te pide usuario/contraseña o querés un usuario propio en vez del `postgres` por defecto:

```sql
-- conectate con: psql postgres
CREATE USER granja_user WITH PASSWORD 'granja_pass';
CREATE DATABASE granja_avicola OWNER granja_user;
```

## 3. Backend (Django + DRF)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # en Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Editá .env si tu usuario/contraseña/puerto de PostgreSQL son distintos
# a los valores por defecto (DB_USER=postgres, DB_PASSWORD=postgres, DB_PORT=5432)

python manage.py migrate
python manage.py createsuperuser   # opcional, para entrar a /admin/
python manage.py runserver
```

El backend queda corriendo en `http://localhost:8000`. Endpoints disponibles:

| Método | URL                        | Acción                          |
|--------|----------------------------|----------------------------------|
| GET    | `/api/galpones/`           | Listar (soporta `?search=` y `?estado=A/I`) |
| POST   | `/api/galpones/`           | Crear                            |
| GET    | `/api/galpones/{id}/`      | Ver detalle                      |
| PATCH  | `/api/galpones/{id}/`      | Editar                           |
| DELETE | `/api/galpones/{id}/`      | Eliminar                         |
| —      | `/admin/`                  | Panel de administración de Django |

Ya viene probado end-to-end: crear, listar, editar, validaciones (capacidad/superficie deben ser mayores a 0) y eliminar funcionan correctamente contra PostgreSQL real.

## 4. Frontend (React + Vite)

En otra terminal, con el backend corriendo:

```bash
cd frontend
npm install
cp .env.example .env    # por defecto ya apunta a http://localhost:8000
npm run dev
```

Abrí `http://localhost:5173` en el navegador. Vas a entrar por la pantalla de login (visual, cualquier clic en "Ingresar" te deja pasar) y de ahí al panel completo con el sidebar de siempre. La sección **Galpones** está conectada a la API real: podés crear, ver el detalle, editar y eliminar galpones, y los cambios quedan guardados en PostgreSQL. El resto de las secciones del menú se ven igual que en el mockup pero son solo visuales por ahora.

## 5. Qué revisar si algo falla

- **El frontend no carga datos / error de conexión**: confirmá que el backend esté corriendo en el puerto 8000 (`python manage.py runserver`) y que no haya errores en esa terminal.
- **Error de conexión a la base de datos** al correr `migrate` o `runserver`: revisá que PostgreSQL esté corriendo (`pg_isready`) y que los datos en `backend/.env` coincidan con tu usuario/contraseña real.
- **CORS bloqueado en la consola del navegador**: el backend ya permite `http://localhost:5173` por defecto (ver `CORS_ALLOWED_ORIGINS` en `backend/.env`); si corrés el frontend en otro puerto, agregalo ahí.

## 6. Documentación

En `docs/` está toda la documentación de la materia:

- `Plan de Trabajo.pdf`
- `Anexo 1 Trabajo Final-Piazza Santiago Nicolás-Vargas Antonio Jesús.docx`
- `AviGest_Documentacion_Arquitectura.docx`

## 7. Próximos pasos

Funcionalmente este repo cubre únicamente Galpones, tal como pidió el tutor — es lo único con backend real detrás. El resto de los módulos (Lotes, Recolección diaria, Descartes, Salidas, Entradas, Materias Primas, Compras, Proveedores, Usuarios, Informes) ya se ven en la app (mismo diseño aprobado), pero son pantallas estáticas sin datos reales. Se van implementando de a uno siguiendo el mismo patrón que Galpones: modelo en `backend/`, endpoints DRF, y reemplazar el `StaticPage` correspondiente por una página React real en `frontend/src/pages/`.
