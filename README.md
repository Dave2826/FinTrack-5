# FinTrack-5

Backend para la gestión de cuentas, conceptos y movimientos financieros.

## Descripción

FinTrack-5 es una aplicación backend desarrollada para gestionar empresas, usuarios, cuentas financieras, conceptos de ingresos y egresos, relaciones entre cuentas y conceptos, y movimientos financieros.

La aplicación expone sus operaciones mediante GraphQL y utiliza una arquitectura por capas para separar la API, la lógica de negocio, el acceso a datos y la persistencia.

El proyecto integra autenticación mediante JWT para identificar al usuario responsable de registrar cada movimiento financiero.

## Arquitectura

La aplicación utiliza una arquitectura por capas con la siguiente estructura:

    GraphQL
        |
        v
    Services
        |
        v
    Repositories
        |
        v
    SQLAlchemy
        |
        v
    PostgreSQL

Cada capa tiene una responsabilidad específica:

- GraphQL: recibe las consultas y mutaciones del cliente.
- Services: contiene las reglas de negocio y validaciones.
- Repositories: concentra las operaciones de acceso a datos.
- SQLAlchemy: proporciona el mapeo entre objetos Python y tablas de PostgreSQL.
- PostgreSQL: almacena la información persistente del sistema.

## Módulos principales

- Gestión de empresas.
- Gestión de usuarios.
- Relación empresa-usuario.
- Gestión de cuentas financieras.
- Gestión de conceptos de ingresos y egresos.
- Relación cuenta-concepto.
- Gestión de movimientos financieros.
- Autenticación mediante JWT.
- Hash de contraseñas mediante Argon2.
- API GraphQL.
- Persistencia con PostgreSQL.
- Migraciones mediante Alembic.
- Contenedores mediante Docker Compose.

## Tecnologías

- Python 3.11
- FastAPI
- Strawberry GraphQL
- SQLAlchemy
- PostgreSQL 16
- Alembic
- Docker
- Docker Compose
- PyJWT
- pwdlib
- Argon2
- psycopg

## Estructura del proyecto

    FinTrack-5/
    ├── alembic/
    │   ├── versions/
    │   ├── env.py
    │   └── script.py.mako
    ├── database/
    │   └── connection.py
    ├── graphql_api/
    │   ├── context.py
    │   └── schema.py
    ├── models/
    │   ├── account.py
    │   ├── account_concept.py
    │   ├── company.py
    │   ├── company_user.py
    │   ├── concept.py
    │   ├── transaction.py
    │   └── user.py
    ├── repositories/
    │   ├── account_repository.py
    │   ├── account_concept_repository.py
    │   ├── company_repository.py
    │   ├── company_user_repository.py
    │   ├── company_user_role_repository.py
    │   ├── concept_repository.py
    │   ├── permission_repository.py
    │   ├── role_repository.py
    │   ├── role_permission_repository.py
    │   ├── transaction_repository.py
    │   └── user_repository.py
    ├── security/
    │   ├── __init__.py
    │   ├── jwt.py
    │   └── password.py
    ├── services/
    │   ├── account_service.py
    │   ├── account_concept_service.py
    │   ├── auth_service.py
    │   ├── authorization_service.py
    │   ├── company_user_service.py
    │   ├── concept_service.py
    │   ├── permission_service.py
    │   ├── role_permission_service.py
    │   ├── role_service.py
    │   ├── seed_service.py
    │   └── transaction_service.py
    ├── evidencias/
    ├── .dockerignore
    ├── .env.example
    ├── .gitignore
    ├── Dockerfile
    ├── README.md
    ├── alembic.ini
    ├── compose.yaml
    ├── main.py
    └── requirements.txt

## GraphQL

La API GraphQL está disponible en:

    http://localhost:8002/graphql

### Queries

Las principales consultas implementadas son:

- `accounts`
- `account`
- `concepts`
- `concept`
- `accountConcepts`
- `transactions`
- `companyUsers`

### Mutations

Las principales mutaciones implementadas son:

- `login`
- `createAccount`
- `createConcept`
- `assignConceptToAccount`
- `removeConceptFromAccount`
- `createTransaction`
- `deleteTransaction`

## Autenticación

El sistema utiliza JSON Web Tokens para autenticar al usuario que registra movimientos.

Primero se debe ejecutar la mutación `login` utilizando las credenciales correspondientes.

    mutation {
      login(
        input: {
          email: "correo_del_usuario"
          password: "contraseña"
        }
      ) {
        accessToken
        tokenType
      }
    }

