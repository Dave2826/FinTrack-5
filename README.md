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
    │   ├── concept_repository.py
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
    │   ├── concept_service.py
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

    2ceeae7ff07c (head)

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