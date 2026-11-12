# Cálculo manual y conciliación — Unidad III, Actividad 1

**Proyecto:** FinTrack-5
**Periodo de demostración:** `2026-10-26` a `2026-10-30` (días completos UTC)
**Conjunto de datos:** B01 aislado (`FinTrack-5 Demo B01`, `companyId = 53`)
**Usuario de demostración:** `demo_b01@test.local`

Este documento separa de forma explícita tres cosas: los valores de referencia
del profesor, la respuesta real del backend y el cálculo manual. La conciliación
final solo se declara cuando los tres coinciden.

---

## A. Valores de referencia del profesor

| Indicador general | Valor de referencia |
|---|---:|
| `openingBalance` | 1000.00 |
| `totalIncome` | 3500.00 |
| `totalExpense` | 2900.00 |
| `profit` | 600.00 |
| `closingBalance` | 1600.00 |
| `isInRed` | false |
| `accountsInRed` | 1 |

| Cuenta | Saldo inicial | Ingresos | Egresos | Profit | Saldo final | En rojo |
|---|---:|---:|---:|---:|---:|---|
| Banco | 1000.00 | 3000.00 | 2200.00 | 800.00 | 1800.00 | No |
| Caja | 0.00 | 500.00 | 700.00 | -200.00 | -200.00 | Sí |
| Ahorro | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | No |
| **General** | **1000.00** | **3500.00** | **2900.00** | **600.00** | **1600.00** | **No** |

---

## B. Respuesta real de `generalBalance`

Consulta ejecutada contra la API real de pruebas con autenticación del usuario
`demo_b01@test.local`. La respuesta íntegra, sin token ni cabeceras, está en
[`../../evidencias/unidad3_actividad1_dashboard/resultados/general_balance_2026-10-26_2026-10-30.json`](../../evidencias/unidad3_actividad1_dashboard/resultados/general_balance_2026-10-26_2026-10-30.json).

### B.1 Respuesta general

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

### B.2 Desglose real por cuenta

| `accountId` | Cuenta | Activa | Saldo inicial | Ingresos | Egresos | Profit | Saldo final | En rojo |
|---:|---|---|---:|---:|---:|---:|---:|---|
| `89` | Banco B01 | Sí | 1000.00 | 3000.00 | 2200.00 | 800.00 | 1800.00 | No |
| `90` | Caja B01 | Sí | 0.00 | 500.00 | 700.00 | -200.00 | -200.00 | Sí |
| `91` | Ahorro B01 | Sí | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | No |

La colección `accounts` conserva las tres cuentas, incluidas las que no tienen
movimientos en el periodo. El backend es la única fuente de los importes: el
dashboard no suma ni recalcula saldos.

---

## C. Cálculo manual y conciliación

### C.1 Fórmulas aplicadas

```text
profit         = totalIncome - totalExpense
closingBalance = openingBalance + profit
```

Una cuenta está en números rojos cuando `closingBalance < 0`. El riesgo general
se calcula sobre el saldo final consolidado: `isInRed = closingBalance < 0`.
`accountsInRed` cuenta las cuentas individuales con saldo final negativo.

### C.2 Cálculo por cuenta

**Banco**

```text
profit         = 3000.00 - 2200.00 = 800.00
closingBalance = 1000.00 + 800.00  = 1800.00
1800.00 >= 0 → isInRed = false
```

**Caja**

```text
profit         = 500.00 - 700.00 = -200.00
closingBalance = 0.00 + (-200.00) = -200.00
-200.00 < 0 → isInRed = true
```

**Ahorro**

```text
profit         = 0.00 - 0.00 = 0.00
closingBalance = 0.00 + 0.00 = 0.00
0.00 >= 0 → isInRed = false
```

### C.3 Cálculo del balance general

Suma de las cuentas:

```text
openingBalance = 1000.00 + 0.00 + 0.00 = 1000.00
totalIncome    = 3000.00 + 500.00 + 0.00 = 3500.00
totalExpense   = 2200.00 + 700.00 + 0.00 = 2900.00
profit         = 800.00 + (-200.00) + 0.00 = 600.00
closingBalance = 1800.00 + (-200.00) + 0.00 = 1600.00
```

