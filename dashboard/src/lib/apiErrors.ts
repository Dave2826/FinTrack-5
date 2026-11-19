import { ApolloError } from '@apollo/client'
import type { GraphQLFormattedError } from 'graphql'

/**
 * Lectura de errores del API para las pantallas de administración.
 *
 * Los mensajes de negocio del backend ("Ya existe un usuario con ese
 * correo", "El concepto ya está asignado a esta cuenta", …) están escritos
 * para el usuario y se muestran tal cual. Los errores de red o de sesión se
 * traducen a un texto propio.
 */

export type ApiErrorKind = 'session' | 'forbidden' | 'network' | 'business'

export interface ApiErrorInfo {
  kind: ApiErrorKind
  message: string
}

const SESSION_PATTERNS = [
  /token\s+inv[aá]lido\s+o\s+expirado/i,
  /usuario\s+no\s+autenticado/i,
  /membres[ií]a\s+no\s+existe\s+o\s+est[aá]\s+inactiva/i,
  /token\s+no\s+corresponde/i,
  /usuario\s+no\s+est[aá]\s+activo/i,
]

const FORBIDDEN_PATTERNS = [
  /no\s+tiene\s+el\s+permiso/i,
  /no\s+tiene\s+un\s+rol\s+activo/i,
  /no\s+pertenece\s+a\s+la\s+empresa/i,
]

function fromGraphQL(errors: readonly GraphQLFormattedError[]): ApiErrorInfo {
  const message = errors.map((error) => error.message).join(' · ')

  if (SESSION_PATTERNS.some((pattern) => pattern.test(message))) {
    return {
      kind: 'session',
      message: 'Tu sesión expiró o ya no es válida. Inicia sesión de nuevo.',
    }
  }

  if (FORBIDDEN_PATTERNS.some((pattern) => pattern.test(message))) {
    return {
      kind: 'forbidden',
      message: `Tu rol no permite esta operación. (${message})`,
    }
  }

  return { kind: 'business', message }
}

export function readApiError(error: unknown): ApiErrorInfo {
  if (error instanceof ApolloError) {
    if (error.graphQLErrors.length > 0) {
      return fromGraphQL(error.graphQLErrors)
    }

    if (error.networkError) {
      return {
        kind: 'network',
        message:
          'No fue posible conectar con el servidor. Revisa tu conexión e inténtalo de nuevo.',
      }
    }
  }

  if (typeof error === 'object' && error !== null) {
    const candidate = error as {
      graphQLErrors?: readonly GraphQLFormattedError[]
    }

    if (candidate.graphQLErrors && candidate.graphQLErrors.length > 0) {
      return fromGraphQL(candidate.graphQLErrors)
    }
  }

  return {
    kind: 'network',
    message: 'No fue posible completar la operación. Inténtalo de nuevo.',
  }
}
