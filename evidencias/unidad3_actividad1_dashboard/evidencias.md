# Evidencias — Unidad III, Actividad 1: dashboard financiero

**Proyecto:** FinTrack-5
**Equipo:** David Morales · Edwuard Chay · Fabrizio Rodriguez
**Subetapa:** 3.7 (documentación, evidencias y paquete de entrega)
**Fecha de captura:** 2026-11-10 (hora local)

Este documento registra las evidencias de la subetapa 3.7. La base del dashboard
corresponde a las subetapas 3.1 a 3.6, publicadas en el commit
`a95226a7303113c1705c8e67b8c7bc9b19f83fbf`. La revisión final de 3.7 completa el
indicador global de riesgo con los campos `isInRed` y `accountsInRed`; no se
modificaron el backend, GraphQL, los servicios, los modelos ni los datos reales.

---

## 1. Objetivo y alcance

| Evidencia | Objetivo |
|---|---|
| Capturas 01–09 | Demostrar el funcionamiento real del login, los indicadores, el indicador global de riesgo, el detalle por cuenta, dos errores y la vista móvil. La captura 09 es una simulación de prueba identificada como tal. |
| `resultados/lint.txt` | Confirmar que el análisis estático termina sin hallazgos. |
| `resultados/typecheck.txt` | Confirmar que TypeScript compila en modo estricto sin errores. |
| `resultados/test.txt` | Registrar la ejecución completa de Vitest, incluidos los cinco escenarios del indicador global. |
| `resultados/build.txt` | Confirmar que el build de producción se genera. |
| `resultados/general_balance_enero_2026.json` | Conservar la respuesta real de `generalBalance` para el periodo de demostración, sin tokens ni cabeceras. |
| `resultados/git_publicacion.txt` | Dejar constancia de la rama, el `HEAD`, los últimos commits y el estado del árbol. |

**Fuera de alcance:** modificar backend, GraphQL, servicios, modelos, base de datos
o Docker; alterar datos reales para provocar escenarios especiales; retirar
permisos para fabricar errores. Los escenarios de riesgo que no existen en los
datos reales se cubren con pruebas y, cuando se ilustran, se etiquetan como
simulación.

---

## 2. Entorno de la demostración

| Elemento | Valor |
|---|---|
| Backend GraphQL real | `http://127.0.0.1:8001/graphql` (contenedor de pruebas expuesto en loopback) |
| Frontend real | Vite + React + TypeScript + Apollo Client, servido en `http://localhost:5174` durante la captura |
| Navegador | Google Chrome 156, controlado por el protocolo DevTools (CDP) en modo headless |
| Usuario de prueba | `admin_a@test.local` — «Admin Pruebas Alpha», empresa #11, 5 cuentas |
| Contraseña | Obtenida del mecanismo local de pruebas (`scripts/setup_pruebas.py`, constante `CONTRASENA_PRUEBAS`). **No se escribe, imprime ni captura.** |
| Periodo de demostración | `2026-01-01` a `2026-01-31` (días completos UTC) |
| Zona horaria | Fechas interpretadas como UTC por el backend |

**Nota sobre el puerto:** la instancia de Vite que ya estaba abierta en el puerto
5173 servía una versión intermedia en caché de la hoja de estilos. Para las
capturas se levantó una instancia propia en el puerto 5174, con el mismo código
fuente y el mismo proxy `/graphql` hacia `8001`. No se modificó ningún archivo
para lograrlo.

Procedimiento del backend temporal: [`../../docs/acceso-temporal-api-pruebas.md`](../../docs/acceso-temporal-api-pruebas.md).

---

## 3. Valores reales verificados

Antes de usar los valores se repitió la consulta `generalBalance` contra la API
real. Respuesta obtenida (también guardada en
[`resultados/general_balance_enero_2026.json`](resultados/general_balance_enero_2026.json)):

| Campo | Valor |
|---|---:|
| `companyId` | `11` |
| `fromDate` | `2026-01-01` |
| `toDate` | `2026-01-31` |
| `openingBalance` | `0.00` |
| `totalIncome` | `1500.00` |
| `totalExpense` | `300.00` |
| `profit` | `1200.00` |
| `closingBalance` | `1200.00` |
| `accountsInRed` | `0` |
| `isInRed` | `false` |
| `currency` | `MXN` |
| Cuentas en `accounts` | 5 |
| Indicador global mostrado | «Sin riesgo global» · «0 cuentas en números rojos» |

