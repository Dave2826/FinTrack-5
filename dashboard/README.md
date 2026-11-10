# FinTrack-5 · Dashboard financiero

Frontend del panel financiero de FinTrack-5, construido con **Vite + React + TypeScript + Apollo Client 3.x**.

## Estado

**Etapa 2:** autenticación funcional con la mutación `login` del backend GraphQL.
El token JWT se mantiene únicamente en memoria. El dashboard financiero se
incorpora en la siguiente etapa.

## Autenticación

- `src/api/apolloClient.ts`: cliente Apollo 3.x con `authLink` + `HttpLink` a `/graphql`.
- `src/api/authLink.ts`: añade `Authorization: Bearer <token>` en cada operación,
  leyendo el token en el momento de la petición.
- `src/auth/tokenStore.ts`: almacén en memoria (`get`, `set`, `clear`, `subscribe`).
  No usa `localStorage`, `sessionStorage`, cookies ni IndexedDB.
- `src/auth/context.ts`: contexto de autenticación y tipos de sesión.
- `src/auth/AuthContext.tsx`: proveedor que ejecuta el login, guarda la sesión,
  programa el cierre por `exp` y limpia el token y la caché de Apollo al salir.
- `src/auth/useAuth.ts`: hook para consumir el contexto de autenticación.
- `src/auth/RequireAuth.tsx`: muestra el login cuando no hay sesión válida.
- `src/auth/jwt.ts`: lee `exp` solo para control de interfaz. No valida la firma.
- `src/auth/authErrors.ts`: traduce los errores de autenticación a mensajes
  comprensibles.
- `src/features/login/`: formulario con validación, estado de carga y errores
  comprensibles.
- `src/features/dashboard/DashboardPlaceholder.tsx`: pantalla provisional tras
  autenticarse, con cierre de sesión. El dashboard financiero real corresponde a
  la siguiente etapa.

El backend sigue siendo la autoridad: la protección de rutas del frontend no
sustituye la autorización de GraphQL.

## Requisitos

- Node.js 22.12 o superior (probado con Node 24). El rango declarado en `engines.node` es `^22.12.0 || ^24.0.0 || >=26.0.0`.
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

Vite reenvía `/graphql` a `http://localhost:8001/graphql` mediante proxy. Por eso el navegador usa una URL relativa y no se necesita CORS.

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

- `VITE_GRAPHQL_URL=/graphql` (ver `.env.example`).
- No se requieren secretos en el frontend.
- El token JWT se maneja solo en memoria; al recargar la página la sesión termina.

## Estructura

```
dashboard/
├── src/
│   ├── api/
│   │   ├── apolloClient.ts   # Apollo Client 3.x
│   │   ├── authLink.ts       # Cabecera Bearer dinámica
│   │   ├── config.ts         # URL relativa /graphql
│   │   └── operations/       # Documentos GraphQL (login)
│   ├── auth/                 # tokenStore, contexto, hook, JWT, errores y RequireAuth
│   ├── components/           # Componentes reutilizables
│   ├── features/
│   │   ├── login/            # Formulario de acceso (Etapa 2)
│   │   └── dashboard/        # Placeholder provisional; dashboard real en la siguiente etapa
│   ├── lib/                  # Carpeta reservada; todavía sin utilidades implementadas
│   ├── styles/               # Tokens y estilos globales
│   └── types/                # Tipos del contrato GraphQL
├── tests/                    # Vitest + Testing Library
├── docs/                     # Evidencias y documentación
└── vite.config.ts            # Proxy /graphql y configuración de pruebas
```

## Alcance de esta etapa

- Apollo Client 3.x con token dinámico.
- Login real contra la mutación `login`.
- Sesión en memoria, cierre manual y cierre automático por `exp`.
- Protección de la pantalla provisional.
- Sin consultas `generalBalance`, KPIs ni cuentas todavía.
