/**
 * URL relativa del endpoint GraphQL.
 *
 * En desarrollo, Vite reenvía `/graphql` a `http://localhost:8001/graphql`
 * mediante el proxy configurado en `vite.config.ts`.
 */
export const GRAPHQL_URL = import.meta.env.VITE_GRAPHQL_URL ?? '/graphql'
