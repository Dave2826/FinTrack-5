import { ApolloClient, HttpLink, InMemoryCache, from } from '@apollo/client'
import type { NormalizedCacheObject } from '@apollo/client'
import { authLink } from './authLink'
import { GRAPHQL_URL } from './config'

/**
 * Cliente Apollo 3.x del dashboard.
 *
 * - La URL es relativa (`/graphql`); Vite la reenvía al backend de pruebas.
 * - `authLink` añade el token en memoria a cada operación.
 * - No se guarda el token dentro del cliente.
 */
export function createApolloClient(): ApolloClient<NormalizedCacheObject> {
  return new ApolloClient({
    link: from([authLink, new HttpLink({ uri: GRAPHQL_URL })]),
    cache: new InMemoryCache(),
    defaultOptions: {
      watchQuery: {
        fetchPolicy: 'cache-and-network',
        notifyOnNetworkStatusChange: true,
      },
      query: {
        fetchPolicy: 'network-only',
      },
    },
  })
}

export const apolloClient = createApolloClient()
