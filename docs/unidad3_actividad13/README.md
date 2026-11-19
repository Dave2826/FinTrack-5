# Unidad III · Actividad 2 (Actividad #13) — Dashboard administrativo

Guía de entrega del equipo. El enunciado oficial es
`unidad3_actividad_2.pdf` ("Dashboard administrativo", semana del 16 al 20 de
noviembre de 2026).

> **Base de datos.** El enunciado habla de MySQL; este proyecto usa
> PostgreSQL 16 desde el Parcial I. Las reglas del enunciado se cumplen igual:
> la llave y el movimiento se confirman en el mismo `COMMIT` de PostgreSQL.

## 1. Qué se entregó

| Entregable del enunciado | Dónde está |
|---|---|
| `createTransaction` idempotente con la tabla de llaves | `models/idempotency_key.py`, `services/transaction_service.py`, migración `alembic/versions/4d2a7c9e1b30_idempotencia_transacciones.py` |
| Captura de GraphiQL: dos envíos con la misma llave y el mismo id | Pendiente de tomar (sección 5); operación en `operaciones_actividad13.graphql` |
| Cliente con las tres secciones en el mismo dashboard de la actividad 1 | `dashboard/src/app/` (menú) y `dashboard/src/features/admin/` (Usuarios, Cuentas, Conceptos) |
| README corto: cómo se entra y qué rol se usó | Sección 3 de esta guía |
| Capturas de las tres pantallas con datos reales y un error | Pendientes de tomar (sección 5) en `evidencias/unidad3_actividad13/` |
| Boceto, si cambió | No cambió: se sigue el wireframe de la figura 9 (menú a la izquierda, título, búsqueda, acción principal y tabla) |

Cambios del backend que necesitaba el dashboard. El enunciado pide
completarlos en el backend antes de pintar la pantalla:

- `me`: empresa, persona, rol y permisos efectivos de la sesión. El dashboard
  decide con estos datos qué botones de alta dibuja; el backend sigue autorizando
  cada operación.
- `companyUsers` ahora trae `user { name email }` y `role { code name }`
  (solo lectura). No existe ningún campo de contraseña en el esquema.
- `createCompanyUser` acepta `name`, `email` y `password` para dar de alta a
  una persona nueva en una sola transacción. Sigue aceptando `userId` como en
  el Parcial I. La respuesta nunca devuelve la contraseña.
- `accountConcepts` trae el `concept { id name conceptType }` anidado.

## 2. Puesta en marcha (Windows CMD, desde la raíz del repo)

La imagen de la API copia el código al construirse y no monta la carpeta. Por
eso el contenedor seguía mostrando el esquema GraphQL anterior: después de
actualizar el código **hay que reconstruir la imagen**.

Entorno de desarrollo (base `actividad5`, API en `http://localhost:8002/graphql`):

    docker compose up -d --build
    docker compose exec api alembic upgrade head
    docker compose exec api alembic current          (debe decir 4d2a7c9e1b30 (head))

Entorno de pruebas (base `fintrack5_test`, que es la que usa el dashboard por
el puerto 8001):

    docker compose -p fintrack5_test --env-file .env.test -f compose.yaml -f compose.test.yaml up -d --build api
    docker compose -p fintrack5_test --env-file .env.test -f compose.yaml -f compose.test.yaml exec api alembic upgrade head

La migración solo **agrega** la tabla `idempotency_keys`. No modifica ni borra
movimientos, cuentas, conceptos ni membresías.

