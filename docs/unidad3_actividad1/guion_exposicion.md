# Guion de exposición — Unidad III, Actividad 1

**Proyecto:** FinTrack-5 · Dashboard financiero
**Equipo:** David Morales · Edwuard Chay · Fabrizio Rodriguez
**Duración objetivo:** 9 min 30 s + preguntas
**Modalidad:** demostración en vivo con el frontend y la API reales; capturas y JSON como respaldo.

> La distribución de tiempos es una asignación **de exposición**. No atribuye autoría individual del código: el repositorio no registra qué persona escribió cada archivo y este documento no inventa esa información.

---

## Antes de empezar (checklist del equipo)

| Elemento | Verificación |
|---|---|
| Backend de pruebas | `http://127.0.0.1:8001/graphql` responde. Procedimiento: [`../acceso-temporal-api-pruebas.md`](../acceso-temporal-api-pruebas.md). |
| Frontend | `cd dashboard && npm run dev`; abrir `http://localhost:5173`. |
| Usuario | `admin_a@test.local` (Admin Pruebas Alpha, empresa #11). |
| Contraseña | Se obtiene del mecanismo local de pruebas (`scripts/setup_pruebas.py`, constante `CONTRASENA_PRUEBAS`). **No se escribe, dicta ni muestra en pantalla.** |
| Periodo | `2026-01-01` a `2026-01-31`. El valor por defecto es el mes UTC actual y muestra importes en cero; hay que cambiarlo. |
| Respaldo | `evidencias/unidad3_actividad1_dashboard/capturas/` y `evidencias/unidad3_actividad1_dashboard/resultados/general_balance_enero_2026.json`. |
| Pestañas | Una con el dashboard y otra con este guion; no abrir DevTools con el token visible. |

**Valores reales esperados para enero de 2026** (verificados contra la API de pruebas):

| Indicador | Valor |
|---|---:|
| Saldo inicial | `$0.00` |
| Ingresos | `$1,500.00` |
| Egresos | `$300.00` |
| Utilidad | `$1,200.00` |
| Saldo final | `$1,200.00` |
| Cuentas | 5 |
| Cuentas en rojo | 0 |
| Indicador global | «Sin riesgo global» · «0 cuentas en números rojos» |

---

## David Morales — 0:00 a 3:00

### 0:00–1:10 · Contexto y objetivo

**Qué decir:**

> «FinTrack-5 es un sistema de gestión financiera: empresas, usuarios, cuentas, conceptos y movimientos, expuestos mediante GraphQL. En las actividades anteriores el backend ya calculaba balances por cuenta y el balance general. El problema era que esos resultados solo se veían como respuestas JSON. Esta actividad agrega el dashboard: una sola pantalla donde la empresa elige un periodo y ve cuánto había, cuánto entró, cuánto salió, cuánto queda y si hay cuentas en números rojos.»

**Qué mostrar:**

- `README.md`, secciones «Descripción», «Arquitectura» y «Dashboard financiero — Unidad III».
- La estructura del repositorio: `graphql_api/`, `services/`, `repositories/`, `models/`, `dashboard/`.

**Qué ejecutar:** nada todavía; solo recorrer la estructura.

### 1:10–2:00 · Arquitectura y rol del frontend

**Qué decir:**

> «La arquitectura es GraphQL → Services → Repositories → SQLAlchemy → PostgreSQL. El dashboard no calcula nada: envía `fromDate` y `toDate`, y el backend devuelve los cinco indicadores y el detalle por cuenta. El cliente solo formatea los importes en MXN. El frontend es Vite + React + TypeScript con Apollo Client, y la autorización real vive en GraphQL; proteger rutas en React no sustituye la validación del servidor.»

**Qué mostrar:** el diagrama del README y `dashboard/src/features/dashboard/`.

### 2:00–3:00 · Autenticación JWT

**Qué decir:**

> «El login usa la mutación `login`. El backend responde un JWT firmado con HS256 y vigencia de 30 minutos. El token se guarda únicamente en memoria: no va a `localStorage`, `sessionStorage` ni cookies. Un `authLink` de Apollo añade `Authorization: Bearer` en cada operación. Al recargar la página la sesión termina, y cuando el token vence la aplicación vuelve al login.»

**Qué mostrar:** `dashboard/src/auth/tokenStore.ts`, `dashboard/src/api/authLink.ts` y `dashboard/src/auth/AuthContext.tsx`.

**Qué ejecutar:** abrir `http://localhost:5173` y mostrar la pantalla de login, sin escribir credenciales todavía.

**Resultado esperado:** formulario de acceso con la nota «La sesión se mantiene solo en esta pestaña y se cierra al recargar la página».

**Transición:** «Edwuard va a iniciar sesión y a consultar el balance.»

---

## Edwuard Chay — 3:00 a 6:30

### 3:00–3:40 · Inicio de sesión real

**Qué decir:**

> «Inicio sesión con el usuario de prueba `admin_a@test.local`. La contraseña proviene del entorno local de pruebas y no se comparte. Al entrar, el encabezado muestra la empresa y la vigencia de la sesión.»

**Qué ejecutar:** escribir el correo, la contraseña (sin mostrarla) y pulsar «Entrar».

**Resultado esperado:** encabezado «AUTENTICACIÓN CORRECTA», «Admin Pruebas Alpha», «Empresa #11» y «Sesión válida hasta …». El dashboard carga el mes UTC actual.

### 3:40–5:00 · Consulta `generalBalance` y filtro de fechas

**Qué decir:**

> «El dashboard consulta `generalBalance(fromDate, toDate)`. La empresa no se envía: se deriva del token. Las fechas se interpretan como días completos UTC. El periodo por defecto es el mes actual, que no tiene movimientos; para la demostración uso enero de 2026.»

**Qué ejecutar:**

1. En «Fecha inicial» escribir `01/01/2026`.
2. En «Fecha final» escribir `31/01/2026`.
3. Pulsar «Consultar».

**Resultado esperado:** «Periodo consultado: 2026-01-01 a 2026-01-31 (UTC)» y los indicadores `$0.00`, `$1,500.00`, `$300.00`, `$1,200.00`, `$1,200.00`.

**Qué mostrar:** `dashboard/src/api/operations/generalBalance.ts` y `dashboard/src/hooks/useGeneralBalance.ts` si preguntan por la consulta.

### 5:00–5:45 · Indicadores y riesgo

**Qué decir:**

> «Los cinco indicadores los calcula el backend: saldo inicial, ingresos, egresos, utilidad y saldo final. El frontend no suma ni resta; solo aplica formato MXN. El tono de la utilidad depende del signo y el del saldo final depende de `isInRed`. Debajo de las cinco tarjetas, el indicador global usa directamente `isInRed` y `accountsInRed`: si `isInRed` es falso muestra “Sin riesgo global” y, si es verdadero, “Riesgo financiero global”. Siempre muestra el conteo exacto, por ejemplo “0 cuentas en números rojos” o “1 cuenta en números rojos”. El caso `isInRed = false` con `accountsInRed > 0` es válido: se presenta como riesgo individual, sin contradecir el estado global. El cliente no recalcula ninguno de los dos campos.»

**Qué mostrar:** las cinco tarjetas del resumen, el bloque global «Sin riesgo global · 0 cuentas en números rojos» y la insignia «Sin riesgo» de cada fila. Si se pregunta por el escenario de riesgo, mostrar la captura 09 y aclarar que es una simulación de prueba, no un dato real.

### 5:45–6:30 · Manejo de errores reales

**Qué decir:**

> «La validación de fechas ocurre antes de llamar al backend. Si la fecha inicial es posterior a la final, el formulario muestra un error, marca ambos campos y mueve el foco al primero. También manejamos credenciales incorrectas con un mensaje claro del servidor.»

**Qué ejecutar:**

1. Cambiar la fecha inicial a `10/02/2026` y la final a `01/02/2026`; pulsar «Consultar».
2. Mostrar el mensaje «La fecha inicial no puede ser posterior a la fecha final.» y el foco en «Fecha inicial».
3. Cerrar sesión, escribir una contraseña incorrecta y pulsar «Entrar».

**Resultado esperado:** alerta de rango invertido con `role="alert"`; alerta de login «El correo o la contraseña no son correctos. Verifica tus datos e inténtalo de nuevo.» con la contraseña enmascarada.

**Transición:** «Fabrizio revisa el detalle por cuenta y el resto de la interfaz.»

---

## Fabrizio Rodriguez — 6:30 a 9:30

### 6:30–7:30 · Detalle de cuentas

**Qué decir:**

> «El detalle muestra las cinco cuentas de la empresa. Por cada una: nombre, estado de actividad, estado de riesgo y los cinco importes. La información viene tal cual del backend; no se recalculan saldos. Las cuentas sin movimientos aparecen en cero, no se ocultan.»

**Qué ejecutar:** iniciar sesión de nuevo, aplicar enero de 2026 y desplazarse a «Detalle de cuentas».

**Resultado esperado:** «Cuenta Alpha Pruebas» con `$1,500.00` de ingresos, `$300.00` de egresos y `$1,200.00` de saldo final; cuatro cuentas en cero; todas «Activa» y «Sin riesgo».

### 7:30–8:15 · Estados, accesibilidad y responsive

**Qué decir:**

> «La interfaz cubre carga inicial, actualización, error y vacío. Los mensajes de estado usan `role="status"`; los errores usan `role="alert"`. El indicador global es una región con nombre accesible, encabezado propio y texto explícito: no depende solo del color. La tabla conserva `caption`, encabezados con `scope` y roles ARIA aunque el CSS la convierta en tarjetas. Por debajo de 900 px la tabla pasa a tarjetas, a 760 px el workspace queda en una columna y a 480 px se apilan encabezado, filtros y el indicador global. Los objetivos táctiles miden al menos 44 px y el foco es visible.»

**Qué ejecutar:** abrir las herramientas de desarrollo y activar el modo responsive a `375 × 812`. Desplazarse para mostrar el indicador global y la tabla como tarjetas. Cerrar las herramientas antes de continuar.

**Resultado esperado:** sin desplazamiento horizontal; encabezado apilado; indicador global en una columna; cada cuenta como tarjeta con sus etiquetas.

**Evidencia de respaldo:** `06_dashboard_movil_375x812.png` (encabezado apilado), `08_indicador_global_movil_375x812.png` (indicador global en móvil) y `07_dashboard_movil_cuentas_375x812.png` (cuentas como tarjetas).

### 8:15–9:00 · Validaciones técnicas

**Qué decir:**

> «La calidad se valida con cuatro comandos: `npm run lint`, `npm run typecheck`, `npm test` y `npm run build`. La suite cubre autenticación, sesión, errores, consulta del balance, fechas, formato, tabla, estados, indicador global de riesgo, accesibilidad, responsive y foco. Son 14 archivos y 134 pruebas aprobadas. Los resultados están guardados en `evidencias/unidad3_actividad1_dashboard/resultados/`.»

**Qué mostrar:** `resultados/test.txt`, `resultados/lint.txt`, `resultados/typecheck.txt` y `resultados/build.txt`.

**Resultado esperado:** lint sin errores, typecheck sin errores, 134/134 pruebas aprobadas y build de producción correcto. Los conteos exactos se leen del archivo, no se improvisan.

### 9:00–9:30 · Cierre

**Qué decir:**

> «El dashboard queda integrado con el backend real: autenticación JWT en memoria, consulta de balance por periodo, cinco indicadores, indicador global de riesgo con `isInRed` y `accountsInRed`, detalle por cuenta, estados de interfaz, accesibilidad y diseño responsive. La documentación, las capturas, el JSON real y este guion están en el ZIP de entrega. ¿Preguntas?»

**Qué mostrar:** el dashboard con enero de 2026 y el `README.md` con los enlaces a evidencias.

---

## Plan alternativo si falla el entorno

| Falla | Acción | Qué decir |
|---|---|---|
| La API en `8001` no responde | No reiniciar contenedores. Seguir `docs/acceso-temporal-api-pruebas.md`. Si no se recupera, usar las capturas. | «La API de pruebas no está disponible en este momento; muestro las evidencias tomadas contra la API real.» |
| Vite no arranca | Usar las capturas de `capturas/`. | «El frontend no está disponible; estas son las capturas reales de la misma versión.» |
| El login falla por credenciales | Verificar el mecanismo local de pruebas; no dictar la contraseña. | «Uso el usuario de prueba documentado; la contraseña no se comparte.» |
| El periodo no muestra movimientos | Confirmar que se aplicó `2026-01-01` a `2026-01-31`. | «El periodo por defecto es el mes actual; lo cambio a enero de 2026.» |
| Una consulta tarda | Esperar el estado «Actualizando balance». | «La interfaz conserva los datos anteriores mientras actualiza.» |
| Se pregunta por el escenario de riesgo | Mostrar `09_simulacion_riesgo_1440x900.png`. | «Esta captura es una simulación de prueba con datos mock; el entorno real solo tiene `isInRed = false` y `accountsInRed = 0`.» |

**Regla del plan B:** las capturas y el JSON se presentan como **evidencias ya tomadas**, nunca como una demostración en vivo. No se inventan valores ni se modifican datos para forzar un resultado. La única captura simulada es la 09 y está etiquetada como tal en la imagen y en `evidencias.md`.

---

## Preguntas previsibles

| Pregunta | Respuesta breve |
|---|---|
| ¿Dónde se guarda el token? | Solo en memoria (`tokenStore`); se pierde al recargar. |
| ¿El frontend valida permisos? | No como autoridad. GraphQL exige el permiso en cada operación. |
| ¿Por qué enero de 2026? | Es el periodo con movimientos reales en la base de pruebas. |
| ¿Hay cuentas en rojo? | No en los datos reales (`accountsInRed = 0`). El caso está cubierto por pruebas automatizadas. |
| ¿Cómo se calcula el riesgo global? | No se calcula en el cliente: se muestran directamente `isInRed` y `accountsInRed` que devuelve `generalBalance`. |
| ¿Qué pasa si `isInRed = false` y `accountsInRed > 0`? | Es un caso válido. Se muestra «Sin riesgo global» y el conteo exacto de cuentas individuales en rojo, con una nota que explica la diferencia. |
| ¿La captura de riesgo es un dato real? | No. La captura 09 es una simulación de prueba con respuesta mock interceptada y lleva un aviso visible; los datos reales solo tienen `isInRed = false` y `accountsInRed = 0`. |
| ¿El cliente suma los importes? | No. Los cinco valores y los saldos llegan calculados del backend. |
| ¿Qué pasa si la fecha inicial es mayor? | Validación local, mensaje accesible y foco en el campo. |
| ¿Funciona en móvil? | Sí; tabla en tarjetas por debajo de 900 px y encabezado apilado a 480 px. |
