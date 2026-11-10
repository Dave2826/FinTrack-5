import { ApolloError } from '@apollo/client'
import type { GraphQLFormattedError } from 'graphql'

/**
 * Interpretación centralizada de los errores de la consulta `generalBalance`.
 *
 * Traduce los errores de Apollo/GraphQL a categorías estables para que la
 * interfaz decida qué mostrar sin acoplarse a los mensajes del backend. Los
 * mensajes públicos nunca incluyen tokens ni detalles internos; el detalle
 * técnico se conserva aparte para diagnóstico.
 */

export type BalanceErrorKind =
  | 'network'
  | 'unauthenticated'
  | 'expired'
  | 'forbidden'
  | 'invalid-dates'
  | 'graphql'

const EXPIRED_PATTERNS = [
  /token\s+inv[aá]lido\s+o\s+expirado/i,
  /\bjwt\s+expired\b/i,
  /\btoken\s+expired\b/i,
]

const UNAUTHENTICATED_PATTERNS = [
  /usuario\s+no\s+autenticado/i,
  /\bno\s+hay\s+sesi[oó]n\b/i,
]

const FORBIDDEN_PATTERNS = [
  /no\s+tiene\s+el\s+permiso/i,
  /no\s+tiene\s+un\s+rol\s+activo/i,
  /\bpermission\s+denied\b/i,
  /\bforbidden\b/i,
  /\bno\s+autorizado\b/i,
]

const DATE_PATTERNS = [
  /\bfromdate\b/i,
  /\btodate\b/i,
  /\bfecha(s)?\b/i,
  /\bdate\b/i,
  /day\s+is\s+out\s+of\s+range/i,
  /invalid\s+value.*\bdate\b/i,
]

const EXPIRED_CODES = new Set(['TOKEN_EXPIRED'])
const UNAUTHENTICATED_CODES = new Set(['UNAUTHENTICATED'])
const FORBIDDEN_CODES = new Set(['FORBIDDEN', 'PERMISSION_DENIED'])

const MESSAGES: Record<BalanceErrorKind, string> = {
  network:
    'No fue posible conectar con el servidor. Revisa tu conexión e inténtalo de nuevo.',
  unauthenticated:
    'No hay una sesión activa. Inicia sesión para consultar el balance.',
  expired:
    'Tu sesión expiró o el token no es válido. Inicia sesión de nuevo.',
  forbidden:
    'No tienes permisos para consultar el balance de esta empresa.',
  'invalid-dates':
    'El periodo seleccionado no es válido. Revisa las fechas e inténtalo de nuevo.',
  graphql:
    'No fue posible consultar el balance en este momento. Inténtalo de nuevo.',
}

export class BalanceError extends Error {
  readonly kind: BalanceErrorKind

  /**
   * Detalle técnico para diagnóstico. Puede contener mensajes del backend,
   * por lo que no debe mostrarse directamente en la interfaz.
   */
  readonly technicalMessage: string

  constructor(
    kind: BalanceErrorKind,
    message: string,
    technicalMessage: string,
  ) {
    super(message)
    this.name = 'BalanceError'
    this.kind = kind
    this.technicalMessage = technicalMessage
  }
}

function matches(patterns: readonly RegExp[], text: string): boolean {
  return patterns.some((pattern) => pattern.test(text))
}

function readCodes(errors: readonly GraphQLFormattedError[]): string[] {
  return errors.flatMap((error) => {
    const code = error.extensions?.code
    return typeof code === 'string' ? [code] : []
  })
}

/**
 * Clasifica un conjunto de errores GraphQL según el contrato del backend.
 *
 * El orden importa: un token expirado también puede llegar como
 * `UNAUTHENTICATED`, por lo que se comprueba antes que la sesión ausente.
 */
export function classifyGraphQLErrors(
  errors: readonly GraphQLFormattedError[],
): BalanceErrorKind {
  const codes = readCodes(errors)
  const messages = errors.map((error) => error.message).join(' | ')

  if (
    codes.some((code) => EXPIRED_CODES.has(code)) ||
    matches(EXPIRED_PATTERNS, messages)
  ) {
    return 'expired'
  }

  if (
    codes.some((code) => UNAUTHENTICATED_CODES.has(code)) ||
    matches(UNAUTHENTICATED_PATTERNS, messages)
  ) {
    return 'unauthenticated'
  }

  if (
    codes.some((code) => FORBIDDEN_CODES.has(code)) ||
    matches(FORBIDDEN_PATTERNS, messages)
  ) {
    return 'forbidden'
  }

  if (matches(DATE_PATTERNS, messages)) {
    return 'invalid-dates'
  }

  return 'graphql'
}

function fromGraphQLErrors(
  errors: readonly GraphQLFormattedError[],
): BalanceError {
  const kind = classifyGraphQLErrors(errors)
  const technicalMessage = [
    ...readCodes(errors),
    ...errors.map((error) => error.message),
  ].join(' | ')

  return new BalanceError(kind, MESSAGES[kind], technicalMessage)
}

/**
 * Normaliza cualquier error de la consulta a un `BalanceError`.
 *
 * No modifica la sesión: clasificar un error de permisos o de red nunca
 * provoca un cierre de sesión por sí mismo.
 */
export function toBalanceError(error: unknown): BalanceError {
  if (error instanceof BalanceError) {
    return error
  }

  if (error instanceof ApolloError) {
    if (error.networkError) {
      return new BalanceError(
        'network',
        MESSAGES.network,
        error.networkError.message,
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
      const technicalMessage =
        candidate.networkError instanceof Error
          ? candidate.networkError.message
          : 'Error de red'

      return new BalanceError('network', MESSAGES.network, technicalMessage)
    }

    if (candidate.graphQLErrors && candidate.graphQLErrors.length > 0) {
      return fromGraphQLErrors(candidate.graphQLErrors)
    }
  }

  const technicalMessage =
    error instanceof Error ? error.message : String(error)

  return new BalanceError('graphql', MESSAGES.graphql, technicalMessage)
}
