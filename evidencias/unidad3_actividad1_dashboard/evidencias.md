# Evidencias — Unidad III, Actividad 1: dashboard financiero

**Proyecto:** FinTrack-5
**Equipo:** David Morales · Edwuard Chay · Fabrizio Rodriguez
**Actividad:** Unidad III, Actividad 1 (Actividad #12)
**Fecha de captura:** 2026-11-11 (hora local)

Este documento registra la evidencia de la Actividad 12. El periodo principal de
demostración es **2026-10-26 a 2026-10-30** sobre el conjunto aislado **B01**
(`FinTrack-5 Demo B01`, `companyId = 53`). La evidencia de enero de 2026 se
conserva al final, claramente identificada como histórica y ajena al periodo
principal.

La distribución de tiempos del guion es de exposición; no atribuye autoría
individual del código.

---

## 1. Objetivo y alcance

| Evidencia | Objetivo |
|---|---|
| `resultados/general_balance_2026-10-26_2026-10-30.json` | Respuesta real de `generalBalance` para el periodo B01, sin token ni cabeceras. |
| `capturas/11_dashboard_b01_1440x900.png` | Dashboard real con los cinco indicadores, el riesgo global y el conteo de cuentas en rojo del periodo B01. |
| `capturas/12_detalle_cuentas_b01_1440x900.png` | Detalle real de Banco, Caja y Ahorro con sus importes y estados. |
| `capturas/10_token_invalido_1440x900.png` | Estado final del login tras un rechazo real del backend por token inválido. |
| `resultados/token_invalido_respuesta.txt` | Respuesta GraphQL real del rechazo, redactada y sin credenciales. |
| `docs/unidad3_actividad1/calculo_manual.md` | Referencia del profesor, respuesta real y conciliación manual. |
| `resultados/lint.txt`, `typecheck.txt`, `test.txt`, `build.txt` | Validaciones del frontend. |
| `resultados/git_publicacion.txt` | Instantánea histórica previa a la limpieza: rama, `HEAD`, últimos commits y estado del árbol. Se conserva sin cambios. |
| `resultados/git_publicacion_final.txt` | Cierre de la Actividad 12: estado final de Git, rotación de credenciales, restauración de la empresa #11, validaciones y empaquetado. |

**Fuera de alcance:** iniciar la Actividad 13, implementar un dashboard
administrativo, añadir gráficas, modificar la empresa #11, alterar usuarios o
permisos existentes, recrear contenedores o volúmenes y publicar cambios con
commit o push.

---

## 2. Entorno de la demostración

| Elemento | Valor |
|---|---|
| Backend GraphQL real | `http://127.0.0.1:8001/graphql` (contenedor de pruebas expuesto en loopback) |
| Frontend real | Vite + React + TypeScript + Apollo Client, en `http://localhost:5173` |
| Navegador de la captura 10 | Google Chrome, controlado por CDP, viewport 1440 × 900 |
| Usuario de demostración | `demo_b01@test.local` — «Administrador Demo B01», empresa #53 |
| Empresa | `FinTrack-5 Demo B01`, `tax_id = B01-DEMO-2026`, `id = 53` |
| Contraseña | Obtenida de `scripts/setup_pruebas.py` (constante `CONTRASENA_PRUEBAS`). **No se escribe, imprime ni captura.** |
| Periodo principal | `2026-10-26` a `2026-10-30` (días completos UTC) |
| Zona horaria | Fechas interpretadas como UTC por el backend |

Procedimiento del backend temporal:
[`../../docs/acceso-temporal-api-pruebas.md`](../../docs/acceso-temporal-api-pruebas.md).

No se publicaron los puertos de PostgreSQL ni de pgAdmin. Los contenedores de
pruebas se iniciaron sin recrearlos.

---

## 3. Conjunto B01 aislado

La empresa #11 no contenía los valores solicitados: su consulta para
`2026-10-26` a `2026-10-30` devolvía `openingBalance = 1231.00`, sin ingresos ni
egresos, y sus cuentas no eran Banco/Caja/Ahorro. Para no modificar datos ajenos
se creó un conjunto separado con
[`../../scripts/datos_demostracion_b01.py`](../../scripts/datos_demostracion_b01.py).

| Elemento | Identificador |
|---|---|
| Empresa | `FinTrack-5 Demo B01`, `tax_id = B01-DEMO-2026`, `id = 53` |
| Usuario | `demo_b01@test.local`, `id = 114` |
| Membresía | `id = 122`, rol `ADMINISTRADOR` activo |
| Cuenta Banco | `Banco B01`, `id = 89` |
| Cuenta Caja | `Caja B01`, `id = 90` |
| Cuenta Ahorro | `Ahorro B01`, `id = 91` |
| Concepto ingreso | `Ingreso B01`, `id = 71` |
| Concepto egreso | `Egreso B01`, `id = 72` |

Movimientos (cinco, marcados `B01 demo ...`):

| Fecha | Cuenta | Tipo | Importe |
|---|---|---|---:|
| 2026-10-25 | Banco B01 | Ingreso | 1000.00 |
| 2026-10-26 | Banco B01 | Ingreso | 3000.00 |
| 2026-10-27 | Caja B01 | Ingreso | 500.00 |
| 2026-10-28 | Banco B01 | Egreso | 2200.00 |
| 2026-10-29 | Caja B01 | Egreso | 700.00 |

El ingreso del 25 de octubre queda antes del periodo y forma el saldo inicial de
Banco. El script solo opera sobre `fintrack5_test` en el host `postgres`,
comprueba la revisión de Alembic y es idempotente: una segunda ejecución reutilizó
los registros y el conteo siguió en cinco movimientos, sin duplicados. La limpieza
(`--cleanup`) se limita a la empresa `B01-DEMO-2026` y al usuario
`demo_b01@test.local`.

No se modificó la empresa #11, sus usuarios, sus permisos ni sus movimientos.

---

## 4. Resultado real de `generalBalance`

Consulta ejecutada con autenticación real de `demo_b01@test.local`. La respuesta
íntegra está en
[`resultados/general_balance_2026-10-26_2026-10-30.json`](resultados/general_balance_2026-10-26_2026-10-30.json).

| Campo | Valor real |
|---|---:|
| `companyId` | `"53"` |
| `fromDate` | `"2026-10-26"` |
| `toDate` | `"2026-10-30"` |
| `openingBalance` | `"1000.00"` |
| `totalIncome` | `"3500.00"` |
| `totalExpense` | `"2900.00"` |
| `profit` | `"600.00"` |
| `closingBalance` | `"1600.00"` |
| `accountsInRed` | `1` |
| `isInRed` | `false` |
| `currency` | `"MXN"` |

| Cuenta | Saldo inicial | Ingresos | Egresos | Utilidad | Saldo final | En rojo |
|---|---:|---:|---:|---:|---:|---|
| Banco B01 | 1000.00 | 3000.00 | 2200.00 | 800.00 | 1800.00 | No |
| Caja B01 | 0.00 | 500.00 | 700.00 | -200.00 | -200.00 | Sí |
| Ahorro B01 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | No |
| **General** | **1000.00** | **3500.00** | **2900.00** | **600.00** | **1600.00** | **No** |

La suma de los saldos finales de las cuentas (`1800.00 - 200.00 + 0.00`) coincide
con el saldo final general (`1600.00`). El dashboard muestra exactamente esos
importes y el bloque «Sin riesgo global · 1 cuenta en números rojos».

La conciliación completa, con las fórmulas y la tabla de tres columnas, está en
[`../../docs/unidad3_actividad1/calculo_manual.md`](../../docs/unidad3_actividad1/calculo_manual.md).

---

## 5. Capturas del periodo principal

Ubicación: `evidencias/unidad3_actividad1_dashboard/capturas/`.

| # | Archivo | Viewport | Escenario | Resultado observado |
|---|---|---|---|---|
| 10 | [`10_token_invalido_1440x900.png`](capturas/10_token_invalido_1440x900.png) | 1440 × 900 | Sesión real, token sustituido en memoria por una cadena dummy y «Actualizar» | Login visible con «Tu sesión expiró por seguridad. Vuelve a iniciar sesión.»; sin indicadores ni tabla; token limpio. |
| 11 | [`11_dashboard_b01_1440x900.png`](capturas/11_dashboard_b01_1440x900.png) | 1440 × 900 | Sesión real con `demo_b01@test.local`, periodo B01 | `$1,000.00`, `$3,500.00`, `$2,900.00`, `$600.00`, `$1,600.00`; «Sin riesgo global» y «1 cuenta en números rojos». |
| 12 | [`12_detalle_cuentas_b01_1440x900.png`](capturas/12_detalle_cuentas_b01_1440x900.png) | 1440 × 900 | Mismo periodo, desplazado al detalle | Banco, Caja y Ahorro con sus importes; Caja marcada «En riesgo» con `-$200.00`. |

### Verificaciones hechas durante la captura

- **Indicadores (11):** los cinco valores del DOM coinciden con la respuesta real
  de la API y con la conciliación manual.
- **Riesgo global (11):** se leen directamente `isInRed = false` y
  `accountsInRed = 1`; la interfaz muestra «Sin riesgo global» y «1 cuenta en
  números rojos». El bloque es una región con nombre accesible, encabezado propio
  y texto explícito; el color no es el único portador del estado.
- **Detalle (12):** las tres cuentas se muestran con sus importes; Caja conserva
  la insignia «En riesgo». No se recalculan saldos en el cliente.
- **Responsive:** la tabla se convierte en tarjetas por debajo de 900 px y el
  encabezado se apila; las capturas móviles históricas 06–08 documentan el mismo
  comportamiento de la interfaz.
- **Token inválido (10):** el backend respondió «Token inválido o expirado»; el
  frontend ejecutó el logout, limpió el token y la caché, volvió al login y no
  dejó visibles `BalanceSummary` ni `AccountsTable`.

### Seguridad de las capturas

- No se capturaron tokens JWT, cabeceras `Authorization`, cookies ni DevTools con
  la sesión abierta.
- La contraseña nunca se escribió en un archivo, no se imprimió en la terminal y
  no aparece en ninguna imagen. El campo de contraseña solo muestra su
  `placeholder` enmascarado.
- Los correos y empresas son datos ficticios del entorno de pruebas.
- La captura 10 se tomó con el frontend y el backend reales; no se usó un mock ni
  una contraseña incorrecta como sustituto.

---

## 6. Evidencia de token inválido

Procedimiento aplicado, sin mocks:

1. Iniciar sesión normalmente con `demo_b01@test.local`.
2. Aplicar el periodo B01 y comprobar los cinco indicadores.
3. Sustituir **solo en memoria** el token por la cadena dummy
   `token-invalido-demo-b01` mediante el mecanismo de desarrollo documentado en
   [`../../dashboard/README.md`](../../dashboard/README.md):
   `tokenStore.set('token-invalido-demo-b01')` desde la consola de Vite.
4. Pulsar «Actualizar» para que la siguiente petición use ese valor.
5. El backend rechazó la petición con el cuerpo real guardado en
   [`resultados/token_invalido_respuesta.txt`](resultados/token_invalido_respuesta.txt):
   `{"data":null,"errors":[{"message":"Token inválido o expirado", ...}]}`.
6. El frontend ejecutó `logout('expired')` una sola vez, limpió `tokenStore` y la
   caché de Apollo, cambió a estado anónimo y mostró el login.
7. El estado final se verificó en el navegador: `tokenStore.get() === null`,
   ausencia de `SALDO INICIAL` y de «Detalle de cuentas», aviso visible con
   `role="alert"`.

La captura 10 muestra el estado final del login, no una pantalla simulada.

---

## 7. Resultados de validación

Ejecutados el 2026-11-11. Los archivos conservan la salida real y el código de
salida de cada comando.

| Comando | Código de salida | Resultado | Archivo |
|---|---:|---|---|
| `npm run lint` | 0 | Oxlint sin hallazgos | [`resultados/lint.txt`](resultados/lint.txt) |
| `npm run typecheck` | 0 | `tsc --noEmit` sin errores en `tsconfig.app.json` y `tsconfig.node.json` | [`resultados/typecheck.txt`](resultados/typecheck.txt) |
| `npm test` | 0 | **14 archivos de prueba aprobados, 140 pruebas aprobadas** | [`resultados/test.txt`](resultados/test.txt) |
| `npm run build` | 0 | `tsc -b && vite build` correcto; build de producción generado | [`resultados/build.txt`](resultados/build.txt) |
| Backend `tests/test_balances.py` | 0 | **16/16 casos aprobados**, `Ran 16 tests in 2.544s`, `OK` | [`../actividad7/B01_B16.txt`](../actividad7/B01_B16.txt) |

Resumen textual de Vitest:

```text
 Test Files  14 passed (14)
      Tests  140 passed (140)
```

La Actividad 12 añadió seis pruebas al frontend:

- `expired` provoca logout una sola vez.
- `unauthenticated` provoca logout una sola vez.
- `forbidden` no cierra la sesión.
- Un error de red no cierra la sesión.
- Un rango de fechas inválido no cierra la sesión.
- Los datos previos se descartan y el logout no se repite durante un refetch.

También se actualizó la prueba de integración para exigir el regreso al login, el
mensaje de sesión expirada, la limpieza del token y la ausencia de indicadores y
tabla. Se conservaron las pruebas de permisos, red, fechas y expiración local del
JWT.

### Validación del JSON de GraphQL

- Archivo: [`resultados/general_balance_2026-10-26_2026-10-30.json`](resultados/general_balance_2026-10-26_2026-10-30.json).
- Contiene exclusivamente `{ "generalBalance": { ... } }`.
- No incluye token, cookie, cabecera HTTP, contraseña ni datos de conexión.
- Los valores coinciden con la tabla de la sección 4 y con las capturas 11 y 12.

### Cierre de la Actividad 12

- **Credenciales:** rotación completada en los entornos de desarrollo y de
  pruebas. Las credenciales anteriores ya no autentican y las nuevas funcionan en
  PostgreSQL, FastAPI, Alembic y las suites. No se recreó ningún volumen.
- **Empresa #11:** restaurada a 5 cuentas y 4 movimientos (baseline real); la base
  completa queda en 9 cuentas y 10 movimientos. Solo se eliminaron los fixtures
  A4 de la última ejecución (cuentas 115 y 116, movimiento 194).
- **B01:** intacta, con 3 cuentas, 5 movimientos y los importes de la sección 4.
- **Backend:** `test_balances` 16/16, `test_control_acceso_rol` 20/20 y
  `test_configuracion_permisos` 18/18, todos `OK`.
- **Paquete:** 286 entradas y 121 evidencias; SHA-256 en
  [`../../SHA256SUMS.txt`](../../SHA256SUMS.txt), fuera del ZIP.
- **Detalle verificable:**
  [`resultados/git_publicacion_final.txt`](resultados/git_publicacion_final.txt).

---

## 8. Evidencia histórica de enero de 2026

Se conserva sin modificaciones como evidencia anterior de la empresa #11. **No es
el periodo principal de esta entrega** y no se usa en la conciliación B01.

| Elemento | Valor histórico |
|---|---|
| Empresa | #11, `Pruebas Alpha SA` |
| Usuario | `admin_a@test.local` |
| Periodo | `2026-01-01` a `2026-01-31` |
| JSON | [`resultados/general_balance_enero_2026.json`](resultados/general_balance_enero_2026.json) |
| Capturas | 01 a 09 |

Las capturas 01–09 documentan el login, los indicadores, el detalle de cinco
cuentas, los errores de rango y login, la vista móvil y la simulación de riesgo.
La captura 09 está etiquetada de forma visible como **simulación de prueba** y no
se presenta como dato real. La captura 05 es una contraseña incorrecta, no un
token inválido; la evidencia auténtica de token inválido es la captura 10.

---

## 9. Limitaciones y notas

1. **B01 es un conjunto de demostración aislado.** Se creó para reproducir el caso
   solicitado sin alterar datos existentes. No sustituye a la empresa #11 ni a sus
   movimientos.
2. **La evidencia de enero es histórica.** Sus importes y capturas no deben
   presentarse como el resultado del periodo principal.
3. **La captura 09 es una simulación.** Se conserva solo como ilustración
   histórica; el riesgo real de esta entrega está en B01 (una cuenta en rojo).
4. **El token vive solo en memoria.** Al recargar la página la sesión termina; no
   se persiste en `localStorage`, `sessionStorage`, cookies ni IndexedDB.
5. **El backend es la única fuente financiera.** El cliente formatea importes,
   pero no suma, resta ni recalcula `isInRed` o `accountsInRed`.

---

## 10. Reproducción

```bash
# Backend de pruebas (procedimiento autorizado, sin recrear contenedores)
# Ver ../../docs/acceso-temporal-api-pruebas.md

# Conjunto B01 aislado (idempotente)
docker cp scripts/datos_demostracion_b01.py fintrack5-test-api:/app/scripts/datos_demostracion_b01.py
docker exec -e PYTHONPATH=/app fintrack5-test-api python scripts/datos_demostracion_b01.py --apply

# Frontend
cd dashboard
npm install
npm run dev

# Validaciones
npm run lint
npm run typecheck
npm test
npm run build
```

Usuario: `demo_b01@test.local`. Empresa: `FinTrack-5 Demo B01` (#53). Periodo:
`2026-10-26` a `2026-10-30`.

---

## 11. Enlaces relacionados

- [README del equipo](../../README.md)
- [README técnico del dashboard](../../dashboard/README.md)
- [Cálculo manual](../../docs/unidad3_actividad1/calculo_manual.md)
- [Guion de exposición](../../docs/unidad3_actividad1/guion_exposicion.md)
- [Procedimiento de la API temporal](../../docs/acceso-temporal-api-pruebas.md)
- [Estado de Git (instantánea histórica)](resultados/git_publicacion.txt)
- [Cierre y publicación final](resultados/git_publicacion_final.txt)
- [SHA-256 del paquete de entrega](../../SHA256SUMS.txt)