El indicador global usa directamente `isInRed` y `accountsInRed`. No se recalcula
el riesgo ni se infiere a partir de los saldos individuales. El caso
`isInRed = false` con `accountsInRed > 0` también es válido: se muestra «Sin
riesgo global» y el conteo exacto de cuentas individuales en rojo.

Las cinco cuentas son «Cuenta Alpha Pruebas» y cuatro cuentas de la Actividad 4.
Solo «Cuenta Alpha Pruebas» tiene movimientos en el periodo; las demás aparecen
en cero porque no se ocultan las cuentas sin movimientos.

> El periodo predeterminado del dashboard es el mes UTC actual. Para la
> demostración se cambia manualmente a enero de 2026, porque el mes actual no
> tiene movimientos registrados.

---

## 4. Capturas

Ubicación: `evidencias/unidad3_actividad1_dashboard/capturas/`.

| # | Archivo | Viewport | Escenario | Resultado observado |
|---|---|---|---|---|
| 01 | [`01_login_1440x900.png`](capturas/01_login_1440x900.png) | 1440 × 900 | Pantalla de login limpia, sin credenciales escritas | Dos columnas, marca FinTrack-5, formulario y nota de sesión en memoria. Sin contraseña ni token visibles. |
| 02 | [`02_dashboard_indicadores_1440x900.png`](capturas/02_dashboard_indicadores_1440x900.png) | 1440 × 900 | Sesión real con `admin_a@test.local`, periodo enero 2026 | Cinco indicadores: `$0.00`, `$1,500.00`, `$300.00`, `$1,200.00`, `$1,200.00`; bloque «Sin riesgo global» con «0 cuentas en números rojos»; encabezado con empresa #11 y vigencia. |
| 03 | [`03_detalle_cuentas_1440x900.png`](capturas/03_detalle_cuentas_1440x900.png) | 1440 × 900 | Mismo periodo, desplazado al detalle | Cinco cuentas, insignias «Activa» y «Sin riesgo», importes MXN y saldo final de `$1,200.00` en la cuenta con movimientos. |
| 04 | [`04_error_rango_1440x900.png`](capturas/04_error_rango_1440x900.png) | 1440 × 900 | Fecha inicial `10/02/2026` y final `01/02/2026`, pulsar «Consultar» | Mensaje «La fecha inicial no puede ser posterior a la fecha final.», campos marcados y foco en «Fecha inicial»; `role="alert"`. |
| 05 | [`05_error_login_1440x900.png`](capturas/05_error_login_1440x900.png) | 1440 × 900 | Contraseña incorrecta, pulsar «Entrar» | Mensaje «El correo o la contraseña no son correctos. Verifica tus datos e inténtalo de nuevo.»; contraseña enmascarada; `role="alert"`. |
| 06 | [`06_dashboard_movil_375x812.png`](capturas/06_dashboard_movil_375x812.png) | 375 × 812 | Dashboard real con enero 2026 en viewport móvil | Encabezado apilado y filtro en una columna, sin desplazamiento horizontal (`scrollWidth` = 375). |
| 07 | [`07_dashboard_movil_cuentas_375x812.png`](capturas/07_dashboard_movil_cuentas_375x812.png) | 375 × 812 | Detalle de cuentas en móvil, con enero 2026 | Cada cuenta se presenta como tarjeta con sus etiquetas; sin desplazamiento horizontal. Complementa la captura 06. |
| 08 | [`08_indicador_global_movil_375x812.png`](capturas/08_indicador_global_movil_375x812.png) | 375 × 812 | Resumen real desplazado al indicador global, enero 2026 | «Sin riesgo global» y «0 cuentas en números rojos» en una sola columna; `scrollWidth` = 375 y ancho del bloque = 301 px. |
| 09 | [`09_simulacion_riesgo_1440x900.png`](capturas/09_simulacion_riesgo_1440x900.png) | 1440 × 900 | **Simulación de prueba** con respuesta `generalBalance` mock interceptada | Aviso visible «SIMULACIÓN DE PRUEBA»; «Riesgo financiero global», «2 cuentas en números rojos», utilidad y saldo final negativos. **No es un dato real.** |

### Verificaciones hechas durante la captura

- **Indicadores (02):** los cinco valores del DOM coinciden con la respuesta real
  de la API (`$0.00`, `$1,500.00`, `$300.00`, `$1,200.00`, `$1,200.00`).
