# Unidad III · Actividad 3 (Actividad #14) — Matriz de roles y permisos

Guía corta de entrega del equipo. El enunciado oficial es
`unidad3_actividad_3.pdf` ("Matriz de roles y permisos del sistema", semana
del 23 al 26 de noviembre de 2026).

> **Base de datos.** El enunciado dice MySQL; el proyecto usa PostgreSQL 16
> desde el Parcial I. Las tablas son las mismas (`roles`, `permissions`,
> `role_permissions`, `company_user_roles`).

## 1. Qué se agregó

Hay dos formas de guardar el acceso, y no existe una tercera:

| Pregunta | Pantalla | Operación | Tabla |
|---|---|---|---|
| ¿Qué puede hacer este puesto? | **Roles y permisos** (nueva) | `setRolePermissions` | `role_permissions` |
| ¿Qué puesto tiene esta persona? | **Usuarios**, columna Rol | `assignRole` | `company_user_roles` |

**Cliente (`dashboard/`, el mismo de las actividades 1 y 2):**

- `src/features/admin/RolesPermissionsPage.tsx` muestra la matriz. Las
  columnas van en este orden: Administrador, Contador, Capturista y
  Consulta. Cada encabezado muestra el nombre y, abajo, el código. Las filas
  están en cinco grupos (Usuarios, Cuentas, Conceptos, Movimientos y Roles),
  y en cada grupo la lectura va antes que la escritura.
- La matriz se arma con `roles`, `permissions` y `rolePermissions`, esta
  última consultada una vez por columna.
- Una celda dice «sí» solo si la relación está activa y el permiso sigue
  activo. «No» es que no hay fila o que la fila está inactiva.
- **Revisar y guardar** pide `previewRolePermissions` con la lista completa
  de la columna. Al confirmar se llama `setRolePermissions` y luego la
  columna se vuelve a leer. Si se guarda la misma lista otra vez, la
  pantalla avisa que llegó `changed: false`.
- La columna **Administrador** aparece como *Solo lectura* y nunca se envía.
- `src/features/admin/components/RoleAssignControl.tsx` agrega el selector de
  la columna Rol en Usuarios. Lista los cuatro roles activos, llama a
  `assignRole` y muestra el rol que devolvió la mutación. Si el API rechaza
  el cambio, el error se lee debajo y se queda el puesto anterior.
- El selector no aparece para el administrador principal, para no tocar
  `isAdmin`.
- Menú: el ítem **Roles y permisos** solo aparece con `roles.read`. Además,
  cada ítem del dashboard administrativo ahora sale solo si el rol tiene el
  permiso de lectura de esa pantalla. Así el menú coincide con la columna del
  puesto (sección 4.1 del enunciado).
- Sin `roles.write`, las casillas aparecen deshabilitadas, no hay botón de
  guardar y la columna Rol de Usuarios es solo texto.
- El token viaja en `Authorization: Bearer …`. Ninguna operación envía
  `actorCompanyUserId`.

**Backend:** solo se hicieron cambios que agregan cosas. Ninguna regla
cambió y todas las operaciones siguen exigiendo `roles.read` o
`roles.write` con el token.

- `roles(activeOnly: Boolean = true)` y `permissions(activeOnly: Boolean = true)`.
  Con el valor por defecto se comportan igual que antes.
- `RolePermission.permission { id code … }`: el permiso anidado de cada
  relación, para leer el código de la celda.
- `CompanyUserRole.role { code name }`: el rol que devuelve `assignRole`.

**Nombres en pantalla.** En el catálogo del Parcial II, el `name` de cada rol
y de cada permiso es igual a su código (`accounts.write`). Por eso la pantalla
muestra la etiqueta del enunciado ("Crear cuentas") y deja el código en texto
secundario. Si el equipo le pone un nombre propio en la base, se muestra ese.

Operaciones para GraphiQL: `operaciones_actividad14.graphql` y
`variables_actividad14/`. Los id de los ejemplos suponen la base creada con
el seed (roles 1–4, permisos 1–10 en el orden del enunciado). Hay que
confirmarlos antes con la query `Matriz`.

## 2. Puesta en marcha

Hay que reconstruir la API para que tome los cambios del esquema:

    docker compose up -d --build

