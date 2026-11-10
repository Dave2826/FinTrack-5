/**
 * Lectura del payload de un JWT.
 *
 * IMPORTANTE: esta lectura es solo para controlar la interfaz (por ejemplo,
 * programar el cierre de sesión cuando vence `exp`). No verifica la firma ni
 * sustituye la validación que hace el backend.
 */

export interface JwtPayload {
  exp?: number
  companyId?: number
  companyUserId?: number
  [claim: string]: unknown
}

const BASE64URL_PATTERN = /^[A-Za-z0-9_-]+$/

function decodeBase64Url(segment: string): string | null {
  if (!BASE64URL_PATTERN.test(segment)) {
    return null
  }

  const normalized = segment.replace(/-/g, '+').replace(/_/g, '/')
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=')

  try {
    return atob(padded)
  } catch {
    return null
  }
}

export function decodeJwtPayload(token: string): JwtPayload | null {
  const parts = token.split('.')

  if (parts.length !== 3) {
    return null
  }

  const json = decodeBase64Url(parts[1])

  if (json === null) {
    return null
  }

  try {
    const parsed: unknown = JSON.parse(json)

    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      return null
    }

    return parsed as JwtPayload
  } catch {
    return null
  }
}

/** Devuelve la expiración en milisegundos, o `null` si no puede leerse. */
export function getTokenExpirationMs(token: string): number | null {
  const payload = decodeJwtPayload(token)
  const exp = payload?.exp

  if (typeof exp !== 'number' || !Number.isFinite(exp)) {
    return null
  }

  return exp * 1000
}

/**
 * Un token sin `exp` legible se considera no utilizable para la interfaz
 * (el backend siempre emite `exp`). El backend sigue siendo la autoridad.
 */
export function isTokenExpired(token: string, now: number = Date.now()): boolean {
  const expiresAt = getTokenExpirationMs(token)

  if (expiresAt === null) {
    return true
  }

  return expiresAt <= now
}