- **Indicador global (02 y 08):** se leen directamente `isInRed = false` y
  `accountsInRed = 0`; la interfaz muestra «Sin riesgo global» y «0 cuentas en
  números rojos». El bloque es una región con nombre accesible, encabezado
  propio y texto explícito; el color no es el único portador del estado.
- **Responsive del indicador (08):** a 375 px el bloque mide 301 px de ancho y
  usa una sola columna (`grid-template-columns: 264px`); `scrollWidth` = 375.
  A 1440 px conserva dos columnas y `scrollWidth` = 1440.
- **Error de rango (04):** el mensaje tiene `role="alert"`, ambos campos quedan
  con `aria-invalid="true"` y el foco se mueve a `#dashboard-from-date`.
- **Error de login (05):** el campo de contraseña es de tipo `password` y su valor
  no aparece en la captura.
- **Móvil (06 y 07):** `document.documentElement.scrollWidth` = 375 px, el
  encabezado mide 327 px de ancho, la tabla usa `display: block`, el encabezado
  de la tabla queda visualmente oculto y cada fila se presenta como tarjeta con
  etiquetas `data-label`.
- **Simulación (09):** la respuesta se sustituyó únicamente en el navegador
  mediante intercepción de red para la captura. La imagen incluye un aviso fijo
  «SIMULACIÓN DE PRUEBA» y no se usó para modificar la base ni la API.

### Seguridad de las capturas

- No se capturaron tokens JWT, cabeceras `Authorization`, cookies ni DevTools con
  la sesión abierta.
- La contraseña nunca se escribió en un archivo, no se imprimió en la terminal y
  no aparece en ninguna imagen.
- El correo `admin_a@test.local` es un dato ficticio del entorno de pruebas.

---

## 5. Resultados de validación

Ejecutados en `dashboard/` el 2026-11-10. Los archivos conservan la salida real y
el código de salida de cada comando.

| Comando | Código de salida | Resultado | Archivo |
|---|---:|---|---|
| `npm run lint` | 0 | Oxlint sin hallazgos | [`resultados/lint.txt`](resultados/lint.txt) |
| `npm run typecheck` | 0 | `tsc --noEmit` sin errores en `tsconfig.app.json` y `tsconfig.node.json` | [`resultados/typecheck.txt`](resultados/typecheck.txt) |
| `npm test` | 0 | **14 archivos de prueba aprobados, 134 pruebas aprobadas** | [`resultados/test.txt`](resultados/test.txt) |
| `npm run build` | 0 | `tsc -b && vite build` correcto; build de producción generado | [`resultados/build.txt`](resultados/build.txt) |

Resumen textual de Vitest:

```text
 Test Files  14 passed (14)
      Tests  134 passed (134)
```

La corrección añadió ocho pruebas: cinco escenarios del indicador global
(`false/0`, `true/1`, `true/>1`, `false/1`, singular/plural), dos de
accesibilidad y una de compatibilidad responsive. Las pruebas existentes se
mantuvieron y siguen aprobadas.

Los scripts se verificaron en `dashboard/package.json` antes de ejecutarlos; no se
asumieron nombres.

### Validación del JSON de GraphQL

- Archivo: [`resultados/general_balance_enero_2026.json`](resultados/general_balance_enero_2026.json).
- Contiene exclusivamente `{ "data": { "generalBalance": { ... } } }`.
- No incluye token, cookie, cabecera HTTP, contraseña ni datos de conexión.
- Los valores coinciden con la tabla de la sección 3 y con la captura 02.

---

## 6. Casos cubiertos solo por pruebas automatizadas

Los datos reales disponibles no permiten reproducir estos escenarios sin
modificar la base o los permisos, lo cual está prohibido en esta subetapa. Por eso
se documentan y se remiten a la suite existente.

