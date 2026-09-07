# Gestión de Usuarios y Autenticación

**Rama:** `feature/gestion-usuarios`
**Casos de uso:** CU01, CU02, CU03, CU04, CU05, CU06, CU07, CU08

Primera feature con autenticación real del sistema. Incorpora el modelo de
usuario propio, el inicio de sesión con JWT, el control de acceso por rol y la
gestión completa de usuarios, tanto en el backend como en la interfaz.

---

## 1. Alcance

### Qué incluye

- Modelo `Usuario` propio, que reemplaza al usuario por defecto de Django.
- Inicio y cierre de sesión con tokens JWT.
- Control de acceso por rol (Administrador, Operario, Consulta) aplicado a
  **todos** los endpoints, incluidos los de Galpones.
- ABM completo de usuarios con búsqueda, filtros, alta y baja lógica.
- Restablecimiento de contraseña por parte del Administrador.
- Interfaz React conectada a la API, con menú y rutas filtradas por rol.

### Qué no incluye

- Recupero automático de contraseña por email. El sistema muestra un cartel
  indicando que hay que pedirle ayuda a un administrador.
- Cambio de contraseña por parte del propio usuario (queda pendiente).
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
4. El sistema genera un token de sesión y lo devuelve junto con los datos del
   usuario.
5. El sistema redirige al panel principal, mostrando únicamente las secciones
   habilitadas para su rol.

**Flujos alternativos**

- **3a. Credenciales incorrectas:** el sistema muestra "Usuario o contraseña
  incorrectos" y permanece en la pantalla de inicio de sesión.
- **3b. Usuario dado de baja:** el sistema rechaza el acceso con el mismo
  mensaje genérico.
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

**Postcondición:** las pantallas del sistema dejan de ser accesibles hasta un
nuevo inicio de sesión.

---

### CU03 – Buscar Usuario

**Actor:** Administrador.

**Flujo principal**

1. El Administrador accede a la sección Usuarios.
2. El sistema muestra el listado de usuarios registrados.
3. El Administrador ingresa un texto de búsqueda o aplica filtros por rol y
   por estado.
4. El sistema muestra los usuarios que cumplen los criterios.
5. El Administrador selecciona un usuario y el sistema muestra su detalle.

**Flujos alternativos**

- **4a. Sin resultados:** el sistema informa que no hay usuarios que coincidan
  con la búsqueda.

**Notas:** la búsqueda se realiza sobre nombre, apellido, nombre de usuario,
email y DNI.

---

### CU04 – Nuevo Usuario

**Actor:** Administrador.

**Flujo principal**

1. El Administrador selecciona "Nuevo usuario".
2. El sistema muestra el formulario de alta.
3. El Administrador completa nombre, apellido, nombre de usuario, email, DNI,
   rol y una contraseña inicial.
4. El sistema valida los datos.
5. El sistema registra el usuario con estado Activo.
6. El sistema muestra el usuario creado en el listado.

**Flujos alternativos**

- **4a. Nombre de usuario, email o DNI ya registrados:** el sistema indica cuál
  es el dato duplicado y no crea el usuario.
- **4b. Contraseña menor a 8 caracteres:** el sistema lo informa y no crea el
  usuario.

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

- **4a. Datos duplicados con otro usuario:** el sistema lo informa y no guarda.

**Notas:** la contraseña no se modifica desde este caso de uso.

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

**Notas:** el borrado es físico. Para conservar el historial de lo que un
usuario registró conviene darlo de baja (CU08) en lugar de eliminarlo.

---

### CU07 – Dar de Alta Usuario

**Actor:** Administrador.
**Precondición:** el usuario está en estado Inactivo.

**Flujo principal**

1. El Administrador selecciona un usuario dado de baja y elige "Dar de alta".
2. El sistema cambia su estado a Activo.

**Flujos alternativos**

- **1a. El usuario ya está activo:** el sistema lo informa y no realiza cambios.

**Postcondición:** el usuario vuelve a poder iniciar sesión.

---

### CU08 – Dar de Baja Usuario

**Actor:** Administrador.
**Precondición:** el usuario está en estado Activo.

**Flujo principal**

1. El Administrador selecciona un usuario y elige "Dar de baja".
2. El sistema cambia su estado a Inactivo.

**Flujos alternativos**

- **1a. El usuario seleccionado es el propio Administrador:** el sistema impide
  la operación, para evitar que quede sin acceso al sistema.
- **1b. El usuario ya está dado de baja:** el sistema lo informa.

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
2. Ingresa una contraseña provisoria de al menos 8 caracteres.
3. El sistema reemplaza la contraseña del usuario.
4. El Administrador comunica la contraseña provisoria al usuario.

**Notas:** no se solicita la contraseña anterior, porque el Administrador no la
conoce; ese es justamente el motivo del pedido.

**Se propone incorporarlo al listado de casos de uso del proyecto.**

---