El resultado proporciona un `accessToken`.

Para ejecutar operaciones protegidas se debe enviar el token mediante el encabezado HTTP:

    Authorization: Bearer <accessToken>

El movimiento financiero no recibe directamente el usuario desde el cliente. El usuario se obtiene a partir del token autenticado y se registra automáticamente en el campo `capturedBy`.

## Gestión de movimientos

Los movimientos utilizan dos tipos:

- `INCOME`: ingreso.
- `EXPENSE`: egreso.

Los movimientos deben cumplir las siguientes validaciones:

- El monto debe ser mayor que cero.
- La cuenta debe existir.
- La cuenta debe estar activa.
- El concepto debe existir.
- El concepto debe estar activo.
- El concepto debe estar permitido para la cuenta.
- El usuario debe estar autenticado.
- El usuario debe pertenecer a la empresa correspondiente.
- La cuenta y el concepto deben pertenecer a la misma empresa.
- El tipo del movimiento debe coincidir con el tipo del concepto.

El usuario responsable se registra mediante `capturedBy`.

La eliminación de movimientos se maneja de forma lógica mediante el campo `isActive`.

## Regla financiera

Los movimientos utilizan montos positivos.

El comportamiento financiero se determina por el tipo de movimiento:

- `INCOME`: representa un ingreso.
- `EXPENSE`: representa un egreso.

El saldo financiero se obtiene conceptualmente mediante:

    Balance = SUM(INCOME) - SUM(EXPENSE)

## Datos mínimos implementados

Como parte de la actividad se generaron los datos mínimos solicitados:

- 3 cuentas.
- 5 conceptos de ingreso.
- 5 conceptos de egreso.
- 10 relaciones cuenta-concepto.
- Más de 20 movimientos de prueba, incluyendo ingresos y egresos.

También se realizaron pruebas de validación mediante GraphQL.

## Validaciones probadas

Se probaron casos correctos y casos de error, incluyendo:

- Creación de un movimiento con usuario autenticado.
- Registro del usuario responsable mediante `capturedBy`.
- Monto igual a cero.
- Cuenta inexistente.
- Concepto inexistente.
- Concepto no permitido para una cuenta.
- Tipo de movimiento incompatible con el concepto.
- Consulta de movimientos.
- Eliminación lógica de movimientos.
- Prevención de relaciones cuenta-concepto duplicadas.
- Prevención de conceptos duplicados.

## Evidencias

Las evidencias de ejecución se encuentran en la carpeta `evidencias/`.

Las capturas disponibles corresponden a las siguientes pruebas:

- `01_create_account_success.png` — creación correcta de una cuenta.
- `02_accounts_minimum_3.png` — consulta de las cuentas creadas.
- `03_income_concepts_5.png` — conceptos de ingreso.
- `04_expense_concepts_5.png` — conceptos de egreso.
- `05_account_concept_relations_10.png` — relaciones cuenta-concepto.
- `06_duplicate_account_concept_error.png` — validación de relación duplicada.
- `08_transaction_income_authenticated.png` — creación de movimiento autenticado.
- `09_transaction_amount_validation.png` — validación de monto mayor que cero.
- `10_transaction_concept_account_validation.png` — validación de concepto permitido para la cuenta.
- `11_transaction_type_validation.png` — validación de compatibilidad entre movimiento y concepto.
- `12_transaction_account_not_found.png` — validación de cuenta inexistente.
- `13_transaction_concept_not_found.png` — validación de concepto inexistente.
- `14_transaction_income_success.png` — creación y consulta de movimiento de ingreso.
- `15_transaction_expense_success.png` — creación y consulta de movimiento de egreso.
- `17_transaction_delete_success.png` — eliminación lógica de un movimiento.

## Configuración del entorno

Antes de ejecutar el proyecto se debe crear un archivo `.env` tomando como referencia `.env.example`.

El archivo `.env` contiene las variables necesarias para configurar:

- Aplicación.
- PostgreSQL.
- pgAdmin.
- JWT.

El archivo `.env` está excluido del repositorio mediante `.gitignore`.

## Ejecución con Docker

Para iniciar los servicios:

    docker compose up -d

Para comprobar el estado de los contenedores:

    docker compose ps

La aplicación principal estará disponible en:

    http://localhost:8002

GraphQL estará disponible en:

    http://localhost:8002/graphql

PostgreSQL estará expuesto localmente mediante:

    localhost:5434

pgAdmin estará disponible en:

    http://localhost:5052

## Migraciones

Para aplicar las migraciones:

    docker compose exec api alembic upgrade head

