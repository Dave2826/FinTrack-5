import { ApolloLink } from '@apollo/client'
import { tokenStore } from '../auth/tokenStore'

/**
 * Link de Apollo que inyecta el token en cada petición.
 *
 * El token se lee en el momento de la operación, nunca se congela en la
 * configuración del cliente. Si no hay token, la petición viaja sin la
 * cabecera `Authorization`.
 */

export type TokenReader = () => string | null

interface HeadersContext {
  headers?: Record<string, string>
}

export function createAuthLink(
  getToken: TokenReader = () => tokenStore.get(),
): ApolloLink {
  return new ApolloLink((operation, forward) => {
    const token = getToken()

    if (token) {
      operation.setContext(({ headers = {} }: HeadersContext) => ({
        headers: {
          ...headers,
          authorization: `Bearer ${token}`,
        },
      }))
    }

    return forward(operation)
  })
}

export const authLink = createAuthLink()
