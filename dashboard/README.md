# FinTrack-5 · Dashboard financiero

Frontend del panel financiero de FinTrack-5, construido con **Vite + React + TypeScript + Apollo Client 3.x**.

## Equipo

- David Morales
- Edwuard Chay
- Fabrizio Rodriguez

La asignación de tiempos del guion es de exposición; no atribuye autoría individual del código.

## Estado actual

Subetapas **3.1 a 3.7** completadas:

- Login contra la mutación `login` del backend GraphQL.
- Sesión JWT mantenida únicamente en memoria.
- Consulta del balance general por rango de fechas.
- Resumen de cinco indicadores calculados por el backend.
- Indicador global de riesgo con `isInRed` y `accountsInRed`.
- Tabla de cuentas con estado de actividad y riesgo.
- Estados de carga inicial, actualización, error y vacío.
- Reintento de errores recuperables y gestión de foco.
- Diseño responsive y ajustes de accesibilidad.

El backend sigue siendo la autoridad: la protección de rutas del frontend no
sustituye la autorización de GraphQL.

## Funcionalidad

### Autenticación y sesión

- `src/api/apolloClient.ts`: cliente Apollo con `authLink` + `HttpLink` a `/graphql`.
- `src/api/authLink.ts`: añade `Authorization: Bearer <token>` en cada operación,
  leyendo el token en el momento de la petición.
- `src/auth/tokenStore.ts`: almacén en memoria (`get`, `set`, `clear`, `subscribe`).
  No usa `localStorage`, `sessionStorage`, cookies ni IndexedDB.
- `src/auth/AuthContext.tsx`: ejecuta el login, guarda la sesión, programa el cierre
  por `exp` y limpia el token y la caché de Apollo al salir.
- `src/auth/RequireAuth.tsx`: muestra el login cuando no hay sesión válida.
- `src/auth/jwt.ts`: lee `exp` y `companyId` solo para la interfaz. No valida la firma.
- `src/auth/authErrors.ts`: traduce los errores de autenticación a mensajes
  comprensibles.
- `src/features/login/`: formulario con validación, anuncio accesible de errores,
  foco en el primer campo inválido, estado de carga y errores del servidor.

Al recargar la página la sesión termina porque el token no se persiste.

### Consulta de balance general

- `src/api/operations/generalBalance.ts`: documento GraphQL `generalBalance`.
- `src/hooks/useGeneralBalance.ts`: ejecuta la consulta con `network-only`, conserva
  los datos previos durante una actualización y normaliza los errores.
- La consulta envía únicamente `fromDate` y `toDate`. La empresa se deriva del JWT
  en el backend; el frontend no envía ni acepta `companyId`.
- `src/lib/dateRange.ts`: rango inicial del mes UTC actual y validación local
  (campos obligatorios, formato, rango invertido).
- `src/lib/balanceErrors.ts`: clasificación de errores de sesión, permisos, fechas,
  GraphQL y red.
- `src/lib/format.ts`: formato de importes MXN; no se recalculan saldos ni utilidades.

El periodo se interpreta como días completos UTC: incluye el día `fromDate` y
excluye el día siguiente a `toDate`.

### Resumen e indicadores

`BalanceSummary` presenta los cinco valores que devuelve el backend:

- Saldo inicial.
- Ingresos.
- Egresos.
- Utilidad.
- Saldo final.

Los importes se muestran con `formatMxn`. El tono de la utilidad se deriva del
signo recibido y el del saldo final de `isInRed`; no se hacen operaciones
aritméticas en el cliente.

Debajo de los cinco indicadores, `BalanceSummary` muestra el estado global de
riesgo usando directamente `isInRed` y `accountsInRed`:

- «Sin riesgo global» cuando `isInRed` es falso.
- «Riesgo financiero global» cuando `isInRed` es verdadero.
- «0 cuentas en números rojos», «1 cuenta en números rojos» o «N cuentas en
  números rojos», según `accountsInRed`.

El caso `isInRed = false` con `accountsInRed > 0` es válido y se presenta como
riesgo individual: «Sin riesgo global» junto al conteo de cuentas en rojo. El
bloque es una región con nombre accesible, encabezado propio y texto explícito;
no depende solo del color y se apila en una columna por debajo de 480 px.

### Detalle de cuentas

`AccountsTable` muestra, por cuenta:

- Nombre.
- Estado de actividad (`isActive`).
- Estado de riesgo (`isInRed`).
- Saldo inicial, ingresos, egresos, utilidad y saldo final.

La tabla incluye `caption`, encabezados con `scope` y roles ARIA explícitos para
conservar la semántica cuando el CSS la convierte en tarjetas en pantallas
pequeñas. Si no hay cuentas, se muestra un mensaje de estado vacío.

