# FinTrack-5

Backend de gestión financiera (empresas, usuarios, cuentas, conceptos y movimientos) expuesto mediante GraphQL, con autenticación JWT y autorización por roles y permisos.

## Descripción

FinTrack-5 separa la API GraphQL, la lógica de negocio, el acceso a datos y la persistencia en capas. Cada petición autentica al usuario con un token JWT y evalúa, contra la base de datos, si el rol activo de su membresía tiene el permiso que exige la operación.

## Integrantes

> **Dato pendiente:** el repositorio no contiene información verificable sobre los integrantes del equipo. No se inventaron nombres. Antes de la entrega, agregue aquí la lista real de integrantes proporcionada por el docente o el equipo.

## Arquitectura

    GraphQL -> Services -> Repositories -> SQLAlchemy -> PostgreSQL

- **GraphQL** (`graphql_api/`): recibe queries y mutations y obtiene la identidad desde el token.
- **Services** (`services/`): reglas de negocio, validaciones y autorización (`exigir_permiso`).
- **Repositories** (`repositories/`): operaciones de acceso a datos.
- **SQLAlchemy** (`models/`): mapeo entre objetos y tablas.
- **PostgreSQL**: almacenamiento persistente.

## Tecnologías

Python 3.11, FastAPI, Strawberry GraphQL, SQLAlchemy, PostgreSQL 16, Alembic, PyJWT, pwdlib/Argon2, Docker y Docker Compose. Las dependencias se declaran en `requirements.txt`.

## Estructura del proyecto

    FinTrack-5/
    ├── alembic/               migraciones y configuración de Alembic
    ├── database/              conexión a PostgreSQL
    ├── graphql_api/           esquema, resolvers y contexto (identidad por token)
    ├── models/                modelos SQLAlchemy
    ├── repositories/          acceso a datos
    ├── security/              JWT y hash de contraseñas
    ├── services/              lógica de negocio y autorización
    ├── scripts/               setup, limpieza y reproductores de evidencias
    ├── tests/                 suites de las Actividades 5, 6 y 7
    ├── variables/             variables de las operaciones de la Actividad 5
    ├── variables_actividad6/  variables de la Actividad 6
    ├── variables_actividad7/  variables de los balances de la Actividad 7
    ├── evidencias/            capturas y transcripciones por actividad
    ├── operaciones.graphql, operaciones_actividad6.graphql, operaciones_actividad7.graphql, comprobaciones.sql
    ├── evidencias.md, evidencias_actividad7.md, investigacion.md
    └── compose.yaml, compose.test.yaml, Dockerfile, requirements.txt, README.md

## Configuración del entorno

Desde Windows CMD, copia las plantillas y sustituye los marcadores `CAMBIAR-*` por valores ficticios propios:

    copy .env.example .env
    copy .env.test.example .env.test

- `.env`: entorno de desarrollo (contenedores `fastapi-api-actividad5`, `postgres-actividad5` y `pgadmin-actividad5`, base `actividad5`).
- `.env.test`: entorno de pruebas aislado (contenedores `fintrack5-test-*`, base `fintrack5_test`, sin puertos publicados).
- `JWT_SECRET` es obligatorio en ambos entornos; el algoritmo (HS256) y la vigencia (30 minutos) son fijos en `security/jwt.py`.
- Las plantillas solo contienen valores ficticios; no compartas ni versiones los archivos `.env` reales (`gitignore` ya los excluye).

## Ejecución con Docker

    docker compose up -d     # iniciar los servicios de desarrollo
    docker compose ps        # comprobar su estado

| Servicio | URL local |
|---|---|
| API | http://localhost:8002 |
| GraphQL | http://localhost:8002/graphql |
| PostgreSQL | localhost:5434 |
| pgAdmin | http://localhost:5052 |

## Migraciones

    docker compose exec api alembic upgrade head
    docker compose exec api alembic current

La revisión actual es `3b9f41c7d2ae (head)`.

## Autenticación y seguridad