## 3. Matriz rol × caso de uso

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
| CU09 Buscar Galpón | Sí | Sí | Sí |
| CU10 a CU14 (escritura sobre Galpones) | Sí | No | No |

### Secciones visibles en el menú

| Sección | Administrador | Operario | Consulta |
|---|:---:|:---:|:---:|
| Dashboard | Sí | Sí | Sí |
| Galpones, Lotes, Recolección, Descartes, Salidas | Sí | Sí | Sí |
| Entradas, Materias Primas | Sí | Sí | Sí |
| Compras, Proveedores | Sí | No | No |
| Informes | Sí | Sí | Sí |
| Usuarios | Sí | No | No |

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

**Campos heredados de Django:** `last_login`, `is_superuser` y las relaciones
de `PermissionsMixin`, que el panel de administración requiere para funcionar.

**Propiedades calculadas (no son columnas):**

- `nombre_completo` — concatena nombre y apellido.
- `es_administrador` — `rol == "A"`.
- `is_active` — se deriva de `estado`. Django consulta este atributo al
  autenticar, de modo que un usuario dado de baja no puede iniciar sesión.

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
  "usuario": { "id_usuario": 1, "usuario": "jperez", "rol": "A", "rol_display": "Administrador", ... }
}
```

Las peticiones posteriores envían el token en el encabezado:

```
Authorization: Bearer <access>
```

---

## 6. Decisiones de diseño

### 6.1 Modelo de usuario propio en lugar del de Django

Django incluye un modelo `User` con campos `username`, `first_name`,
`last_name` y `is_active`. No se utilizó porque el modelo relacional del
proyecto define `nombre`, `apellido`, `dni`, `rol` y `estado`, que no tienen
correspondencia directa.

Se extendió `AbstractBaseUser` para conservar el manejo seguro de contraseñas y
la integración con el panel de administración, definiendo los campos propios.

**Consecuencia:** `AUTH_USER_MODEL` debe declararse **antes de la primera
migración** del proyecto. Cambiarlo después obliga a recrear la base de datos.

### 6.2 Roles como campo `rol`, no como Grupos de Django

Django ofrece un sistema de grupos y permisos configurable desde el panel de
administración. Se optó por el campo `rol` por cuatro razones:

1. **Los roles son fijos.** El análisis de requisitos define exactamente tres,
   y no se prevé que el cliente cree otros.
2. **El modelo relacional ya define `rol`.** Usar además grupos implicaría
   mantener la misma información en dos lugares, con riesgo de desincronización.
3. **La granularidad no coincide.** Los permisos de Django son por modelo y
   operación (`add_galpon`, `change_galpon`). Las reglas del sistema son de otra
   naturaleza: "un administrador no puede darse de baja a sí mismo", "un
   operario solo carga en sus galpones asignados". Esas reglas se escriben en
   código de todos modos.
4. **Rendimiento.** Se midió: verificar el campo `rol` no genera consultas SQL,
   mientras que `has_perm()` genera dos consultas la primera vez por petición.

**Cuándo revisar esta decisión:** si el cliente solicitara definir roles nuevos
sin modificar el código.

### 6.3 Autenticación con JWT en lugar de sesiones

La API es consumida por una aplicación React independiente, no por páginas
renderizadas por el servidor. Los tokens JWT resultan más adecuados porque:

- No requieren estado en el servidor.
- Funcionan igual desde una eventual aplicación móvil.
- No son vulnerables a CSRF, ya que el token se envía explícitamente por
  código y no automáticamente por el navegador.

El panel `/admin/` de Django sigue utilizando cookies de sesión, que es el
mecanismo apropiado para una interfaz renderizada en el servidor. Ambos
mecanismos conviven sin interferir, ya que operan sobre rutas distintas.

### 6.4 `is_active` derivado de `estado`

Django consulta el atributo `is_active` para permitir o bloquear el inicio de
sesión. Se implementó como propiedad calculada a partir de `estado` en lugar de
como un campo independiente, para evitar dos atributos que signifiquen lo mismo
y puedan quedar desincronizados.

**Consecuencia:** dar de baja a un usuario (CU08) le impide iniciar sesión de
forma automática, sin lógica adicional.

### 6.5 El control de acceso se implementa en el backend

Los permisos se validan en el backend mediante dos clases:

- `EsAdministrador` — restringe la gestión de usuarios.
- `LecturaAutenticados_EscrituraAdministrador` — permite consultar a cualquier
  usuario autenticado y modificar solo al Administrador. Se aplica a Galpones y
  se reutilizará en los módulos productivos siguientes.

El frontend replica esa lógica únicamente para **ocultar acciones no
disponibles**, lo que mejora la experiencia de uso pero **no constituye un
mecanismo de seguridad**: se verificó que la API responde 403 ante cualquier
operación no autorizada, aun cuando se la invoque sin pasar por la interfaz.

### 6.6 Restricción de rutas además de ocultar enlaces en el menú

Ocultar un enlace del menú no impide acceder a la ruta escribiendo la URL, ni
evita que una pantalla ya abierta permanezca visible al cambiar de usuario. Por
eso las rutas restringidas se envuelven en el componente `RequireRol`.

La matriz rol × sección se define en un único archivo (`src/config/menu.js`),
consumido tanto por el menú lateral como por las rutas, para que ambos no
puedan quedar desincronizados.

### 6.7 Recupero de contraseña manual

El sistema no envía correos de recupero. El enlace "¿Olvidaste tu contraseña?"
muestra un cartel indicando que hay que solicitar ayuda a un administrador.

Esta decisión hace necesario el caso de uso adicional de restablecimiento de
contraseña, sin el cual el circuito quedaría incompleto.

### 6.8 Validación centralizada en el backend

Los formularios utilizan validación de HTML (`required`, `minLength`,
`type="email"`) para dar respuesta inmediata, pero la validación efectiva es la
del backend: cuando la API responde con un error, el mensaje se muestra tal
como llega.

El motivo es evitar dos conjuntos de reglas que puedan divergir con el tiempo.

---

## 7. Archivos de la feature

### Backend

```
backend/
├── config/
│   ├── settings.py            AUTH_USER_MODEL, JWT, app "usuarios"
│   └── urls.py                incorpora las rutas de usuarios
├── usuarios/                  app nueva
│   ├── models.py              Usuario y UsuarioManager
│   ├── serializers.py         validación de entrada y salida
│   ├── views.py               login, me, logout y UsuarioViewSet
│   ├── permissions.py         clases de permisos por rol
│   ├── urls.py                rutas de autenticación y del ViewSet
│   ├── admin.py               configuración del panel de administración
│   └── migrations/0001_initial.py
└── galpones/
    └── views.py               se le aplican los permisos por rol