Para consultar la migración actual:

    docker compose exec api alembic current

La migración actual utilizada por el proyecto es:

    3b9f41c7d2ae (head)

Migraciones existentes (orden):

    1f16b37ae1a4  base inicial (Actividad 5)
    2ceeae7ff07c  esquema financiero
    3b9f41c7d2ae  roles y permisos (Actividad 3)

## Actividad 3 — Autorización con roles y control de acceso

### Arquitectura de autorización

Las 25 operaciones GraphQL (10 queries y 15 mutations) pasan por
`services/authorization_service.py`, que expone `exigir_permiso`:

- Exige el permiso exacto (código) del rol activo de la membresía del
  actor en la empresa indicada (`actorCompanyUserId`).
- Aplica scope por empresa para recursos de negocio (cuentas,
  conceptos, transacciones, membresías y asignación de roles).
- El catálogo de roles y permisos es global (sin scope): las
  operaciones de catálogo exigen `roles.read` / `roles.write`.
- `is_admin` NO es un bypass: el alta como administrador asigna el
  rol ADMINISTRADOR con todos los permisos, pero toda operación sigue
  exigiendo el permiso correspondiente.
- Los errores de autorización se devuelven como errores GraphQL
  (HTTP 200 con payload `errors`), con mensajes fijos del código.

### Roles oficiales

- ADMINISTRADOR (protegido: no se puede desactivar ni retirarle
  `roles.write`).
- CONTADOR
- CAPTURISTA
- CONSULTA

### Permisos (catálogo de 10)

- company.users.read, company.users.write
- accounts.read, accounts.write
- concepts.read, concepts.write
- transactions.read, transactions.write
- roles.read, roles.write

### Módulos de la Actividad 3

- `services/authorization_service.py` — `exigir_permiso` y scope.
- `services/role_service.py`, `services/permission_service.py`,
  `services/role_permission_service.py` — catálogo.
- `services/company_user_service.py` — membresías empresa-usuario y
  asignación de roles.
- `services/seed_service.py` — roles y permisos iniciales.
- `repositories/role_repository.py`, `permission_repository.py`,
  `role_permission_repository.py`, `company_user_repository.py`,
  `company_user_role_repository.py`.
- Migración `3b9f41c7d2ae_roles_y_permisos.py`.

### Endurecimiento de autorización (corrección Actividad 5)

Correcciones aplicadas sobre la base de roles (evidencia completa en
`evidencias/actividad3/correcciones/`):

- `get_transaction_service` exige ahora `transactions.read` con scope
  de la cuenta de la transacción (antes era un servicio de lectura sin
  autorización); se eliminó su import muerto en `graphql_api/schema.py`.
- `deactivate_company_user_service` es atómica (membresía + roles en un
  solo commit con rollback) y aplica el guard del último administrador
  con mensaje fijo:
  `No se puede desactivar al último administrador de la empresa`
  (alcance: no queda ninguna membresía activa con rol ADMINISTRADOR
  activo en la empresa).
- `assign_role_service` rota el rol en una sola transacción; requiere
  `db.flush()` tras desactivar por el índice único parcial
  `uq_company_user_role_active(company_user_id) WHERE is_active`.
- Nueva query `companyUsers` (con `company.users.read` y scope por
  empresa): argumentos `actorCompanyUserId`, `companyId`, `activeOnly`
  (por defecto `true`).
- `create_company_admin_service` sigue siendo de uso exclusivo de
  bootstrap: solo se documentó, la lógica no cambió.

Decisiones aceptadas y documentadas (sin cambio de código):

- El catálogo de roles/permisos sigue siendo **global** (sin scope por
  empresa): un ADMINISTRADOR de una empresa puede alterar el catálogo
  que usan las demás. Aceptado y documentado.
- Riesgo de enumeración en login (F7): el mensaje propio de usuario
  inactivo permite discernir existencia de cuentas inactivas. Aceptado;
  los mensajes no se modifican.

Pendientes explícitos de la fase de corrección (NO ejecutados, NO
dados por aprobados): N10 (idempotencia de `setup_pruebas.py` +
dry-run de `limpiar_pruebas.py`) y la verificación de rollback por
inyección de fallo. Ambos requieren escribir en la base de datos y
quedaron fuera de autorización.

### Entorno de pruebas aislado (compose.test.yaml)

Existe un overlay de Compose, `compose.test.yaml`, que:

- Renombra los contenedores (`fintrack5-test-api`,
  `fintrack5-test-postgres`) y usa el volumen `fintrack5_test_pgdata`.