- `login` es público y responde `AuthPayload { token, tokenType, user }`. El `user` mínimo (`id`, `name`, `email`) nunca expone el hash y un login rechazado no entrega token.
- El token es un JWT firmado con **HS256** y vigencia de **30 minutos**; su payload contiene únicamente `companyUserId`, `companyId` y `exp` (UTC).
- El secreto se lee exclusivamente de `JWT_SECRET` (sin valor por defecto) y nunca se registra.
- Las 30 operaciones protegidas (15 queries y 15 mutations) dejaron de recibir la identidad en el cuerpo; se envía el token en la cabecera:

      Authorization: Bearer <token>

  El contexto valida firma, expiración, membresía y usuario activos, y la correspondencia del `companyId` del token con la empresa de la membresía.
- La autorización no depende del token: cada operación exige un permiso del catálogo y el rol activo se consulta en la base de datos en cada petición, por lo que un token anterior refleja de inmediato un cambio de rol.
- Las contraseñas se almacenan con hash Argon2.

## Pruebas

Todas las suites se ejecutan **solo** contra el entorno de pruebas aislado `fintrack5_test` (guardas `DB_NAME=fintrack5_test`, `DB_HOST=postgres` y revisión de Alembic `3b9f41c7d2ae`). Nunca contra la base de desarrollo `actividad5`.

    docker exec -e PYTHONPATH=/app fintrack5-test-api python -m unittest tests.test_control_acceso_rol -v       # Actividad 6: 20/20 OK
    docker exec -e PYTHONPATH=/app fintrack5-test-api python -m unittest tests.test_configuracion_permisos -v   # Actividad 5: 18/18 OK
    docker exec -e PYTHONPATH=/app fintrack5-test-api python -m scripts.pruebas_actividad4                      # Actividad 4: 34/34 APROBADOS

Para preparar o limpiar los datos ficticios (mismas guardas; la limpieza simula primero y aplica solo con `--confirm`), la invocación sobre el overlay de pruebas es:

    docker compose -p fintrack5_test --env-file .env.test -f compose.yaml -f compose.test.yaml exec -T -e PYTHONPATH=/app api python /app/scripts/setup_pruebas.py

## Actividad 7: balances por cuenta y balance general

### Objetivo

Convertir los movimientos registrados (cuenta, concepto, tipo, importe, fecha de operación) en respuestas de balance calculadas en el servidor. El cliente no suma importes: recibe el saldo inicial, los ingresos y egresos del periodo, el profit, el saldo final y la marca de números rojos con la misma regla para cualquier pantalla.

### Consultas

Ambas son de solo lectura. Obtienen la empresa desde la membresía autenticada (nunca desde un argumento `companyId`) y exigen los permisos `accounts.read` y `transactions.read`.

#### `accountBalance(accountId: ID!, fromDate: Date!, toDate: Date!): AccountBalance!`

Devuelve el balance de una cuenta de la empresa autenticada. Incluye cuentas activas e inactivas, y cuentas sin movimientos (con importes en cero).

Campos: `accountId`, `accountName`, `isActive`, `openingBalance`, `totalIncome`, `totalExpense`, `profit`, `closingBalance`, `isInRed`, `currency`.

#### `generalBalance(fromDate: Date!, toDate: Date!): GeneralBalance!`

Devuelve el balance consolidado de todas las cuentas de la empresa autenticada. La colección `accounts` se ordena por `accountId` ascendente y los totales se derivan de esos mismos balances.

Campos: `companyId`, `fromDate`, `toDate`, `openingBalance`, `totalIncome`, `totalExpense`, `profit`, `closingBalance`, `accountsInRed`, `isInRed`, `currency`, `accounts`.

`companyId` es un campo de salida de tipo `ID!`. Su valor procede de la empresa de la identidad autenticada que ya usa el resolver para ejecutar la consulta; no es un argumento y el cliente no puede sustituirlo. La consulta solo acepta `fromDate` y `toDate`.

### Reglas de cálculo

