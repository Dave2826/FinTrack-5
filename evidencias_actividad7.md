# Evidencias — Actividad 7: balances por cuenta y balance general

> **Nombre del archivo:** se conserva `evidencias.md` de la Actividad 5
> sin cambios. La evidencia de la Actividad 7 se registra en este archivo
> para no sobrescribir el entregable anterior.

> **Estado de ejecución:** la suite `tests/test_balances.py` se ejecutó
> contra el entorno aislado `fintrack5_test` (PostgreSQL 16 en Docker) el
> **2026-10-29**. Resultado de la ejecución vigente (incluye B16, el campo
> `companyId`): **16/16 casos aprobados**, `Ran 16 tests in 2.533s`, `OK`,
> código de salida **0**. La salida completa se conserva en
> [`evidencias/actividad7/B01_B16.txt`](evidencias/actividad7/B01_B16.txt).
>
> Se conserva además la ejecución histórica anterior a B16 (15/15,
> `Ran 15 tests in 2.532s`) en
> [`evidencias/actividad7/B01_B15.txt`](evidencias/actividad7/B01_B15.txt),
> sin alterar su contenido. Ese archivo representa el estado previo a la
> incorporación de `GeneralBalance.companyId`.

## Entorno de la ejecución

Comprobado antes de lanzar la suite (solo lectura):

| Comprobación | Resultado |
|---|---|
| `fintrack5-test-api` | Activo |
| `fintrack5-test-postgres` | Activo, PostgreSQL 16 |
| `current_database()` | `fintrack5_test` |
| `alembic_version` | `3b9f41c7d2ae` |
| `role_permissions` activas | 26 |

Comando ejecutado desde PowerShell, dentro del contenedor `api`:

```powershell
docker exec -e PYTHONPATH=/app fintrack5-test-api python -m unittest tests.test_balances -v
```

La salida se capturó con stdout y stderr redirigidos al archivo de
evidencia, conservando el código de salida real del proceso (`0`).

## Tabla B01–B16