```

### Frontend

```
frontend/
├── index.html                 título y favicon propios
├── public/favicon.svg         ícono del sistema
└── src/
    ├── api/
    │   ├── client.js          envío del token y traducción de errores
    │   ├── auth.js            login, me, logout
    │   └── usuarios.js        una función por caso de uso
    ├── config/menu.js         matriz rol × sección
    ├── context/AuthContext.jsx  estado de la sesión
    ├── components/
    │   ├── RequireAuth.jsx    rutas que exigen sesión
    │   ├── RequireRol.jsx     rutas restringidas por rol
    │   ├── CampoPassword.jsx  campo de contraseña con mostrar/ocultar
    │   └── UsuarioFormModal.jsx  alta y edición
    ├── pages/
    │   ├── LoginPage.jsx      CU01, con autenticación real
    │   ├── AppLayout.jsx      menú filtrado por rol
    │   └── UsuariosPage.jsx   CU03 a CU08
    └── index.css              estilos agregados
```

---

## 8. Verificación realizada

Se comprobó, con la base de datos PostgreSQL y ambos servidores en ejecución:

**Autenticación**

- Inicio de sesión con nombre de usuario y con email.
- Credenciales incorrectas y usuario inexistente devuelven el mismo mensaje.
- Un usuario dado de baja no puede iniciar sesión; al darlo de alta, sí.
- Sin token o con token inválido, la API responde 401.
- La sesión se conserva al recargar la página.

**Permisos**

- Galpones: consulta permitida a los tres roles; creación, modificación y
  eliminación solo al Administrador (403 en los demás casos).
- Usuarios: los roles Operario y Consulta reciben 403 en todas las operaciones.
- Al escribir la URL `/app/usuarios` con un rol no autorizado, la interfaz
  redirige al panel principal.

**Gestión de usuarios**

- Alta, búsqueda por texto, filtros por rol y estado, modificación parcial.
- Rechazo de nombre de usuario, email y DNI duplicados.
- Rechazo de contraseñas menores a 8 caracteres.
- Alta y baja lógica, incluyendo el rechazo de operaciones repetidas (409).
- Un Administrador no puede eliminarse ni darse de baja a sí mismo.
- El restablecimiento de contraseña invalida la anterior y habilita la nueva.
- El hash de la contraseña nunca se incluye en las respuestas de la API.

---

## 9. Pendientes

- **Cambio de contraseña por el propio usuario.** Hoy solo el Administrador
  puede restablecerla.
- **Campo `debe_cambiar_password`,** para obligar al usuario a definir una
  contraseña propia tras un restablecimiento.
- **Renovación automática del token.** La sesión expira a las 8 horas y obliga
  a iniciar sesión nuevamente.
- **Revocación de tokens.** Al cerrar sesión, el token se descarta en el
  cliente pero sigue siendo válido hasta su expiración.
- **Asignación de operarios a galpones** (`UsuariosDelGalpon`), que permitirá
  restringir la carga de datos a los galpones asignados a cada operario.
- **Registro de auditoría:** qué usuario creó o modificó cada registro.
- **Pruebas automatizadas** con el framework de pruebas de Django. La
  verificación descrita en la sección 8 se realizó de forma manual.