| Caso | Por qué no se reproduce con datos reales | Prueba que lo cubre |
|---|---|---|
| Cuenta en números rojos | `accountsInRed = 0` e `isInRed = false`; ninguna cuenta real cierra en negativo. Provocarlo exigiría registrar egresos o alterar datos. | `dashboard/tests/accountsTable.test.tsx` → «identifica una cuenta en riesgo» y «representa una cuenta activa y en riesgo». |
| Error de permisos | Los cuatro roles operativos de prueba pueden leer `generalBalance`; retirar `transactions.read` modificaría permisos reales. | `dashboard/tests/dashboardBalance.test.tsx` → «muestra el error de permisos sin ofrecer reintento ni cerrar sesión». |
| Empresa sin cuentas | No hay una empresa accesible sin cuentas en el entorno de pruebas. | `dashboard/tests/dashboardA11y.test.tsx` → «anuncia el estado vacío de cuentas mediante role status» y `accountsTable.test.tsx` → «muestra un estado vacío informativo cuando no hay cuentas». |
| Error de red y reintento | Requiere cortar la red o el backend; no se fuerza sobre el entorno real. | `dashboardBalance.test.tsx` → «clasifica un error de red y permite reintentar» y `dashboardA11y.test.tsx` → «permite reintentar una actualización fallida y mueve el foco al título». |
| Cuenta inactiva | Las cinco cuentas reales están activas. | `accountsTable.test.tsx` → «identifica una cuenta inactiva» y «representa una cuenta inactiva sin riesgo». |
| Riesgo global (`isInRed = true`) | Los datos reales tienen `isInRed = false`; provocarlo exigiría alterar movimientos o la base. | `dashboardBalance.test.tsx` → «presenta riesgo global y una cuenta en rojo…» y «usa el plural…». La captura 09 lo ilustra como **simulación de prueba**. |
| `isInRed = false` con `accountsInRed > 0` | Los datos reales tienen `accountsInRed = 0`; el contrato permite el caso, pero no existe en el periodo demostrado. | `dashboardBalance.test.tsx` → «no contradice el caso válido sin riesgo global con una cuenta en rojo». |
| Singular y plural del conteo | Depende de `accountsInRed`, que es 0 en los datos reales. | `dashboardBalance.test.tsx` → «mantiene el singular y el plural diferenciados». |

**Roles verificados:** se comprobó con login real que `consulta_a@test.local`,
`capturista_a@test.local` y `contador_a@test.local` pueden ejecutar
`generalBalance` con sus permisos actuales. Por eso no existe un caso real de
«permiso denegado» que capturar sin alterar la configuración.

Solo se generó la captura 09 para ilustrar el escenario de riesgo global. Está
etiquetada de forma visible como **simulación de prueba** y no se presenta como
dato real. Los demás casos siguen cubiertos únicamente por pruebas automatizadas.

---

## 7. Limitaciones de los datos reales

1. **No hay cuentas en rojo.** El contrato devuelve `accountsInRed = 0` y
   `isInRed = false`. La interfaz muestra «Sin riesgo» en todas las cuentas y el
   indicador global muestra «Sin riesgo global» con «0 cuentas en números rojos».
2. **Los datos reales solo ejercitan el estado sin riesgo global.** Los estados
   «Riesgo financiero global» y «cuentas individuales en rojo» se verifican con
   pruebas y con la captura 09, identificada como simulación de prueba. No se
   alteró la base ni la API para producirla.
3. **No hay empresa sin cuentas** accesible con los usuarios de prueba.
4. **No se puede fabricar un error de autorización** sin retirar permisos, lo que
   modificaría datos reales.
5. **El periodo por defecto no tiene movimientos.** Es el mes UTC actual; la
   demostración usa enero de 2026.

---

## 8. Boceto

- Editable: [`../../docs/unidad3_actividad1/boceto_dashboard.svg`](../../docs/unidad3_actividad1/boceto_dashboard.svg)
- Exportación: [`../../docs/unidad3_actividad1/boceto_dashboard.png`](../../docs/unidad3_actividad1/boceto_dashboard.png) (3200 × 3120 px)

**Aclaración:** el boceto se elaboró **a partir de la interfaz ya implementada**.
No representa un diseño previo al desarrollo ni un prototipo distinto de lo que
se entregó. Incluye encabezado, filtro de fechas, cinco indicadores, indicador
global de riesgo (`isInRed` y `accountsInRed`), riesgo por cuenta, tabla, estados
de la interfaz y adaptación responsive. El boceto representa el estado real sin
riesgo; los estados de riesgo se documentan en la captura simulada 09 y en las
pruebas automatizadas.

---

## 9. Reproducción

```bash
# Backend de pruebas (procedimiento autorizado, sin reiniciar contenedores)
# Ver ../../docs/acceso-temporal-api-pruebas.md

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

Usuario: `admin_a@test.local`. Periodo: `2026-01-01` a `2026-01-31`.

---

## 10. Enlaces relacionados

- [README del equipo](../../README.md)
- [README técnico del dashboard](../../dashboard/README.md)
- [Guion de exposición](../../docs/unidad3_actividad1/guion_exposicion.md)
- [Procedimiento de la API temporal](../../docs/acceso-temporal-api-pruebas.md)
- [Estado de Git](resultados/git_publicacion.txt)