| Caso | Objetivo | Preparación | Resultado esperado | Resultado obtenido | Estado | Evidencia o explicación |
|---|---|---|---|---|---|---|
| B01 | Referencia de Banco, Caja, Ahorro y general; las consultas no mutan filas | Empresa propia con Banco (25-oct ingreso 1000.00; 26-oct ingreso 3000.00; 27-oct egreso 1200.00; 28-oct egreso 1000.00), Caja (26-oct ingreso 500.00; 29-oct egreso 700.00) y Ahorro sin movimientos; periodo 2026-10-26 a 2026-10-30 | Banco: opening 1000.00, income 3000.00, expense 2200.00, profit 800.00, closing 1800.00, isInRed false. Caja: 0.00, 500.00, 700.00, -200.00, -200.00, true. Ahorro: todo 0.00, false. General: 1000.00, 3500.00, 2900.00, 600.00, 1600.00, accountsInRed 1, isInRed false. Snapshot de cuentas y movimientos idéntico antes/después | Coincide con lo esperado; el snapshot antes/después fue idéntico | APROBADO | `test_01_b01_referencia_y_sin_mutaciones`; `B01_B16.txt` |
| B02 | Periodo de un solo día para Banco | Consultar Banco del 2026-10-28 al 2026-10-28 | opening 2800.00, income 0.00, expense 1000.00, profit -1000.00, closing 1800.00, isInRed false | Coincide con lo esperado | APROBADO | `test_02_b02_banco_un_solo_dia`; `B01_B16.txt` |
| B03 | Empresa sin cuentas | Empresa propia sin cuentas; consultar balance general | `accounts: []`; importes 0.00; accountsInRed 0; isInRed false; currency MXN | Coincide con lo esperado | APROBADO | `test_03_b03_empresa_sin_cuentas`; `B01_B16.txt` |
| B04 | Límites UTC inclusivo/exclusivo | Cuenta propia con movimientos 2026-10-25T23:59:59Z (100.00), 2026-10-26T00:00:00Z (10.00), 2026-10-30T23:59:59Z (5.00) y 2026-10-31T00:00:00Z (200.00); consultar 26–30, 25 y 31 | 26–30: opening 100.00, income 10.00, expense 5.00, profit 5.00, closing 105.00. 25: income 100.00. 31: opening 105.00, income 200.00, closing 305.00 | Coincide con lo esperado | APROBADO | `test_04_b04_limites_utc`; `B01_B16.txt` |
| B05 | `transactionDate` manda sobre `capturedAt` | Crear por GraphQL un ingreso de 30.00 con `transactionDate=2026-01-15T12:00:00Z`; consultar 15 y 16 de enero de 2026 | 15-ene: income 30.00, closing 30.00. 16-ene: opening 30.00, income 0.00, closing 30.00. `capturedAt` posterior a `transactionDate` | Coincide con lo esperado | APROBADO | `test_05_b05_fecha_operacion_manda_sobre_captura`; `B01_B16.txt` |
| B06 | Precisión decimal | Ingresos 0.10 y 0.20; egreso 0.30 el 2026-10-28 | income 0.30, expense 0.30, profit 0.00, closing 0.00, isInRed false | Coincide con lo esperado | APROBADO | `test_06_b06_precision_decimal`; `B01_B16.txt` |
| B07 | Movimiento inactivo | Ingreso previo 100.00 (20-oct), ingreso 50.00 (28-oct) y baja lógica del segundo con `deleteTransaction` | opening 100.00, income 0.00, closing 100.00 | Coincide con lo esperado | APROBADO | `test_07_b07_movimiento_inactivo`; `B01_B16.txt` |
| B08 | Cuenta inactiva conserva historial | Ingresos 100.00 (20-oct) y 50.00 (28-oct); `accounts.is_active=false`; consultar cuenta y general | `isActive=false`; opening 100.00, income 50.00, closing 150.00; el general incluye la cuenta y suma 150.00 | Coincide con lo esperado; `is_active` restaurado en `finally` | APROBADO | `test_08_b08_cuenta_inactiva_conserva_historial`; `B01_B16.txt` |
| B09 | Conceptos adicionales no duplican | Dos conceptos de ingreso permitidos, un movimiento de 10.00 con cada uno | totalIncome 20.00, profit 20.00, closing 20.00 (no 40.00) | Coincide con lo esperado | APROBADO | `test_09_b09_conceptos_adicionales_no_duplican`; `B01_B16.txt` |
| B10 | Validación de fechas | `fromDate=2026-10-31`, `toDate=2026-10-01`; y `fromDate=2026-02-30` | Error controlado por intervalo invertido; error de escalar `Date` por fecha inexistente; `data` nulo | Coincide con lo esperado | APROBADO | `test_10_b10_validacion_de_fechas`; `B01_B16.txt` |
| B11 | Autenticación obligatoria | Token ausente, alterado (primer carácter de la firma) y vencido; ambas consultas | `data` nulo y error en todos los casos | Coincide con lo esperado | APROBADO | `test_11_b11_autenticacion_obligatoria`; `B01_B16.txt` |
| B12 | Aislamiento multiempresa | Empresa A (Banco/Caja/Ahorro) y Empresa B (una cuenta con ingreso 100.00); además, un ID inexistente | Cuenta de B con token de A y cuenta inexistente: mismo error "La cuenta no existe" (no revela existencia). Cuenta de A con token de B: mismo error. General de A solo contiene cuentas de A; general de B solo contiene cuentas de B | Coincide con lo esperado | APROBADO | `test_12_b12_aislamiento_multiempresa`; `B01_B16.txt` |
| B13 | Rol CONSULTA | Usuario con rol CONSULTA en Empresa A; consultar ambos balances y intentar `createTransaction` | Ambas consultas exitosas; `createTransaction` rechazado con `transactions.write`; sin filas nuevas | Coincide con lo esperado | APROBADO | `test_13_b13_rol_consulta_lee_pero_no_escribe`; `B01_B16.txt` |
| B14 | Retiro temporal de `transactions.read` | Retirar el permiso al rol CONSULTA; consultar; restaurar en `finally` | Ambas consultas rechazadas con `transactions.read`; tras restaurar, vuelven a funcionar y la relación activa queda en 1 | Coincide con lo esperado; permiso restaurado | APROBADO | `test_14_b14_retiro_temporal_de_transactions_read`; `B01_B16.txt` |
| B15 | Saldo negativo | Empresa propia con una sola cuenta sin movimientos previos y egreso 50.00 el 2026-10-28 | Cuenta: opening 0.00, income 0.00, expense 50.00, profit -50.00, closing -50.00, isInRed true. General: closing -50.00, accountsInRed 1, isInRed true | Coincide con lo esperado | APROBADO | `test_15_b15_saldo_negativo`; `B01_B16.txt` |
| B16 | `companyId` de la empresa autenticada | Empresas A y B de la suite; consultar el general con el token de cada administrador y, con el token de A, enviar `companyId` como argumento | A devuelve `companyId` = id de A; B devuelve el id de B; las cuentas de B son solo de B; el argumento `companyId` se rechaza en validación GraphQL y el token de A sigue devolviendo A | Coincide con lo esperado | APROBADO | `test_16_b16_company_id_autenticada`; `B01_B16.txt` |

