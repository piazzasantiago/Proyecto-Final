# Gestión de Usuarios y Autenticación

**Rama:** `feature/gestion-usuarios`
**Casos de uso:** CU01, CU02, CU03, CU04, CU05, CU06, CU07, CU08

Primera feature con autenticación real del sistema. Incorpora el modelo de
usuario propio, el inicio de sesión con JWT, el control de acceso por rol,
la gestión completa de usuarios, tests automatizados y CI con GitHub Actions.

---

## 1. Alcance

### Qué incluye

- Modelo `Usuario` propio, que reemplaza al usuario por defecto de Django.
- Inicio y cierre de sesión con tokens JWT.
- Control de acceso por rol (Administrador, Operario, Consulta) aplicado a
  todos los endpoints, incluidos los de Galpones.
- ABM completo de usuarios con búsqueda, filtros, alta y baja lógica.
- Restablecimiento de contraseña por parte del Administrador.
- Interfaz React conectada a la API, con menú y rutas filtradas por rol.
- Matriz de visibilidad de secciones por rol, definida en `config/menu.js`.
- Tests automatizados del backend (35 tests en 4 clases).
- Workflow de CI con GitHub Actions que corre los tests en cada push.

### Qué no incluye

- Recupero automático de contraseña por email. El sistema muestra un cartel
  indicando que hay que pedirle ayuda a un administrador.
- Refresh automático del token: la sesión dura 8 horas y luego hay que
  volver a iniciar sesión.
- Asignación de operarios a galpones (tabla `UsuariosDelGalpon` del modelo
  relacional). Se implementará junto con el módulo que la requiera.

---

## 2. Casos de uso

### CU01 – Iniciar Sesión

**Actor:** cualquier usuario del sistema.
**Precondición:** el usuario existe y está en estado Activo.

**Flujo principal**

1. El usuario accede a la pantalla de inicio de sesión.
2. Ingresa su nombre de usuario o su email, y su contraseña.
3. El sistema valida las credenciales.
4. El sistema genera un token de sesión y lo devuelve junto con los datos
   del usuario.
5. El sistema redirige al panel principal, mostrando únicamente las secciones
   habilitadas para su rol.

**Flujos alternativos**

- **3a. Credenciales incorrectas:** el sistema muestra "Usuario o contraseña
  incorrectos" y permanece en la pantalla de inicio de sesión.
- **3b. Usuario dado de baja:** el sistema rechaza el acceso con el mismo
  mensaje genérico, sin revelar que el usuario existe.
- **2a. El usuario no recuerda su contraseña:** selecciona "¿Olvidaste tu
  contraseña?" y el sistema informa que debe solicitar a un administrador que
  se la restablezca.

**Postcondición:** el usuario queda autenticado por 8 horas.

---

### CU02 – Cerrar Sesión

**Actor:** usuario autenticado.

**Flujo principal**

1. El usuario selecciona "Cerrar sesión".
2. El sistema descarta el token de sesión.
3. El sistema redirige a la pantalla de inicio de sesión.

**Postcondición:** las pantallas del sistema dejan de ser accesibles hasta
un nuevo inicio de sesión.

---

### CU03 – Buscar Usuario

**Actor:** Administrador.

**Flujo principal**

1. El Administrador accede a la sección Usuarios.
2. El sistema muestra el listado de usuarios registrados.
3. El Administrador ingresa un texto de búsqueda o aplica filtros por rol
   y por estado.
4. El sistema muestra los usuarios que cumplen los criterios.
5. El Administrador selecciona un usuario y el sistema muestra su detalle.

**Flujos alternativos**

- **4a. Sin resultados:** el sistema informa que no hay usuarios que
  coincidan con la búsqueda.

**Notas:** la búsqueda se realiza sobre nombre, apellido, nombre de usuario,
email y DNI.

---

### CU04 – Nuevo Usuario

**Actor:** Administrador.

**Flujo principal**

1. El Administrador selecciona "Nuevo usuario".
2. El sistema muestra el formulario de alta.
3. El Administrador completa nombre, apellido, nombre de usuario, email,
   DNI, rol y una contraseña inicial.
4. El sistema valida los datos.
5. El sistema registra el usuario con estado Activo.
6. El sistema muestra el usuario creado en el listado.