- `openingBalance`: ingresos activos anteriores al inicio del periodo menos egresos activos anteriores al inicio.
- `totalIncome`: suma de ingresos activos dentro del periodo.
- `totalExpense`: suma de egresos activos dentro del periodo.
- `profit = totalIncome - totalExpense`.
- `closingBalance = openingBalance + profit`.
- `isInRed = closingBalance < 0` (cero no está en rojo).
- `accountsInRed`: número de cuentas con `closingBalance` estrictamente negativo.
- `currency`: `MXN`.

Los movimientos inactivos no participan. Las relaciones con conceptos no se unen a la agregación para evitar duplicar importes. Una empresa sin cuentas devuelve `accounts: []`, importes `0.00`, `accountsInRed: 0` e `isInRed: false`.

### Números rojos

Una cuenta está en números rojos cuando su saldo final es negativo (`closingBalance < 0`). El indicador general `isInRed` se calcula sobre el saldo final consolidado de la empresa, no sobre el número de cuentas negativas. Por eso una empresa puede tener `isInRed: false` y, a la vez, `accountsInRed: 1` si una cuenta individual cierra en negativo pero el consolidado es positivo.

### Ejemplo de referencia Banco/Caja

Datos del caso B01 (periodo 2026-10-26 a 2026-10-30):

| Cuenta | Saldo inicial | Ingresos | Gastos | Profit | Saldo final | En rojo |
|---|---:|---:|---:|---:|---:|---|
| Banco | 1,000.00 | 3,000.00 | 2,200.00 | 800.00 | 1,800.00 | No |
| Caja | 0.00 | 500.00 | 700.00 | -200.00 | -200.00 | Sí |
| Ahorro | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | No |
| **Balance general** | **1,000.00** | **3,500.00** | **2,900.00** | **600.00** | **1,600.00** | **No** |

Caja está en números rojos (`closingBalance = -200.00`) aunque el balance general sea positivo (`closingBalance = 1,600.00`, `accountsInRed = 1`, `isInRed = false`): el indicador general depende del saldo final consolidado, mientras que `accountsInRed` cuenta las cuentas individualmente negativas.

### Fechas y zona horaria

`fromDate` y `toDate` son obligatorios y se interpretan como días completos UTC. El intervalo es `transaction_date >= fromDate 00:00:00` y `transaction_date < (toDate + 1 día) 00:00:00`. Se usa siempre `transaction_date`, nunca `captured_at`. Si `fromDate` es posterior a `toDate`, la consulta devuelve un error controlado.

`transactionDate` (fecha de la operación, aportada al registrar el movimiento) y `capturedAt` (instante en que el servidor guardó el registro) se conservan como campos distintos. Los balances usan `transactionDate`; un movimiento capturado hoy pero con fecha de operación anterior se contabiliza en el periodo de su fecha de operación.

### Precisión decimal

Los importes se agregan y se calculan con `Decimal`; no se convierten a `float`. Cada valor se cuantiza a dos decimales con `ROUND_HALF_UP` antes de construir la respuesta, por lo que todos los importes monetarios se devuelven con formato de dos decimales (por ejemplo `1800.00`, `-200.00`, `0.00`).

### Autenticación y permisos

Ambas consultas requieren un JWT válido con membresía y usuario activos. La empresa se toma de la membresía autenticada. Un token ausente, alterado o vencido no permite consultar. Retirar `transactions.read` impide ambas consultas. El rol `CONSULTA` puede leer balances con sus permisos actuales, pero no registrar movimientos. Una cuenta de otra empresa se trata igual que una cuenta inexistente (`La cuenta no existe`) para no revelar su existencia.

### Operaciones y variables GraphQL

- [`operaciones_actividad7.graphql`](operaciones_actividad7.graphql): `BalanceCuenta`, `BalanceGeneral`, `RegistrarMovimientoConFecha` y `EliminarMovimiento`.
- [`operaciones.graphql`](operaciones.graphql): incluye al final las operaciones `BalanceCuenta` y `BalanceGeneral`.
- [`variables_actividad7/balance_cuenta.json`](variables_actividad7/balance_cuenta.json) y [`variables_actividad7/balance_general.json`](variables_actividad7/balance_general.json): variables de ejemplo (fechas y un `accountId` ficticio). No contienen tokens ni credenciales.