## Validaciones posteriores a la ejecución

Comprobadas mediante consultas de solo lectura:

| Comprobación | Resultado |
|---|---|
| Código de salida de la suite | 0 |
| Casos aprobados | 16/16 |
| `GeneralBalance.companyId` | Expuesto como `ID!`; `generalBalance` solo acepta `fromDate` y `toDate` |
| `current_database()` | `fintrack5_test` |
| `alembic_version` | `3b9f41c7d2ae` |
| `role_permissions` activas | 26 |
| `CONSULTA/transactions.read` activo | 1 relación |
| Empresas residuales `Pruebas Balance A7%` | 0 |
| Usuarios residuales `a7_%@test.local` | 0 |
| Conteos previos conservados | `companies=2`, `company_users=10`, `company_user_roles=11`, `accounts=6`, `concepts=3`, `account_concepts=3`, `transactions=5`, `users=12`, `role_permissions=28` |
| Empresas 11/12 y usuarios 54–65 | Presentes sin cambios |

La suite no dejó residuos y restauró el permiso que B14 retira
temporalmente.

## Validaciones estáticas realizadas previamente

1. **Sintaxis Python:** `ast.parse` correcto en
   `repositories/balance_repository.py`, `services/balance_service.py`,
   `services/transaction_service.py`, `graphql_api/schema.py` y
   `tests/test_balances.py`.
2. **Fórmulas y fechas:** se cargó `services/balance_service.py` con
   stubs de sus dependencias y se comprobaron:
   - límites UTC de un día y de un intervalo;
   - rechazo de intervalo invertido;
   - B01 (1800.00, -200.00, 0.00), B06 (0.00) y B15 (-50.00);
   - totales generales 1000.00 / 3500.00 / 2900.00 / 600.00 / 1600.00.
3. **Validación de importes y fechas de transacción:** se cargó
   `services/transaction_service.py` con stubs y se comprobó que acepta
   15.5 → 15.50 y 1.230 → 1.23, y rechaza 0, negativos, NaN, infinito,
   1.234 y 1E+20; una fecha con offset -06:00 se normaliza a UTC naive.
4. **Agregación SQL:** se ejecutó `list_account_balance_rows` sobre
   SQLite en memoria con los datos de B01, B02 y B04. Se verificaron
   `LEFT JOIN`, filtros en el `ON`, exclusión de movimientos inactivos,
   cuentas sin movimientos, cuentas inactivas y orden por `account_id`.
5. **No revelación de cuentas ajenas:** con stubs de permisos y del
   repositorio de cuentas se comprobó que una cuenta de otra empresa y
   una cuenta inexistente producen exactamente el mismo error
   `La cuenta no existe`. La comprobación de `accounts.read` ocurre
   antes de buscar la cuenta.
6. **Alteración de JWT:** se comprobó con `base64.urlsafe_b64decode`
   que cambiar el primer carácter de una firma de 32 bytes altera los
   bytes decodificados, mientras que cambiar el último puede caer en los
   bits de relleno Base64 y conservar la firma. B11 usa el primer
   carácter para garantizar la invalidez.

## Reproducción

Con el entorno aislado `fintrack5_test` levantado y autorizado:

```bash
# 1. Comprobar guardas y revisión Alembic (solo lectura)
docker exec -e PYTHONPATH=/app fintrack5-test-api alembic current

# 2. Ejecutar la suite B01–B16
docker exec -e PYTHONPATH=/app fintrack5-test-api \
  python -m unittest tests.test_balances -v

# 3. Regresión de las suites existentes
docker exec -e PYTHONPATH=/app fintrack5-test-api \
  python -m unittest tests.test_control_acceso_rol -v
docker exec -e PYTHONPATH=/app fintrack5-test-api \
  python -m unittest tests.test_configuracion_permisos -v
```

La suite crea sus propias empresas, cuentas, conceptos y movimientos, y
los elimina en `tearDownClass`/`tearDown`. No requiere ejecutar
`setup_pruebas.py` de nuevo, pero sí que el catálogo de roles y permisos
exista en `fintrack5_test`.

> **Nota de sincronización:** el contenedor `fintrack5-test-api` ejecuta
> una copia del código creada al construir la imagen (no monta el árbol de
> trabajo). Si el código cambió después de esa construcción, reconstruya la
> imagen de pruebas o copie los archivos modificados antes de ejecutar la
> suite; de lo contrario se ejecutaría la versión anterior. La ejecución
> de B01_B16.txt se hizo tras sincronizar `graphql_api/schema.py`,
> `services/balance_service.py` y `tests/test_balances.py` en el
> contenedor.