**Flujos alternativos**

- **4a. Nombre de usuario, email o DNI ya registrados:** el sistema indica
  cuál es el dato duplicado y no crea el usuario.
- **4b. Contraseña menor a 8 caracteres:** el sistema lo informa y no crea
  el usuario.

**Postcondición:** el usuario puede iniciar sesión con la contraseña asignada.

---

### CU05 – Modificar Usuario

**Actor:** Administrador.

**Flujo principal**

1. El Administrador selecciona un usuario y elige "Editar".
2. El sistema muestra el formulario con los datos actuales.
3. El Administrador modifica los datos que necesite.
4. El sistema valida y guarda los cambios.

**Flujos alternativos**

- **4a. Datos duplicados con otro usuario:** el sistema lo informa y no
  guarda.

**Notas:** la contraseña no se modifica desde este caso de uso. Para eso
existe el restablecimiento.

---

### CU06 – Borrar Usuario

**Actor:** Administrador.

**Flujo principal**

1. El Administrador selecciona un usuario y elige "Eliminar".
2. El sistema solicita confirmación.
3. El Administrador confirma.
4. El sistema elimina el registro.

**Flujos alternativos**

- **1a. El usuario seleccionado es el propio Administrador:** el sistema
  impide la operación.
- **3a. El usuario tiene registros asociados** (compras, recolecciones,
  descartes, entradas o salidas que cargó): el sistema no lo elimina y responde
  `409 Conflict` con un mensaje que indica qué registros lo impiden y sugiere
  darlo de baja (F-18/F-19). La interfaz lo muestra en un cartel dentro del
  panel de detalle, sin ocultar el listado.

**Notas:** el borrado es físico y solo se permite si el usuario no cargó nada.
Para conservar el historial de lo que un usuario registró hay que darlo de
baja (CU08) en lugar de eliminarlo.

---

### CU07 – Dar de Alta Usuario

**Actor:** Administrador.
**Precondición:** el usuario está en estado Inactivo.

**Flujo principal**

1. El Administrador selecciona un usuario dado de baja y elige "Dar de alta".
2. El sistema cambia su estado a Activo.

**Flujos alternativos**

- **1a. El usuario ya está activo:** el sistema lo informa (409 Conflict).

**Postcondición:** el usuario vuelve a poder iniciar sesión.

---

### CU08 – Dar de Baja Usuario

**Actor:** Administrador.
**Precondición:** el usuario está en estado Activo.

**Flujo principal**

1. El Administrador selecciona un usuario y elige "Dar de baja".
2. El sistema cambia su estado a Inactivo.

**Flujos alternativos**

- **1a. El usuario seleccionado es el propio Administrador:** el sistema
  impide la operación, para evitar que quede sin acceso al sistema.
- **1b. El usuario ya está dado de baja:** el sistema lo informa (409 Conflict).

**Postcondición:** el usuario no puede iniciar sesión, pero se conserva su
registro y el historial asociado.

---

### Caso de uso adicional: Restablecer Contraseña de Usuario

No figura en el listado original de casos de uso, pero es necesario: como el
sistema no envía correos de recupero, el Administrador debe poder asignar una
contraseña provisoria.

**Actor:** Administrador.

**Flujo principal**

1. El Administrador selecciona un usuario y elige "Restablecer contraseña".
2. El Administrador ingresa una contraseña provisoria de al menos 8 caracteres.
   El campo arranca visible para que pueda leerla y comunicársela al usuario.
3. El sistema reemplaza la contraseña del usuario.
4. El Administrador comunica la contraseña provisoria al usuario.

**Notas:** no se solicita la contraseña anterior, porque el Administrador
no la conoce. **Se propone incorporarlo al listado de casos de uso.**

---

## 3. Matriz rol × caso de uso

### Autenticación y usuarios

| Caso de uso | Administrador | Operario | Consulta |
|---|:---:|:---:|:---:|
| CU01 Iniciar Sesión | Sí | Sí | Sí |
| CU02 Cerrar Sesión | Sí | Sí | Sí |
| CU03 Buscar Usuario | Sí | No | No |
| CU04 Nuevo Usuario | Sí | No | No |
| CU05 Modificar Usuario | Sí | No | No |
| CU06 Borrar Usuario | Sí | No | No |
| CU07 Dar de Alta Usuario | Sí | No | No |
| CU08 Dar de Baja Usuario | Sí | No | No |
| Restablecer Contraseña | Sí | No | No |