Comprobaciones solicitadas:

```text
3500.00 - 2900.00 = 600.00        ✓
1000.00 + 600.00  = 1600.00       ✓
1800.00 + (-200.00) + 0.00 = 1600.00 ✓
```

Cuentas en rojo:

```text
Caja: -200.00 < 0 → cuenta en rojo
Banco: 1800.00 >= 0 → sin riesgo
Ahorro: 0.00 >= 0 → sin riesgo
accountsInRed = 1
```

Riesgo general:

```text
closingBalance = 1600.00 >= 0 → isInRed = false
```

El resultado es coherente: la empresa no está en riesgo global, pero una cuenta
individual sí cierra en negativo.

### C.4 Tabla de conciliación

| Indicador | Referencia del profesor | Backend real | Cálculo manual | ¿Coincide? |
|---|---:|---:|---:|---|
| `openingBalance` | 1000.00 | 1000.00 | 1000.00 | Sí |
| `totalIncome` | 3500.00 | 3500.00 | 3500.00 | Sí |
| `totalExpense` | 2900.00 | 2900.00 | 2900.00 | Sí |
| `profit` | 600.00 | 600.00 | 600.00 | Sí |
| `closingBalance` | 1600.00 | 1600.00 | 1600.00 | Sí |
| `accountsInRed` | 1 | 1 | 1 | Sí |
| `isInRed` | false | false | false | Sí |

| Cuenta | Saldo final referencia | Saldo final real | Saldo final manual | ¿Coincide? |
|---|---:|---:|---:|---|
| Banco | 1800.00 | 1800.00 | 1800.00 | Sí |
| Caja | -200.00 | -200.00 | -200.00 | Sí |
| Ahorro | 0.00 | 0.00 | 0.00 | Sí |

**Conclusión:** los siete indicadores generales y las tres cuentas coinciden
exactamente entre la referencia, la respuesta real del backend y el cálculo
manual. La suma de los saldos finales de las cuentas (`1800.00 - 200.00 + 0.00`)
es igual al saldo final general (`1600.00`).

---

## D. Origen del conjunto B01

Los datos existentes de la empresa #11 no producían este caso. Para no alterar
datos ajenos se creó un conjunto aislado con el script idempotente
[`../../scripts/datos_demostracion_b01.py`](../../scripts/datos_demostracion_b01.py):

- Empresa `FinTrack-5 Demo B01`, `tax_id = B01-DEMO-2026`, `id = 53`.
- Usuario `demo_b01@test.local`, `id = 114`, membresía `122` con rol
  `ADMINISTRADOR`.
- Cuentas `Banco B01` (`89`), `Caja B01` (`90`) y `Ahorro B01` (`91`).
- Conceptos `Ingreso B01` (`71`) y `Egreso B01` (`72`).
- Cinco movimientos marcados `B01 demo ...`: un ingreso previo de 1000.00 el
  `2026-10-25` (saldo inicial), un ingreso de 3000.00 y un egreso de 2200.00 en
  Banco, un ingreso de 500.00 y un egreso de 700.00 en Caja, todos dentro del
  periodo.

El script solo opera sobre `fintrack5_test` en el host `postgres`, comprueba la
revisión de Alembic y es idempotente: una segunda ejecución reutiliza los
registros y no duplica movimientos. La limpieza (`--cleanup`) se limita a la
empresa y al usuario identificados por `B01-DEMO-2026` y
`demo_b01@test.local`.

## E. Evidencia histórica

La respuesta de enero de 2026 se conserva en
[`../../evidencias/unidad3_actividad1_dashboard/resultados/general_balance_enero_2026.json`](../../evidencias/unidad3_actividad1_dashboard/resultados/general_balance_enero_2026.json)
como evidencia anterior de la empresa #11. **No es el periodo principal de esta
entrega** y no se usa en la conciliación B01.
