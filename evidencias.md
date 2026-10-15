# Evidencias — Actividad 5: configuración de permisos con GraphQL

Todas las evidencias se ejecutaron contra la base **`fintrack5_test`**
(Stack de pruebas `fintrack5_test`), con la API en el contenedor
`fintrack5-test-api`. Las transcripciones crudas (JSON/TXT) están en
`evidencias/actividad5_configuracion_permisos/`.

**Actor principal:** Ana Torres (`ana@test.local`), `company_user` 29,
empresa 5, rol `ADMINISTRADOR` (posee `roles.read` y `roles.write`).
**Actor sin autorización:** `capturista_a@test.local` (rol CAPTURISTA).
**Roles:** ADMINISTRADOR=1, CONTADOR=2, CAPTURISTA=3, CONSULTA=4.
**Permisos:** company.users.read=1 … roles.write=10 (catálogo oficial).
**Configuraciones:** S0 = 4 permisos originales de CAPTURISTA
(`accounts.read`, `concepts.read`, `transactions.read`,
`transactions.write`); S1 = S0 + `accounts.write` (5 permisos).

Las operaciones GraphQL provienen del entregable `operaciones.graphql`
con los archivos de `variables/` (mismo documento, misma
`operationName`), ejecutadas por `scripts/evidencias_actividad5.py`
dentro del contenedor.

## Resumen de resultados

| Evidencia | Descripción | Resultado | Archivo |
|---|---|---|---|
| E01 | Configuración inicial por rol (SQL) | MATRIZ OFICIAL 10/8/4/4, 0 duplicados | `E01_configuracion_inicial.json` |
| E02 | Catálogo sin filtro (10) y por recurso (2 c/u) + denegación a actor sin `roles.read` | APROBADO | `E02_catalogo_permisos.json` |
| E03 | Preview S0→S1 sin escrituras | `toActivate=[accounts.write]`, `finalCount=5`, matriz idéntica antes/después | `E03_preview_s1.json` |
| E04 | Aplicar S1 dos veces | 1ª: `changed=true`, `finalCount=5`; 2ª: `changed=false`; concesión `id=31` activa | `E04_aplicar_s1_dos_veces.json` |
| E05 | Aplicar S0 y volver a S1 | `mismo_identificador=true` (id 31 se conserva inactiva y reactiva) | `E05_estable_identificador.json` |
| E06 | Seis entradas inválidas + actor sin `roles.write` | 7/7 APROBADOS, matriz intacta, estados temporales restaurados | `E06_entradas_invalidas.json` |
| E07 | Rollback controlado tras `flush` sin `commit` (mock) | `OK` (prueba unitaria) + suite completa 18/18 | `E07_rollback_e07.txt`, `E07_pruebas_completas.txt` |
| E08 | Aplicar `permissionIds: []` + reinicio de la API | `changed=true`, 0 activas; tras reinicio persisten 0 | `E08_pre_lista_vacia.json`, `E08_post_reinicio.json`, `E08_reinicio_contenedor.json` |
| E09 | Restauración de la matriz oficial | `matriz_oficial_cumplida=true`, 10/8/4/4, 0 duplicados | `E09_restauracion.json` |
| E10 | Consulta de cuentas + movimiento real (cuenta 5, concepto 7 INCOME) | 9 cuentas (cuenta 5 visible); transacción id 18 amount 123.45 persistida | `E10_cuentas_y_movimiento.json` |
| E11 | Publicación del commit en GitHub (cierre documental) | `HEAD` = `origin/main` = `d33c5aa558d4ab87ce0293b1e11c0da87d3caae0`; `status` limpio; `diff --check HEAD` exit 0 | `11_publicacion_git.txt` |

Estado final verificado también en la raíz:
`configuracion_inicial.json` y `configuracion_final.json` (ambos con la
matriz oficial) y `comprobaciones.sql` (C1–C12 ejecutados, resultados
documentados en comentarios).

## Detalle por evidencia

### E01 — Configuración inicial
Captura SQL por códigos antes de tocar nada: ADMINISTRADOR 10,
CONTADOR 8, CAPTURISTA 4, CONSULTA 4; sin duplicados en
`(role_id, permission_id)`.

### E02 — Catálogo (`ExplorarCatalogo`)
- Sin filtro: 10 permisos activos ordenados por `code`.
- `COMPANY_USERS`, `ACCOUNTS`, `CONCEPTS`, `TRANSACTIONS`, `ROLES`:
  2 permisos cada uno, todos con el prefijo esperado.
- `capturista_a` (sin `roles.read`): `El rol no tiene el permiso
  roles.read` en `errors`, `data.permissionCatalog = null`.

### E03 — Previsualización (`RevisarConfiguracion`)
Propuesta S1 sobre CAPTURISTA: `current` = configuración activa previa
completa (los 4 de S0), `toActivate=[accounts.write]`,
`toDeactivate=[]`, `unchanged` = los 4 de S0, `finalCount=5`.
La matriz SQL antes y después es idéntica: la operación es de solo
lectura.