### Visibilidad de secciones en el menú

| Sección | Administrador | Operario | Consulta |
|---|:---:|:---:|:---:|
| Dashboard | Sí | Sí | Sí |
| Galpones | Sí (CRUD) | Sí (consulta) | Sí (consulta) |
| Lotes de Gallinas | Sí (CRUD) | Sí (consulta) | Sí (consulta) |
| Recolección diaria | Sí (CRUD) | Sí (CRUD) | Sí (consulta) |
| Entradas | Sí (CRUD) | Sí (CRUD) | Sí (consulta) |
| Descartes | Sí (CRUD) | Sí (CRUD) | Sí (consulta) |
| Salidas | Sí (CRUD) | Sí (CRUD) | Sí (consulta) |
| Materias Primas | Sí (CRUD) | Sí (consulta) | Sí (consulta) |
| Compras | Sí (CRUD) | No | Sí (consulta) |
| Proveedores | Sí (CRUD) | No | Sí (consulta) |
| Productos | Sí (CRUD) | No | Sí (consulta) |
| Informes | Sí | No | Sí |
| Usuarios | Sí (CRUD) | No | No |

**Importante:** la columna "visibilidad" controla si el enlace aparece en el
menú y si la ruta es accesible. Los permisos de escritura dentro de cada
sección (CRUD vs solo consulta) se implementan en el `permission_classes` del
ViewSet de cada módulo cuando se desarrolle. La fuente única de la matriz es
`frontend/src/config/menu.js`.

---

## 4. Modelo de datos

Corresponde a la tabla `Usuarios` del modelo relacional.

| Campo | Tipo | Restricciones |
|---|---|---|
| `idUsuario` | AutoField | Clave primaria |
| `nombre` | VARCHAR(100) | Obligatorio |
| `apellido` | VARCHAR(100) | Obligatorio |
| `usuario` | VARCHAR(100) | Obligatorio, único |
| `email` | VARCHAR(150) | Obligatorio, único |
| `dni` | VARCHAR(15) | Obligatorio, único |
| `password` | VARCHAR(128) | Hash PBKDF2, gestionado por Django |
| `rol` | CHAR(1) | A (Administrador), O (Operario), C (Consulta) |
| `estado` | CHAR(1) | A (Activo), I (Inactivo) |
| `is_staff` | BOOLEAN | Acceso al panel `/admin/` de Django |

**Propiedades calculadas (no son columnas):**

- `nombre_completo` — concatena nombre y apellido.
- `es_administrador` — `rol == "A"`.
- `is_active` — se deriva de `estado`. Django consulta este atributo al
  autenticar; un usuario dado de baja no puede iniciar sesión.

---

## 5. Endpoints

| Caso de uso | Método | Ruta | Rol |
|---|---|---|---|
| CU01 | POST | `/api/auth/login/` | — |
| CU02 | POST | `/api/auth/logout/` | autenticado |
| Usuario actual | GET | `/api/auth/me/` | autenticado |
| CU03 | GET | `/api/usuarios/` | Administrador |
| CU04 | POST | `/api/usuarios/` | Administrador |
| CU05 | PATCH | `/api/usuarios/{id}/` | Administrador |
| CU06 | DELETE | `/api/usuarios/{id}/` | Administrador |
| CU07 | POST | `/api/usuarios/{id}/alta/` | Administrador |
| CU08 | POST | `/api/usuarios/{id}/baja/` | Administrador |
| Restablecer contraseña | POST | `/api/usuarios/{id}/restablecer-password/` | Administrador |

**Filtros de CU03:** `?search=`, `?rol=A|O|C`, `?estado=A|I`

**Respuesta del login:**

```json
{
  "access": "eyJhbGci...",
  "refresh": "eyJhbGci...",
  "usuario": {
    "id_usuario": 1,
    "usuario": "jperez",
    "rol": "A",
    "rol_display": "Administrador",
    "nombre_completo": "Juan Pérez",
    ...
  }
}
```

