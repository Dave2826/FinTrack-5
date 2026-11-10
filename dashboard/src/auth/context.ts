import { createContext } from 'react'
import type { AuthUser, LoginInput } from '../types/auth'

/**
 * Contexto y tipos de autenticación.
 *
 * Se mantienen en un archivo sin componentes para que `AuthContext.tsx` solo
 * exporte el proveedor y Fast Refresh siga funcionando.
 */

export type SessionStatus = 'anonymous' | 'authenticated'
export type SessionEndReason = 'manual' | 'expired' | null

export interface AuthContextValue {
  status: SessionStatus
  user: AuthUser | null
  expiresAt: number | null
  sessionEndReason: SessionEndReason
  login: (input: LoginInput) => Promise<void>
  logout: (reason?: 'manual' | 'expired') => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)