### E04 — Aplicación e idempotencia (`AplicarConfiguracion`)
1ª aplicación de S1: `changed=true`, `activated=[accounts.write]`,
`finalCount=5`; la concesión `accounts.write` de CAPTURISTA es la fila
`id=31`. 2ª aplicación idéntica: `changed=false`,
`activated=[]`, `unchanged` = 5 permisos; la fila sigue siendo `id=31`.

### E05 — Conservación del identificador
Aplicación de S0 (`changed=true`, `deactivated=[accounts.write]`,
`finalCount=4`, fila 31 inactiva) y reaplicación de S1 (fila 31
reactivada). `mismo_identificador=true`: la fila se reutiliza, nunca se
borra ni se duplica.

### E06 — Entradas inválidas
1. Rol inexistente (`roleId=999999`) → `El rol no existe`.
2. Rol inactivo (CONSULTA desactivado temporalmente) → `El rol no está
   activo`; CONSULTA restaurada (`is_active=t`).
3. Propuesta sobre `ADMINISTRADOR` (10 permisos y lista vacía) →
   `No se puede modificar la configuración de permisos del
   rol ADMINISTRADOR`.
4. Permiso inexistente mezclado con válidos → `El permiso con id 999999
   no existe`.
5. Permiso inactivo (`concepts.write` desactivado temporalmente) →
   `El permiso concepts.write no está activo`; permiso restaurado
   (`is_active=t`).
6. IDs repetidos (`["31","31"]` equivalente `"3"` vs `3`) →
   `permissionIds contiene IDs repetidos: 31`.
7. (Adición) Actor sin `roles.write` →
   `El rol no tiene el permiso roles.write`.

En todos los casos `setRolePermissions` devolvió `data=null` con error,
y la matriz SQL antes/después quedó idéntica (`estado_intacto=true`).

Nota metodológica: las variantes 2 y 5 requieren un rol/permiso inactivo
para poder observarse vía GraphQL; se prepararon con SQL directo
(`UPDATE`) y se restauraron inmediatamente dentro del mismo script,
verificando la restauración en la propia evidencia. La suite unitaria
cubre además ambos casos a nivel de servicio (pruebas `test_09` y
`test_12`) sin tocar el esquema.

### E07 — Rollback (fallo controlado)
`tests/test_configuracion_permisos.py::test_15` aplica S1 con
`mock.patch` sobre `_construir_resumen` (falla después del `flush` y
antes del `commit`), espera la excepción, hace `rollback` y verifica
desde una **sesión nueva** que ninguna fila cambió. Salida:
`Ran 1 test … OK`. La suite completa corre 18/18 (`E07_pruebas_completas.txt`).

### E08 — Lista vacía + reinicio de la API
- Pre: `setRolePermissions(permissionIds=[])` sobre CAPTURISTA →
  `changed=true`, `finalCount=0`, 0 permisos activos.
- Reinicio: `docker restart fintrack5-test-api`.
  `E08_reinicio_contenedor.json` documenta
  `StartedAt=2026-10-15T02:25:53.899093666Z`, intermedio entre el UTC
  de E08-pre (`02:25:53.175`) y el de E08-post (`02:26:12.055`): el
  contenedor se reinició entre ambas fases.
- Post: la API volvió a responder (login OK) y CAPTURISTA continuó con
  0 permisos activos y `finalCount=0`: la configuración vacía persistió
  (no es un estado en memoria).

### E09 — Restauración
Aplicación de S0 sobre CAPTURISTA → `changed=true`; la matriz activa
vuelve a ser exactamente la oficial (10/8/4/4) sin duplicados.

### E10 — Continuidad del negocio
Como Ana: consulta `accounts(companyId=5)` devuelve 9 cuentas incluida
la cuenta 5; `createTransaction(cuenta 5, concepto 7, INCOME, 123.45)`
crea la transacción **id 18**, confirmada por SQL en `transactions`.

### E11 — Publicación del commit (cierre documental)
A diferencia de E01–E10, esta evidencia no se ejecutó contra la base
de pruebas: registra la verificación de Git del cierre (15-oct-2026,
sin pruebas ni escrituras en base de datos). `git ls-remote` y
`git fetch` confirman que `origin/main` =
`d33c5aa558d4ab87ce0293b1e11c0da87d3caae0`, idéntico a `HEAD`;
`git status --short --branch` limpio (`## main...origin/main`) y
`git diff --check HEAD` exit 0. Registro completo en
`11_publicacion_git.txt`.

## Reproducción

```bash
# Suite de pruebas (18 tests)
docker exec -e PYTHONPATH=/app fintrack5-test-api \
  python -m unittest tests.test_configuracion_permisos -v

# Evidencias E01–E10 (fases)
docker exec -e PYTHONPATH=/app fintrack5-test-api \
  python /app/scripts/evidencias_actividad5.py e01   # … e02 e03 e04 e05 e06
docker exec -e PYTHONPATH=/app fintrack5-test-api \
  python /app/scripts/evidencias_actividad5.py e08pre
docker restart fintrack5-test-api
docker exec -e PYTHONPATH=/app fintrack5-test-api \
  python /app/scripts/evidencias_actividad5.py e08post   # … e09 e10 final

# Comprobaciones SQL
docker exec -i fintrack5-test-postgres psql \
  -U fintrack5_test_user -d fintrack5_test < comprobaciones.sql
```