Dashboard (con el acceso temporal a la API de pruebas en el puerto 8001, ver
`docs/acceso-temporal-api-pruebas.md`):

    cd dashboard
    npm install
    npm run dev                                      (abrir http://localhost:5173)

## 3. Cómo se entra a la administración

1. Iniciar sesión con el mismo login de la actividad 1.
2. En el menú de la izquierda, **Dashboard administrativo → Usuarios, Cuentas
   o Conceptos**. **Dashboard financiero** regresa a la vista de la
   actividad 1. El encabezado conserva el nombre de la empresa y **Cerrar
   sesión**.
3. También se puede entrar directo con `#/admin/usuarios`, `#/admin/cuentas`
   o `#/admin/conceptos` en la URL.

**Rol usado para probar la escritura:** `ADMINISTRADOR`, con la cuenta
`david.morales@tecdesoftware.edu.mx` (administrador principal de FinTrack
Demo). **Rol de solo lectura:** `CONSULTA`, con
`luis.chay@tecdesoftware.edu.mx`. Ve las tablas, pero no los botones de alta,
Desactivar, Asignar ni Quitar.

Qué botón ve cada rol (matriz vigente del Parcial II, que esta semana no se
edita):

| Rol | Usuarios | Cuentas | Conceptos |
|---|---|---|---|
| ADMINISTRADOR | ver, alta, desactivar | ver, alta | ver, alta, asignar, quitar |
| CONTADOR | ver | ver, alta | ver, alta, asignar, quitar |
| CAPTURISTA | sin permiso de lectura (aviso) | ver | ver |
| CONSULTA | ver | ver | ver |

## 4. Las cuatro cuentas de FinTrack Demo (bootstrap)

Script: `scripts/bootstrap_fintrack_demo.py`. Deja esta distribución:

| Usuario | Correo | Rol | Administrador |
|---|---|---|---|
| Edwuard Chay | luis.chay@tecdesoftware.edu.mx | CONSULTA | No |
| Alexander Fabrizio Rodriguez | alexander.rodriguez@tecdesoftware.edu.mx | CAPTURISTA | No |
| David Morales (nueva) | david.morales@tecdesoftware.edu.mx | ADMINISTRADOR | Sí |
| David Morales (histórica) | david.demo@fintrack.local | CONTADOR | No |

Garantías (se verifican **antes** del `COMMIT`; si alguna falla hay `ROLLBACK`):

- La empresa, los movimientos, las cuentas, los conceptos y las relaciones
  cuenta-concepto no cambian. Se compara una huella antes y después.
- La membresía histórica de David conserva su ID y su contraseña.
- La nueva cuenta de David es el único administrador principal.
- Cada membresía queda con exactamente un rol activo.
- Las demás membresías de la empresa no se tocan.

Orden seguro. Usar el mismo prefijo de `docker compose` del entorno donde vive
FinTrack Demo; los ejemplos son del entorno de desarrollo:

    REM 1) Plan en solo lectura (transacción READ ONLY; no escribe nada)
    docker compose exec api python -m scripts.bootstrap_fintrack_demo

    REM 2) Aplicar. Las contraseñas de las cuentas que se crean se piden en pantalla
    REM    (no se imprimen ni se guardan en archivos). -it es necesario para el prompt.
    docker compose exec -it api python -m scripts.bootstrap_fintrack_demo --aplicar

    REM 3) Verificación final de solo lectura (código 0 si todo coincide)
    docker compose exec api python -m scripts.bootstrap_fintrack_demo --verificar

Alternativa sin prompt: pasar `-e BOOTSTRAP_PASSWORD_LUIS=...`,
`-e BOOTSTRAP_PASSWORD_ALEXANDER=...` y `-e BOOTSTRAP_PASSWORD_DAVID=...` a
`docker compose exec`. Conviene no dejarlas en el historial de la terminal.
Cada contraseña se entrega en persona a su dueño.

Si el plan aborta, no cambió nada. Mensajes posibles:

- `no existe la empresa "FinTrack Demo"`: revisar el nombre exacto o pasar
  `--empresa "Nombre exacto"`.
- `hay administradores principales activos fuera de la distribución`: hay
  que decidir en equipo qué hacer con esa membresía antes de aplicar.
- `no existe el usuario histórico`: el script no lo crea de nuevo para no
  perder el historial.

El error de importación de los intentos anteriores (`No module named
'database'`) venía de ejecutar el archivo como `python scripts/...` fuera de
la raíz. El script ahora funciona de las dos formas, pero conviene usar
`python -m scripts.bootstrap_fintrack_demo`.