Las peticiones posteriores envían el token en el encabezado:

```
Authorization: Bearer <access>
```

---

### Paginación del listado

`GET /api/usuarios/` devuelve los resultados paginados de a **16 registros**
(`?page=N`), con la forma `count`, `next`, `previous` y `results`. Se puede pedir
otro tamaño con `?page_size=` (máximo 100) y los filtros y la búsqueda se aplican
**antes** de paginar. Usa `PaginacionListado` (`backend/config/pagination.py`), la
misma clase que Recolecciones.

Las tarjetas se paginan y la barra de paginación queda debajo de la grilla (`src/pages/UsuariosPage.jsx`): "Mostrando X–Y de N", Anterior / Siguiente, números de
página clickeables y selector de elementos por página (la barra se muestra siempre, también con una sola página), que se recuerda en el
navegador (`useTamanoPagina("usuarios")`). Al cambiar un filtro o la búsqueda se vuelve
a la página 1, y si al eliminar un registro la página queda vacía se retrocede a
la anterior. `listOperarios` acepta parámetros y el formulario de galpones lo consume con `traerTodas`, de modo que la lista de operarios no se corta en 16.

Tests: `PaginacionUsuariosTests` en `backend/config/tests_pagination.py` (7 tests: 16 por página,
última página con el resto, `page_size`, páginas sin repetidos, página inexistente
→ 404 y filtro aplicado antes de paginar).

## 6. Tests automatizados

Los tests viven en `backend/usuarios/tests.py` y cubren los casos de uso de
esta feature. Se organizan en cuatro clases, cada una independiente: Django
crea una base temporaria al principio y la destruye al terminar.

### Estructura

| Clase | Tests | Qué cubre |
|---|:---:|---|
| `LoginTests` | 7 | CU01: credenciales, email, mensaje genérico, usuario inactivo |
| `MeTests` | 3 | Token válido, sin token, token inválido |
| `PermisosPorRolTests` | 8 | Los tres roles × usuarios y galpones |
| `ABMUsuariosTests` | 17 | CU03 a CU08 completo y restablecimiento de contraseña |
| **Total** | **35** | |

### Cómo correrlos localmente

```bash
cd backend
python manage.py test --verbosity=2
```

`--verbosity=2` muestra el nombre de cada test y si pasó (`ok`) o falló
(`FAIL`). Sin ese flag solo muestra el total.

### Cómo escalar los tests a futuras features

Cada nueva app de Django tiene su propio `tests.py`:

```
backend/lotes/tests.py       ← se crea con la feature de Lotes
backend/recoleccion/tests.py ← se crea con esa feature
```

El comando `python manage.py test` los descubre y los corre todos juntos
automáticamente. No hace falta modificar ningún archivo de configuración.

### Decisiones sobre los tests

**No se implementaron tests de frontend.** Los tests del backend cubren la
API completa (modelo, serializer, permisos, respuesta HTTP), que es donde
vive la lógica del sistema. La configuración de Jest con React en Vite tiene
un costo significativo que no se justifica en esta etapa. Se puede incorporar
más adelante comenzando por `config/menu.js`, que es JavaScript puro sin
dependencias de React.

---

## 7. Integración continua (CI con GitHub Actions)

El workflow `.github/workflows/tests.yml` corre automáticamente en cada push.

### Cuándo se ejecuta

| Situación | ¿Corre? |
|---|:---:|
| Push con solo cambios en `docs/` o `*.md` | No |
| Push con cualquier otro archivo | Sí |
| Pull Request hacia `develop` o `main` | Siempre |

Los pushes de documentación pura no disparan el CI porque no pueden romper
el código. Los PR hacia ramas protegidas siempre corren, sin excepción.

### Qué hace el workflow

1. Levanta PostgreSQL 16 como servicio Docker.
2. Instala Python 3.11 y las dependencias del backend.
3. Crea un archivo `.env` con las credenciales del entorno de CI.
4. Verifica la configuración de Django (`manage.py check`).
5. Aplica las migraciones.
6. Corre `python manage.py test --verbosity=2`.

### Resultado visible en GitHub

- **Pestaña Actions:** historial de todas las ejecuciones.
- **Junto a cada commit:** ✅ o ❌.
- **En el PR:** bloque de checks antes del botón de merge.

