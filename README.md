# FinTrack-5

Backend de gestión financiera (empresas, usuarios, cuentas, conceptos y movimientos) expuesto mediante GraphQL, con autenticación JWT y autorización por roles y permisos.

## Descripción

FinTrack-5 separa la API GraphQL, la lógica de negocio, el acceso a datos y la persistencia en capas. Cada petición autentica al usuario con un token JWT y evalúa, contra la base de datos, si el rol activo de su membresía tiene el permiso que exige la operación.

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
    ├── tests/                 suites de las Actividades 5 y 6
    ├── variables/             variables de las operaciones de la Actividad 5
    ├── variables_actividad6/  variables de la Actividad 6
    ├── evidencias/            capturas y transcripciones por actividad
    ├── operaciones.graphql, operaciones_actividad6.graphql, comprobaciones.sql
    ├── evidencias.md, investigacion.md
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

## Actividades

| Actividad | Propósito | Resultado | Evidencias |
|---|---|---|---|
| 3 | Autorización con roles y control de acceso por empresa | Matriz funcional 89/89 registros y suite de corrección 63/63 (pruebas distintas) | [`funcionales/`](evidencias/actividad3/funcionales/) y [`correcciones/`](evidencias/actividad3/correcciones/) |
| 4 | Configuración de permisos por roles vía GraphQL | Runner 34/34; matriz oficial 10/8/4/4 (26 permisos activos) | [`evidencias/actividad4/`](evidencias/actividad4/) |
| 5 | Contrato GraphQL para configurar permisos (`permissionCatalog`, `previewRolePermissions`, `setRolePermissions`) | Suite 18/18; evidencias E01–E10 y cierre de publicación | [`evidencias/actividad5_configuracion_permisos/`](evidencias/actividad5_configuracion_permisos/), [`evidencias.md`](evidencias.md) |
| 6 | Control de acceso según el rol: identidad desde JWT | Suite 20/20; evidencias E01–E10 | [`evidencias/actividad6_control_acceso/`](evidencias/actividad6_control_acceso/) |

Notas: las 30 operaciones protegidas de la Actividad 6 conservan la llamada a `exigir_permiso` sobre un catálogo global de roles y permisos, y `createCompany` y el primer `createCompanyAdmin` no están expuestos como operaciones GraphQL. Las evidencias E01–E10 de la Actividad 5 se capturaron con su contrato histórico (`actorCompanyUserId`); `operaciones.graphql` y `variables/` se actualizaron al contrato autenticado. El enunciado menciona MySQL, pero el proyecto conserva PostgreSQL 16.

## Evidencias

Las evidencias están en [`evidencias/`](evidencias/): capturas del entorno de pruebas y de las validaciones de negocio en la raíz, y transcripciones por actividad en las subcarpetas de las Actividades 3 a 6. La Actividad 6 incluye E01–E10, `resumen_actividad6.json` y el registro de la validación final en [`validacion_final.txt`](evidencias/actividad6_control_acceso/validacion_final.txt).

## Estado del proyecto

- **Implementado**: gestión de empresas, usuarios, membresías empresa-usuario, cuentas, conceptos y movimientos; autenticación JWT; autorización por roles con scope por empresa; contrato de configuración de permisos de la Actividad 5; y control de acceso de la Actividad 6 (identidad desde token en las 30 operaciones protegidas).
- **Pruebas registradas**: Actividad 4 (34/34), Actividad 5 (18/18) y Actividad 6 (20/20), además de la matriz funcional y las suites de corrección de la Actividad 3.
- **Deuda explícita**: la idempotencia de `setup_pruebas.py` con dry-run de `limpiar_pruebas.py` y la verificación de rollback por inyección de fallo no se dan por aprobadas; véase [`evidencias/actividad3/correcciones/03_pendientes_y_validaciones.txt`](evidencias/actividad3/correcciones/03_pendientes_y_validaciones.txt).

## Control de versiones

La implementación de la Actividad 6 está registrada en el commit local `c38ee1f` (`feat(auth): implement JWT access control for activity 6`). La rama `main` está un commit por delante de `origin/main`, ese commit aún no se ha publicado y los cambios de este `README.md` siguen sin confirmar.

## Referencias

Documentación oficial de GraphQL, FastAPI, Strawberry GraphQL, SQLAlchemy, Alembic, PostgreSQL y PyJWT, junto con el material de clase.