## 5. Comprobación y evidencias (orden del enunciado)

Guardar las capturas en `evidencias/unidad3_actividad13/`.

**Idempotencia (antes de las pantallas), en GraphiQL** (`/graphql`, con el
encabezado `Authorization: Bearer <token>` de una cuenta con
`transactions.write`):

1. `MovimientoIdempotente` con `variables_actividad13/movimiento_llave_1.json`
   (ajustar `accountId` y `conceptId` a una pareja asignada). Enviar dos
   veces: **el mismo `id`**. → captura `01_graphiql_misma_llave.png`.
2. La misma mutación con `movimiento_llave_2.json` (otra llave, mismo monto):
   **otro `id`**. → `02_graphiql_otra_llave.png`.
3. En pgAdmin: `SELECT * FROM idempotency_keys;` y
   `SELECT count(*) FROM transactions WHERE id = <id del paso 1>;` → una
   sola fila. → `03_pgadmin_llaves.png`.

**Dashboard, con ADMINISTRADOR (david.morales):**

1. Login y abrir Dashboard administrativo. → `04_usuarios.png`.
2. La tabla de usuarios coincide con `companyUsers` en GraphiQL
   (`Administracion` con `administracion.json`).
3. Crear un usuario nuevo. Aparece en la tabla. Repetir con el mismo correo:
   "Ya existe un usuario con ese correo". → `05_error_correo_duplicado.png`.
4. Desactivarlo: la fila sigue con estado Inactivo; `companyUsers(activeOnly:
   false)` muestra `isActive: false`.
5. Crear una cuenta. → `06_cuentas.png`.
6. Crear un concepto de egreso, asignarlo a esa cuenta y volver a asignarlo:
   "El concepto ya está asignado a esta cuenta". → `07_conceptos_duplicado.png`.
7. Quitarlo: sigue en el catálogo y ya no aparece en la cuenta.
8. Cerrar sesión y entrar con CONSULTA (luis.chay): ve las tablas y no ve los
   botones de alta. → `08_consulta_sin_botones.png`.

## 6. Pruebas automatizadas

Backend (solo contra `fintrack5_test`, con las mismas guardas de siempre;
revisión de Alembic esperada `4d2a7c9e1b30`):

    docker exec -e PYTHONPATH=/app fintrack5-test-api python -m unittest tests.test_actividad13 -v
    docker exec -e PYTHONPATH=/app fintrack5-test-api python -m unittest tests.test_bootstrap_fintrack_demo -v

- `tests/test_actividad13.py` (14 casos): misma llave → mismo id y una sola
  fila; otra llave → otro movimiento; misma llave con otros datos → rechazo;
  seis envíos concurrentes con la misma llave → una fila; un rechazo no deja
  llave huérfana; `me`; el esquema no expone contraseñas; alta, correo
  duplicado, segundo administrador, baja lógica, permisos de escritura y
  conceptos por cuenta.
- `tests/test_bootstrap_fintrack_demo.py` (4 casos): plan de solo lectura,
  aborto sin contraseñas, rollback completo si algo falla a la mitad, y
  aplicación + verificación + repetición sin cambios.

Ambas crean su propia empresa ficticia y la borran al terminar. Si las cuatro
cuentas reales ya existen en `fintrack5_test`, la suite del bootstrap **se
omite** (`skipped`) para no tocarlas. En ese caso, la comprobación es
`--verificar`.

Frontend (`dashboard/`): `npm run lint`, `npm run typecheck`, `npm test`
(incluye `tests/adminDashboard.test.tsx`) y `npm run build`.

## 7. Fuera de alcance (según el enunciado)

- No se editan permisos ni se asignan roles: es la Actividad #14. La columna
  Rol solo se muestra; una persona dada de alta desde la pantalla nace "Sin rol".
- No se capturan movimientos desde el dashboard administrativo.
- No se borran filas: desactivar pone `isActive` en `false`.
- La contraseña solo existe en el formulario de alta y en la mutación.