### Protección de ramas (recomendado)

En Settings → Branches → Branch protection rules, configurar para `develop`
y `main`:

```
☑ Require status checks to pass before merging
  → Django Tests
```

Con esto ningún PR puede mergearse si los tests están fallando.

### Agregar tests de una nueva feature

Solo hay que crear `backend/<app>/tests.py` en la rama de la feature. El
workflow los descubre y los corre automáticamente junto con los existentes.
**El archivo `tests.yml` no necesita modificarse nunca.**

---

## 8. Archivos de la feature

### Backend

```
backend/
├── config/
│   ├── settings.py              AUTH_USER_MODEL, JWT, CORS, app "usuarios"
│   └── urls.py                  incluye las rutas de usuarios
├── usuarios/
│   ├── models.py                Usuario y UsuarioManager
│   ├── serializers.py           validación de entrada y salida
│   ├── views.py                 login, me, logout y UsuarioViewSet
│   ├── permissions.py           EsAdministrador y LecturaAutenticados_EscrituraAdministrador
│   ├── urls.py                  rutas de autenticación y del ViewSet
│   ├── admin.py                 configuración del panel de administración
│   ├── tests.py                 34 tests automatizados
│   └── migrations/0001_initial.py
└── galpones/
    └── views.py                 se le aplica LecturaAutenticados_EscrituraAdministrador
```

### Frontend

```
frontend/
├── index.html                   título y favicon propios
├── public/favicon.svg           ícono del sistema (huevo dorado)
└── src/
    ├── api/
    │   ├── client.js            envío del token y traducción de errores DRF
    │   ├── auth.js              login, me, logout
    │   └── usuarios.js          una función por caso de uso
    ├── config/menu.js           matriz rol × sección — fuente única de verdad
    ├── context/AuthContext.jsx  estado de la sesión
    ├── components/
    │   ├── RequireAuth.jsx      rutas que exigen sesión
    │   ├── RequireRol.jsx       rutas restringidas por rol
    │   ├── CampoPassword.jsx    campo de contraseña con mostrar/ocultar
    │   └── UsuarioFormModal.jsx alta y edición de usuarios
    ├── pages/
    │   ├── LoginPage.jsx        CU01, con autenticación real
    │   ├── AppLayout.jsx        menú filtrado por rol y datos reales del usuario
    │   └── UsuariosPage.jsx     CU03 a CU08
    └── index.css                estilos agregados
```

### CI

```
.github/
└── workflows/
    └── tests.yml                workflow de GitHub Actions
```

---

## 9. Decisiones de diseño

### 9.1 Modelo de usuario propio en lugar del de Django

Django incluye un modelo `User` que no tiene `dni`, `rol` ni `estado`, que
son campos del modelo relacional del proyecto. Se extendió `AbstractBaseUser`
para definir los campos propios manteniendo el manejo seguro de contraseñas
y la integración con el panel de administración.

**Consecuencia:** `AUTH_USER_MODEL` debe declararse antes de la primera
migración. Cambiarlo después obliga a recrear la base de datos.

### 9.2 Roles como campo `rol`, no como Grupos de Django

Se midió el costo en consultas SQL: verificar `u.es_administrador` (campo
`rol`) genera **0 consultas**; `has_perm()` genera **2 consultas** la primera
vez por petición. Además, los roles son fijos según el análisis de requisitos,
y las reglas de negocio no son expresables con permisos de modelo de Django
("un administrador no puede darse de baja a sí mismo").

### 9.3 Autenticación con JWT en lugar de sesiones

La API es consumida por una SPA independiente. JWT no requiere estado en el
servidor, funciona igual desde una eventual app móvil, y no es vulnerable
a CSRF. El panel `/admin/` sigue usando cookies de sesión, que es el
mecanismo apropiado para una interfaz server-side.

### 9.4 `is_active` derivado de `estado`

Django consulta `is_active` para permitir o bloquear el inicio de sesión.
Se implementó como propiedad calculada a partir de `estado` para evitar dos
atributos que signifiquen lo mismo. Dar de baja a un usuario bloquea el
login automáticamente.

### 9.5 El control de acceso se implementa en el backend