- Elimina la publicación de puertos (`ports: !reset []`): la API y la
  base solo son accesibles desde dentro de la red de Docker.
- Fija `DB_HOST=postgres` y `DB_NAME` a la base de pruebas
  `fintrack5_test` (distinta de la base de desarrollo `actividad5`).

Invocación canónica (desde la raíz del repo):

    docker compose -p fintrack5_test --env-file .env.test \
      -f compose.yaml -f compose.test.yaml <comando>

### Configuración del entorno de pruebas

Copia la plantilla y completa los valores ficticios que desees:

    cp .env.test.example .env.test

`.env.test` está excluido de Git (`.gitignore` y `.dockerignore`).
La plantilla solo incluye nombres de variables y valores de ejemplo;
no contiene credenciales reales.

Variables requeridas por `compose.test.yaml` (interpolación):
`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`,
`JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES`.
El servicio `pgadmin` (perfil `herramientas`) usa además
`PGADMIN_EMAIL` y `PGADMIN_PASSWORD`; las variables `APP_PORT`,
`POSTGRES_PORT` y `PGADMIN_PORT` se mantienen solo para la
interpolación del `compose.yaml` base.

### Preparación, pruebas y limpieza (solo sobre fintrack5_test)

Los scripts viven en `scripts/` y NO están dentro de la imagen: cópialos
al contenedor antes de ejecutarlos.

    docker compose -p fintrack5_test --env-file .env.test \
      -f compose.yaml -f compose.test.yaml cp scripts/setup_pruebas.py api:/app/scripts/setup_pruebas.py

    docker compose -p fintrack5_test --env-file .env.test \
      -f compose.yaml -f compose.test.yaml exec -T -e PYTHONPATH=/app api \
      python /app/scripts/setup_pruebas.py

Para limpiar (primero simula; aplica solo con `--confirm`):

    ... exec -T -e PYTHONPATH=/app api python /app/scripts/limpiar_pruebas.py
    ... exec -T -e PYTHONPATH=/app api python /app/scripts/limpiar_pruebas.py --confirm

ADVERTENCIAS:

- Ambos scripts se niegan a ejecutarse si `DB_NAME` no es
  `fintrack5_test` o si `DB_HOST` no es `postgres`: nunca apuntan a la
  base de desarrollo.
- `limpiar_pruebas.py` borra datos ficticios de `fintrack5_test` (las
  empresas "Pruebas Alpha SA" y "Pruebas Beta SA" y sus recursos);
  ejecuta primero sin `--confirm`.
- No ejecutes estos scripts contra la base de desarrollo `actividad5`.

Las pruebas funcionales de autorización (matriz de 89 registros) están
documentadas en `evidencias/actividad3/funcionales/`.

## Verificación de la aplicación

Para comprobar que FastAPI está funcionando:

    curl http://localhost:8002/

La aplicación debe responder con un mensaje indicando que el backend de la Actividad 5 está funcionando.

También se puede comprobar que el esquema GraphQL carga correctamente mediante:

    docker compose run --rm api python -c "import graphql_api.schema; print('schema OK')"

Para comprobar la compilación de los módulos principales:

    docker compose run --rm api python -m compileall models repositories services security graphql_api database

## Control de versiones

El proyecto utiliza Git para el control de versiones.

El commit correspondiente a la implementación de autenticación y gestión de movimientos es:

    18a2d75 feat: add authentication and transaction management

El proyecto se encuentra sincronizado con la rama principal del repositorio remoto.

## Seguridad

Las credenciales sensibles no se almacenan directamente en el código fuente.

Las variables sensibles se proporcionan mediante `.env`, mientras que `.env.example` contiene únicamente valores de referencia para configurar el entorno local.

Las contraseñas de usuario se almacenan mediante hash utilizando Argon2.

Los tokens de autenticación se generan mediante JWT y utilizan la clave definida mediante la variable de entorno `JWT_SECRET_KEY`.

## Referencias

- Documentación oficial de GraphQL.
- Documentación oficial de FastAPI.
- Documentación oficial de SQLAlchemy.
- Documentación oficial de Alembic.
- Material proporcionado durante la clase.

## Estado del proyecto

El backend correspondiente a la gestión de cuentas, conceptos y movimientos financieros se encuentra implementado y probado mediante GraphQL.

La aplicación cuenta con persistencia en PostgreSQL, migraciones mediante Alembic, arquitectura por capas, autenticación JWT, validaciones de reglas de negocio y evidencias de ejecución.