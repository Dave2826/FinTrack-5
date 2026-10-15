# Investigación — Actividad 5: configuración de permisos con GraphQL

> Fuentes consultadas el **14 de octubre de 2026** (verificadas por
> descarga directa; se indica la versión de cada documento).

## 1. Consultas y mutaciones en GraphQL

GraphQL distingue dos tipos de operaciones. Las *queries* solicitan datos
sin producir efectos secundarios, mientras que las *mutations*
"representan operaciones que modifican datos del servidor y/o causan
efectos secundarios" y pueden devolver cualquier tipo del esquema,
incluido el estado resultante de un objeto tras la actualización
(Strawberry GraphQL, *Mutations*). Esta distinción explica la arquitectura
de la actividad: `permissionCatalog` y `previewRolePermissions` son
*queries* de solo lectura, y `setRolePermissions` es la única *mutation*
de escritura. Además, la especificación establece que los campos de la
raíz `Mutation` se resuelven de forma serial: una mutación termina antes
de que inicie la siguiente, lo que serializa de forma natural las
aplicaciones de configuración (Strawberry GraphQL, *Mutations*, nota sobre
resolución serial). Otra propiedad relevante es la anulabilidad: los
campos de error se expresan como tipos anulables y la respuesta incluye
un arreglo `errors` con mensajes legibles por el cliente, tal como se
documenta en la especificación de GraphQL (spec.graphql.org, versión
estable *September 2025*, working draft del 28 de septiembre de 2026).
En esta actividad los errores de validación llegan sin enmascarar al
campo `errors`, por lo que el cliente recibe mensajes exactos como
"El rol no existe" o "permissionIds contiene IDs repetidos".

## 2. Autorización y gestión de permisos

El modelo implementado es RBAC (*role-based access control*): los
usuarios no poseen permisos directamente, sino que los obtienen por medio
de roles, y cada rol agrupa permisos granulares identificados por códigos
jerárquicos (`accounts.read`, `transactions.write`, `roles.write`…). El
catálogo se filtra por prefijo en SQL para cada recurso
(`COMPANY_USERS`, `ACCOUNTS`, `CONCEPTS`, `TRANSACTIONS`, `ROLES`),
evitando cargar el catálogo completo para filtrarlo en memoria.

Strawberry ofrece un mecanismo declarativo de autorización mediante
clases `Permission` con el método `has_permission`, que se aplican a cada
campo con `permission_classes`; cuando el método devuelve falso, la
respuesta contiene `data: null` y un error con el mensaje definido
(Strawberry GraphQL, *Permissions*). Esos mecanismos leen la información
del usuario desde `info.context`, que en FastAPI incorpora la solicitud
web. En FinTrack-5 la verificación se resolvió en la capa de servicios
(`exigir_permiso` y `_validar_actor`) porque el enunciado exige mensajes
de denegación byte a byte ("El rol no tiene el permiso {codigo}", "La
membresía no tiene un rol activo") y reglas de negocio adicionales que
trascienden un simple `has_permission`: por ejemplo, denegar toda
propuesta que intente reconfigurar el rol `ADMINISTRADOR`. La
autorización se evaluó siempre antes de tocar datos y sobre la membresía
activa del actor en la empresa del recurso.

## 3. Idempotencia e integridad transaccional

La mutación `setRolePermissions` recibe la **lista completa** de permisos
deseados y la aplica como tal, en lugar de "agregar" o "quitar"
incrementalmente. Una operación así es **idempotente**: aplicar la misma
propuesta N veces produce el mismo estado final y, a partir de la segunda
aplicación, el resumen reporta `changed: false` sin escribir filas nuevas.
La unicidad de la pareja `(role_id, permission_id)` (constraint
`uq_role_permission`) y la reactivación de la fila existente —conservando
su identificador— son las garantías físicas de esa idempotencia: la
evidencia E04/E05 demuestra que la concesión `accounts.write` mantiene el
mismo `id` (31) al aplicar S1, volver a S0 y aplicar S1 otra vez.

La integridad se apoya en las transacciones de PostgreSQL: una
transacción "agrupa varios pasos en una operación de todo-o-nada", sus
cambios intermedios no son visibles para otras transacciones concurrentes
y, si algo falla, "ninguno de los pasos afecta a la base de datos"
(PostgreSQL, *3.4. Transactions*). `setRolePermissionsService` ejecuta
todas las validaciones antes de escribir, calcula el plan, aplica
activaciones/reactivaciones, construye el resumen y realiza **un único
`commit`**; si cualquier excepción ocurre después del `flush` pero antes
del commit, se ejecuta `rollback` y la configuración previa permanece
intacta. La prueba E07 provoca exactamente esa falla controlada con
`mock.patch` y verifica desde una sesión nueva que no existió ningún
efecto persistido, ilustrando la atomicidad descrita por PostgreSQL
(`COMMIT` vs `ROLLBACK`).

## 4. Validación de entradas, errores y pruebas automatizadas

Toda propuesta pasa por una cadena de validación en orden determinista:
rol existe → rol activo → no es `ADMINISTRADOR` → IDs normalizados
(`"3"` y `3` equivalen, pero no pueden repetirse) → permisos existen →
permisos activos. Solo después se escribe. Strawberry señala que en una
aplicación real las mutaciones "suelen manejar errores y comunicarlos al
cliente" (Strawberry GraphQL, *Mutations*), y esa es la razón de
mantener los mensajes en español del enunciado.

Las pruebas se automatizaron con `unittest` (el proyecto no tiene
pytest):17 casos cubren catálogo con y sin filtro, autorización,
previsualización sin escrituras, aplicación S0→S1, idempotencia,
conservación de identificadores, las seis entradas inválidas, lista vacía
con no-restauración por la semilla, rollback E07 y continuidad. Las
guardas de las pruebas exigen explícitamente la base `fintrack5_test`,
el host `postgres` y la revisión de Alembic, de modo que es imposible
ejecutarlas contra la base de desarrollo `actividad5`.

## Fuentes

1. GraphQL Foundation. *GraphQL Specification* — https://spec.graphql.org/
   (última versión estable: September 2025; working draft: 28 sep 2026).
   Consultado el 14 oct 2026.
2. Strawberry GraphQL. *Mutations* —
   https://strawberry.rocks/docs/general/mutations (documentación v0.335.0).
   Consultado el 14 oct 2026.
3. Strawberry GraphQL. *Permissions* —
   https://strawberry.rocks/docs/guides/permissions (v0.335.0).
   Consultado el 14 oct 2026.
4. PostgreSQL Global Development Group. *3.4. Transactions* —
   https://www.postgresql.org/docs/current/tutorial-transactions.html
   (documentación de PostgreSQL 18). Consultado el 14 oct 2026.
5. Strawberry GraphQL. *Errors* — https://strawberry.rocks/docs/errors
   (v0.335.0). Consultado el 14 oct 2026.