Los permisos se validan en el backend (`permissions.py`) antes de ejecutar
cualquier vista. El frontend replica esa lógica solo para ocultar acciones
no disponibles: se verificó que la API responde 403 ante cualquier operación
no autorizada aunque se la invoque sin pasar por la interfaz.

### 9.6 Matriz de permisos centralizada en `config/menu.js`

La visibilidad de cada sección por rol se define en un único archivo,
consumido tanto por el sidebar como por `RequireRol` en `App.jsx`. Si
estuviera en dos lugares distintos, podrían quedar desincronizados. Cuando
un módulo obtenga backend real, el `permission_classes` de su ViewSet debe
replicar la misma lógica.

### 9.7 CI en todas las ramas, no solo en `develop` y `main`

Detectar un test roto en la rama `feature/*` mientras se trabaja es mucho
más barato que detectarlo al abrir el PR. Por eso el workflow corre en
cualquier push. Los pushes de documentación pura se excluyen con
`paths-ignore` para no consumir minutos de CI innecesariamente.

### 9.8 Recupero de contraseña manual

El sistema no envía correos. El enlace "¿Olvidaste tu contraseña?" muestra
un cartel con instrucciones para pedirle ayuda al administrador. Esto hace
necesario el caso de uso adicional de restablecimiento.

### 9.9 Validación centralizada en el backend

Los formularios usan validación HTML básica (`required`, `minLength`,
`type="email"`) para respuesta inmediata, pero la validación efectiva es la
del backend. Los mensajes de error se muestran tal como llegan de la API,
para evitar dos conjuntos de reglas que puedan divergir.

---

## 10. Verificación realizada

**Autenticación**

- Inicio de sesión con nombre de usuario y con email.
- Credenciales incorrectas y usuario inexistente devuelven el mismo mensaje.
- Un usuario dado de baja no puede iniciar sesión; al darlo de alta, sí.
- Sin token o con token inválido, la API responde 401.
- La sesión se conserva al recargar la página (token en `localStorage`).

**Permisos**

- Galpones: consulta permitida a los tres roles; escritura solo al
  Administrador (403 en los demás).
- Usuarios: Operario y Consulta reciben 403 en todas las operaciones.
- Al escribir la URL `/app/usuarios` con un rol no autorizado, la interfaz
  redirige al panel principal.
- Compras, Proveedores e Informes no aparecen en el menú del Operario.

**Gestión de usuarios**

- Alta, búsqueda por texto, filtros por rol y estado, modificación parcial.
- Rechazo de nombre de usuario, email y DNI duplicados.
- Rechazo de contraseñas menores a 8 caracteres.
- Alta y baja lógica, incluyendo el rechazo de operaciones repetidas (409).
- Un Administrador no puede eliminarse ni darse de baja a sí mismo.
- Un usuario con registros asociados no se elimina: responde 409 con el detalle.
- El restablecimiento invalida la contraseña anterior y habilita la nueva.
- El hash de la contraseña nunca se incluye en las respuestas de la API.

**Tests y CI**

- 35 tests corren en pocos segundos: `Ran 35 tests — OK`.
- El workflow de GitHub Actions se ejecutó correctamente en la rama
  `feature/gestion-usuarios` tras el push.
- Los pushes con solo cambios en `docs/` no disparan el CI.

---

## 11. Pendientes

- **Renovación automática del token.** La sesión expira a las 8 horas.
- **Revocación de tokens al cerrar sesión.** El token se descarta en el
  cliente pero sigue siendo técnicamente válido hasta su expiración.
- **Asignación de operarios a galpones** (`UsuariosDelGalpon`), que
  permitirá restringir la carga a los galpones asignados a cada operario.
- **Protección de ramas en GitHub:** el workflow ya corre los tests y reporta
  el resultado, pero el bloqueo efectivo del merge requiere una configuración
  adicional en GitHub: Settings → Branches → Branch protection rules →
  "Require status checks to pass before merging" → seleccionar `Django Tests`.
  Sin esa configuración, el PR se puede mergear aunque el CI haya fallado.
- **Tests de `config/menu.js`:** la matriz de permisos del frontend es
  JavaScript puro, testeable sin Jest + React. Conveniente cuando la
  matriz crezca con más módulos.
