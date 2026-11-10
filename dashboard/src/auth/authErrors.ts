import { ApolloError } from '@apollo/client'
import type { GraphQLFormattedError } from 'graphql'

/**
 * Errores de autenticación normalizados para la interfaz.
 *
 * Se distinguen credenciales incorrectas, problemas de conexión, errores
 * GraphQL genéricos, token expirado y ausencia de sesión. Nunca se muestran
 * tokens, contraseñas ni detalles internos del backend.
 */

export type AuthErrorKind =
  | 'invalid-credentials'
  | 'network'
  | 'graphql'
  | 'expired'
  | 'missing-session'
  | 'invalid-response'

export class AuthError extends Error {
  readonly kind: AuthErrorKind

  constructor(kind: AuthErrorKind, message: string) {
    super(message)
    this.name = 'AuthError'
    this.kind = kind
  }
}

const CREDENTIAL_PATTERNS = [
  /credenciales\s+inv[aá]lidas/i,
  /invalid\s+credentials/i,
  /correo\s+o\s+contrase[nñ]a/i,
]

const EXPIRED_PATTERNS = [
  /token\s+inv[aá]lido\s+o\s+expirado/i,
  /usuario\s+no\s+autenticado/i,
  /membres[ií]a\s+no\s+existe\s+o\s+est[aá]\s+inactiva/i,
  /token\s+no\s+corresponde/i,
  /jwt\s+expired/i,
  /token\s+expired/i,
]

const EXPIRED_CODES = new Set(['UNAUTHENTICATED', 'TOKEN_EXPIRED'])

function readCodes(errors: readonly GraphQLFormattedError[]): string[] {
  return errors.flatMap((error) => {
    const code = error.extensions?.code
    return typeof code === 'string' ? [code] : []
  })
}

export function classifyGraphQLErrors(
  errors: readonly GraphQLFormattedError[],
): AuthErrorKind {
  if (readCodes(errors).some((code) => EXPIRED_CODES.has(code))) {
    return 'expired'
  }

  const messages = errors.map((error) => error.message).join(' | ')

  if (CREDENTIAL_PATTERNS.some((pattern) => pattern.test(messages))) {
    return 'invalid-credentials'
  }

  if (EXPIRED_PATTERNS.some((pattern) => pattern.test(messages))) {
    return 'expired'
  }

  return 'graphql'
}

function fromGraphQLErrors(
  errors: readonly GraphQLFormattedError[],
): AuthError {
  const kind = classifyGraphQLErrors(errors)

  if (kind === 'invalid-credentials') {
    return new AuthError(
      'invalid-credentials',
      'El correo o la contraseña no son correctos.',
    )
  }

  if (kind === 'expired') {
    return new AuthError('expired', 'La sesión expiró o el token no es válido.')
  }

  return new AuthError(
    'graphql',
    'El servidor rechazó la solicitud de autenticación.',
  )
}

export function toAuthError(error: unknown): AuthError {
  if (error instanceof AuthError) {
    return error
  }

  if (error instanceof ApolloError) {
    if (error.networkError) {
      return new AuthError(
        'network',
        'No fue posible conectar con el servidor.',
      )
    }

    if (error.graphQLErrors.length > 0) {
      return fromGraphQLErrors(error.graphQLErrors)
    }
  }

  // Compatibilidad con errores equivalentes creados en otro contexto.
  if (typeof error === 'object' && error !== null) {
    const candidate = error as {
      networkError?: unknown
      graphQLErrors?: readonly GraphQLFormattedError[]
    }

    if (candidate.networkError) {
      return new AuthError(
        'network',
        'No fue posible conectar con el servidor.',
      )
    }

    if (candidate.graphQLErrors && candidate.graphQLErrors.length > 0) {
      return fromGraphQLErrors(candidate.graphQLErrors)
    }
  }

  return new AuthError(
    'graphql',
    'No fue posible completar la autenticación.',
  )
}

/** Mensaje apto para mostrarse en la interfaz, sin datos sensibles. */
export function messageForAuthError(error: AuthError): string {
  switch (error.kind) {
    case 'invalid-credentials':
      return 'El correo o la contraseña no son correctos. Verifica tus datos e inténtalo de nuevo.'
    case 'network':
      return 'No se pudo conectar con el servidor. Revisa tu conexión e inténtalo de nuevo.'
    case 'expired':
      return 'Tu sesión expiró. Inicia sesión de nuevo para continuar.'
    case 'missing-session':
      return 'No hay una sesión activa. Inicia sesión para continuar.'
    case 'invalid-response':
      return 'El servidor devolvió una respuesta inesperada. Inténtalo de nuevo.'
    case 'graphql':
    default:
      return 'No fue posible iniciar sesión en este momento. Inténtalo de nuevo en unos momentos.'
  }
}