Para el entorno de pruebas (puerto 8001), usar el mismo prefijo
`-p fintrack5_test …` de la Actividad 13. No hay migración nueva.

    cd dashboard
    npm install
    npm run dev                                      (abrir http://localhost:5173)

## 3. Cómo se abre Roles y permisos

1. Iniciar sesión con el login de la actividad 1.
2. En el menú, ir a **Dashboard administrativo → Roles y permisos**. También
   se puede entrar directo con `#/admin/roles`.

**Quién edita la matriz:** `ADMINISTRADOR`, con
`david.morales@tecdesoftware.edu.mx`.

**Quiénes comprueban el efecto:**

- `CAPTURISTA`, con `alexander.rodriguez@tecdesoftware.edu.mx`. Ve aparecer
  y desaparecer **Nueva cuenta** en Cuentas.
- Un segundo capturista. Se crea en Usuarios con **Nuevo usuario** y se le
  asigna Capturista con el selector de Rol.
- `CONSULTA`, con `luis.chay@tecdesoftware.edu.mx`. Es la persona que pasa
  a Capturista en la sección 4.3.
- `CONTADOR`, con `david.demo@fintrack.local`. Ve la matriz sin poder
  guardarla.

Así queda el menú con la matriz inicial:

| Rol | Usuarios | Cuentas | Conceptos | Roles y permisos |
|---|---|---|---|---|
| ADMINISTRADOR | sí | sí | sí | sí (edita) |
| CONTADOR | sí | sí | sí | sí (solo lectura) |
| CAPTURISTA | no | sí | sí | no |
| CONSULTA | sí | sí | sí | no |

## 4. Recorrido para las evidencias

Las capturas se guardan en `evidencias/unidad3_actividad14/` y se describen
en `evidencias/unidad3_actividad14/evidencias.md`.

1. **Matriz inicial.** Como administrador, abrir Roles y permisos y comparar
   con la sección 2.2 del enunciado: 10, 8, 4 y 4 permisos.
2. **GraphiQL.** Ejecutar `ListaDelRol` con `columna_capturista.json`.
   Salen cuatro relaciones activas.
3. **Vista previa.** En Capturista, marcar *Crear cuentas* y pulsar
   **Revisar y guardar**. Debe decir: se activa `accounts.write`, no se
   desactiva nada, 4 sin cambio y total final 5.
4. **Cuentas del capturista.** Tomar una captura antes de guardar, sin
   Nueva cuenta. Guardar y entrar como capturista: ya aparece Nueva cuenta.
   El segundo capturista también la ve, aunque su fila de Usuarios no se
   editó.
5. **Cambio de puesto.** En Usuarios, pasar a luis.chay de Consulta a
   Capturista. `isAdmin` sigue en No, y la columna Consulta de la matriz no
   cambia.
6. **Segundo guardado.** Volver a pulsar **Revisar y guardar** en
   Capturista, sin cambios, y guardar. La pantalla avisa `changed: false`.
7. **Sin permiso.** El contador ve la matriz deshabilitada, o el capturista
   no tiene el ítem en el menú.

Al terminar, para regresar a la matriz inicial: desmarcar *Crear cuentas* en
Capturista y guardar, y devolver a luis.chay a Consulta.

## 5. Pruebas

Frontend: `npm run lint`, `npm run typecheck`, `npm test` y
`npm run build` (163/163 pruebas). `tests/rolesPermissions.test.tsx` cubre:

- la matriz inicial, el orden y la columna Administrador en solo lectura;
- una fila inactiva que se lee como «no»;
- la vista previa y el guardado, con la columna vuelta a leer y
  `changed: false` al repetir;
- un error del API al guardar;
- el contador en solo lectura;
- el capturista sin el ítem de menú;
- el catálogo vacío;
- `assignRole` (con éxito, con rechazo y sin `roles.write`).

## 6. ZIP de entrega

El archivo `unidad3_actividad3_equipo.zip` debe llevar el `dashboard/`,
`graphql_api/schema.py` (se ajustó), esta guía, `evidencias.md` con sus
capturas, `operaciones_actividad14.graphql` y `variables_actividad14/`.

No debe llevar `node_modules`, `dist`, ambientes virtuales, `.env` ni tokens.
Desde la raíz, con los cambios ya confirmados en git:

    git archive --format=zip -o unidad3_actividad3_equipo.zip HEAD dashboard graphql_api docs/unidad3_actividad14 evidencias/unidad3_actividad14 operaciones_actividad14.graphql variables_actividad14 README.md

`git archive` solo incluye archivos versionados, así que deja fuera
`node_modules` y `.env`.