### Pruebas de la Actividad 7

La suite `tests/test_balances.py` contiene los casos B01–B16. Se ejecuta solo contra el entorno aislado `fintrack5_test`:

    docker exec -e PYTHONPATH=/app fintrack5-test-api python -m unittest tests.test_balances -v

Los datos de referencia se crean en empresas propias de la suite y se eliminan al finalizar. Antes de ejecutar, las guardas comprueban `DB_NAME=fintrack5_test`, `DB_HOST=postgres`, `current_database()`, la revisión de Alembic `3b9f41c7d2ae` y la disponibilidad de la API de pruebas; si algo no coincide, la suite aborta. No se deben ejecutar `setup_pruebas.py`, `limpiar_pruebas.py` ni `docker compose down -v` para preparar la ejecución: la suite no los necesita y podrían afectar datos ajenos.

Resultado real de la ejecución vigente (2026-10-29): **16/16 casos aprobados**, `Ran 16 tests in 2.533s`, `OK`, código de salida **0**. La salida completa está en [`evidencias/actividad7/B01_B16.txt`](evidencias/actividad7/B01_B16.txt).

Se conserva la ejecución histórica anterior a la prueba de `companyId` (15/15, `Ran 15 tests in 2.532s`, `OK`) en [`evidencias/actividad7/B01_B15.txt`](evidencias/actividad7/B01_B15.txt), sin modificar su contenido. El estado de cada caso está en [`evidencias_actividad7.md`](evidencias_actividad7.md).

> **Nota de sincronización:** el contenedor `fintrack5-test-api` ejecuta una copia del código creada al construir la imagen (no monta el árbol de trabajo). Si el código cambió después de esa construcción, reconstruya la imagen de pruebas o copie los archivos modificados antes de ejecutar la suite; de lo contrario se ejecutaría la versión anterior.

### Evidencias y capturas pendientes

La transcripción real de la suite está en `evidencias/actividad7/`. Las siguientes capturas son **manuales** y todavía **no existen**; deben tomarse en Visual Studio Code y guardarse en `evidencias/actividad7/capturas/`:

1. `evidencias/actividad7/capturas/01_implementacion_balances.png`: `services/balance_service.py`, líneas 55–111 (uso de `Decimal`, cuantización a dos decimales, saldo inicial, profit, saldo final e `isInRed`).
2. `evidencias/actividad7/capturas/02_graphql_y_pruebas.png`: `graphql_api/schema.py`, líneas 237–298 (tipos `AccountBalance`/`GeneralBalance` con `companyId`), y `tests/test_balances.py` desde la línea 1370 (prueba B16 de `companyId`).
3. `evidencias/actividad7/capturas/03_resultado_B01_B16.png`: `evidencias/actividad7/B01_B16.txt`, con las 16 líneas `ok`, `Ran 16 tests in 2.533s` y `OK` visibles.

### Diferencias respecto al enunciado

- **Motor de base de datos:** el enunciado menciona MySQL; el proyecto utiliza **PostgreSQL 16** y no se migró. Esta diferencia se documenta de forma transparente y requiere confirmación del docente.
- **Campo adicional:** `AccountBalance.currency` no forma parte del contrato mínimo del enunciado; se conserva como campo extra (superconjunto) y no rompe las consultas solicitadas.
- **Integrantes:** el README no puede completar los nombres porque no hay información verificable en el repositorio.

## Actividades