### Estados de la interfaz

- **Carga inicial:** esqueletos del resumen y mensaje `role="status"`.
- **Actualización:** mensaje `role="status"` y `aria-busy` sin ocultar los datos previos.
- **Error bloqueante:** alerta con mensaje y botón de reintento cuando el error es
  recuperable.
- **Error de actualización:** alerta que conserva los datos del periodo anterior y
  permite reintentar.
- **Vacío:** mensaje cuando todavía no hay balance o cuentas que mostrar.
- **Foco:** al reintentar, el foco se mueve al título del resumen para no perderlo.

## Requisitos

- Node.js 22.12 o superior (probado con Node 24). El rango declarado en
  `engines.node` es `^22.12.0 || ^24.0.0 || >=26.0.0`.
- npm 11 o superior.
- Backend GraphQL de pruebas accesible en `http://localhost:8001/graphql`.
  Consulta `../docs/acceso-temporal-api-pruebas.md` para habilitarlo.

## Instalación

```bash
cd dashboard
npm install
```

## Desarrollo

```bash
npm run dev
```

Abrir <http://localhost:5173>.

Vite reenvía `/graphql` a `http://localhost:8001/graphql` mediante proxy. Por eso
el navegador usa una URL relativa y no se necesita CORS en desarrollo.

## Scripts

| Script | Descripción |
|---|---|
| `npm run dev` | Servidor de desarrollo en el puerto 5173 |
| `npm run build` | Typecheck y build de producción |
| `npm run preview` | Vista previa del build |
| `npm run typecheck` | TypeScript en modo estricto |
| `npm test` | Vitest + React Testing Library |
| `npm run test:watch` | Vitest en modo watch |
| `npm run lint` | Oxlint |

## Configuración

- `VITE_GRAPHQL_URL` es opcional. Si no se define, el cliente usa `/graphql`
  (ver `.env.example`).
- No se requieren secretos en el frontend.
- El token JWT se maneja solo en memoria; al recargar la página la sesión termina.
- El proxy de desarrollo apunta a `http://localhost:8001`; ajústalo en
  `vite.config.ts` si el backend se publica en otro puerto.

## Estructura

```
dashboard/
├── src/
│   ├── api/
│   │   ├── apolloClient.ts       # Apollo Client
│   │   ├── authLink.ts           # Cabecera Bearer dinámica
│   │   ├── config.ts             # URL relativa /graphql
│   │   └── operations/           # login y generalBalance
│   ├── auth/                     # tokenStore, contexto, hook, JWT, errores y RequireAuth
│   ├── components/               # Marca y panel de presentación del login
│   ├── features/
│   │   ├── login/                # Formulario de acceso
│   │   └── dashboard/            # Página, componentes y estilos del panel
│   ├── hooks/                    # useGeneralBalance
│   ├── lib/                      # balanceErrors, dateRange y format
│   ├── styles/                   # Tokens y estilos globales
│   └── types/                    # Tipos del contrato GraphQL
├── tests/                        # Vitest + Testing Library
├── docs/                         # Evidencias y notas
└── vite.config.ts                # Proxy /graphql y configuración de pruebas
```

## Pruebas y validación

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

La suite cubre autenticación, sesión, clasificación de errores, consulta del
balance, validación de fechas, formato, tabla de cuentas, estados de la interfaz,
indicador global de riesgo, accesibilidad, responsive y gestión de foco. Los
escenarios del indicador global incluyen `false/0`, `true/1`, `true/>1`,
`false/1`, singular/plural y la comprobación de que el estado no se comunica solo
por color.

## Accesibilidad y responsive

- Errores de validación anunciados con `role="alert"` y asociados con
  `aria-describedby`; el foco se mueve al primer campo inválido.
- `aria-busy` en los paneles que se actualizan y mensajes de estado fuera de
  esos contenedores.
- Tabla semántica con roles explícitos y vista de tarjetas por debajo de 900 px.
- Objetivos táctiles de al menos 44 px y foco visible.
- Contraste revisado para textos, insignias y estados de riesgo.
- Puntos de quiebre principales: 900 px (tabla a tarjetas), 760 px (workspace a
  una columna) y 480 px (encabezado y filtros apilados).

## Documentación relacionada

- `../docs/acceso-temporal-api-pruebas.md`: proxy temporal hacia la API de pruebas.
- `../docs/unidad3_actividad1/guion_exposicion.md`: guion de la demostración para los tres integrantes.
- `../docs/unidad3_actividad1/boceto_dashboard.svg` y `boceto_dashboard.png`: boceto de la interfaz implementada.
- `../evidencias/unidad3_actividad1_dashboard/evidencias.md`: capturas reales, resultados de validación y limitaciones.
- `docs/README.md`: criterios para guardar evidencias y capturas.
