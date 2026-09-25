# Convención de mensajes de commit

Usamos **Conventional Commits** para que el historial sea parejo entre
todos los integrantes y quede fácil de leer para el jurado/profesor.

## Formato

```
tipo(alcance): descripción corta en minúscula, sin punto final

Cuerpo opcional: explica el POR QUÉ del cambio, no el qué (el diff ya
muestra el qué). Útil sobre todo en fixes no obvios.
```

- **tipo**: qué clase de cambio es (ver tabla abajo).
- **alcance**: el módulo/app afectado — `galpones`, `usuarios`, `auth`,
  `frontend`, `docs`, `ci`, etc. Si el cambio toca varios módulos por
  igual, se puede omitir.
- **descripción**: en español, modo imperativo ("agregar", "corregir",
  "quitar"), no "agregado" ni "agrega".

## Tipos

| Tipo       | Cuándo usarlo                                                        |
|------------|-----------------------------------------------------------------------|
| `feat`     | Una funcionalidad nueva o un cambio de comportamiento visible         |
| `fix`      | Corrección de un bug                                                  |
| `test`     | Se agregan o modifican tests, sin cambiar código de producción        |
| `docs`     | Cambios solo en documentación (README, docs/, comentarios sueltos)    |
| `refactor` | Reordenar o limpiar código sin cambiar comportamiento                 |
| `style`    | Formato, espacios, nombres — sin efecto funcional                     |
| `chore`    | Tareas de mantenimiento (dependencias, configuración, CI)             |

## Ejemplos (reales, de este proyecto)

```
fix(galpones): cambiar el texto del botón "Dar de alta" a "Activar galpón"

feat(galpones): mostrar por defecto solo galpones activos para el rol Operario

feat(galpones): no listar operarios inactivos en el detalle del galpón

fix(galpones): no borrar la asignación de un operario inactivo al editar el galpón

El reemplazo de operarios en _sincronizar_operarios borraba TODAS las
asignaciones del galpón, incluida la de operarios dados de baja, porque
el formulario del frontend solo pre-carga operarios activos. Esto
rompía la regla de conservar el vínculo para cuando el operario se
reactive. Ahora el reemplazo solo toca asignaciones de operarios activos.

feat(galpones): agregar buscador y chips seleccionables para asignar operarios

test(galpones): cobertura de operarios inactivos y permisos de alta/baja
```

## Qué NO hacer

- No mezclar varios tipos de cambio no relacionados en un mismo commit
  (ej: un `fix` de backend junto con un `feat` de frontend sin relación).
- No usar mensajes genéricos ("cambios", "arreglos varios", "wip").
- No dejar commits sin mensaje de cuerpo cuando el fix no es obvio con
  solo leer el título (como en el ejemplo de arriba).