| Actividad | Propósito | Resultado | Evidencias |
|---|---|---|---|
| 3 | Autorización con roles y control de acceso por empresa | Matriz funcional 89/89 registros y suite de corrección 63/63 (pruebas distintas) | [`funcionales/`](evidencias/actividad3/funcionales/) y [`correcciones/`](evidencias/actividad3/correcciones/) |
| 4 | Configuración de permisos por roles vía GraphQL | Runner 34/34; matriz oficial 10/8/4/4 (26 permisos activos) | [`evidencias/actividad4/`](evidencias/actividad4/) |
| 5 | Contrato GraphQL para configurar permisos (`permissionCatalog`, `previewRolePermissions`, `setRolePermissions`) | Suite 18/18; evidencias E01–E10 y cierre de publicación | [`evidencias/actividad5_configuracion_permisos/`](evidencias/actividad5_configuracion_permisos/), [`evidencias.md`](evidencias.md) |
| 6 | Control de acceso según el rol: identidad desde JWT | Suite 20/20; evidencias E01–E10 | [`evidencias/actividad6_control_acceso/`](evidencias/actividad6_control_acceso/) |
| 7 | Balances por cuenta y balance general (`accountBalance`, `generalBalance`) | Implementado; suite B01–B16 16/16 en el entorno Docker aislado | [`evidencias_actividad7.md`](evidencias_actividad7.md), [`B01_B16.txt`](evidencias/actividad7/B01_B16.txt) |

Notas: las 30 operaciones protegidas de la Actividad 6 conservan la llamada a `exigir_permiso` sobre un catálogo global de roles y permisos, y `createCompany` y el primer `createCompanyAdmin` no están expuestos como operaciones GraphQL. Las evidencias E01–E10 de la Actividad 5 se capturaron con su contrato histórico (`actorCompanyUserId`); `operaciones.graphql` y `variables/` se actualizaron al contrato autenticado. El enunciado menciona MySQL, pero el proyecto conserva PostgreSQL 16.

## Evidencias

Las evidencias están en [`evidencias/`](evidencias/): capturas del entorno de pruebas y de las validaciones de negocio en la raíz, y transcripciones por actividad en las subcarpetas de las Actividades 3 a 7. La Actividad 6 incluye E01–E10, `resumen_actividad6.json` y el registro de la validación final en [`validacion_final.txt`](evidencias/actividad6_control_acceso/validacion_final.txt); la Actividad 7 conserva la ejecución vigente de la suite en [`B01_B16.txt`](evidencias/actividad7/B01_B16.txt) y la ejecución histórica anterior a `companyId` en [`B01_B15.txt`](evidencias/actividad7/B01_B15.txt). Las tres capturas manuales de la Actividad 7 se guardarán en `evidencias/actividad7/capturas/` (todavía no existen).

## Estado del proyecto

- **Implementado**: gestión de empresas, usuarios, membresías empresa-usuario, cuentas, conceptos y movimientos; autenticación JWT; autorización por roles con scope por empresa; contrato de configuración de permisos de la Actividad 5; control de acceso de la Actividad 6 (identidad desde token en las 30 operaciones protegidas); y balances de la Actividad 7 (`accountBalance` y `generalBalance`, con `GeneralBalance.companyId`).
- **Verificado**: suite B01–B16 16/16 en `fintrack5_test` (2026-10-29), `Ran 16 tests in 2.533s`, `OK`, código de salida 0; esquema con `companyId: ID!` y `generalBalance` sin argumento `companyId`; base sin residuos y conteos previos conservados.
- **Pruebas registradas**: Actividad 4 (34/34), Actividad 5 (18/18), Actividad 6 (20/20) y Actividad 7 (16/16), además de la matriz funcional y las suites de corrección de la Actividad 3.
- **Pendiente manual**: integrantes del equipo y las tres capturas de la Actividad 7.
- **Deuda explícita**: la idempotencia de `setup_pruebas.py` con dry-run de `limpiar_pruebas.py` y la verificación de rollback por inyección de fallo no se dan por aprobadas; véase [`evidencias/actividad3/correcciones/03_pendientes_y_validaciones.txt`](evidencias/actividad3/correcciones/03_pendientes_y_validaciones.txt).

## Control de versiones

La Actividad 7 se implementó sin crear commits, sin hacer push y sin modificar el historial. Las referencias locales de `main` y `origin/main` conservan el mismo commit registrado antes de esta actividad. Los cambios quedaron únicamente en el árbol de trabajo.

## Referencias

Documentación oficial de GraphQL, FastAPI, Strawberry GraphQL, SQLAlchemy, Alembic, PostgreSQL y PyJWT, junto con el material de clase.
