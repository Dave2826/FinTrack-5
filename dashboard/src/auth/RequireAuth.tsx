import type { ReactNode } from 'react'
import { LoginPage } from '../features/login/LoginPage'
import { useAuth } from './useAuth'

interface RequireAuthProps {
  children: ReactNode
  /** Contenido alternativo cuando no hay sesión válida. */
  fallback?: ReactNode
}

/**
 * Protege el contenido privado. Sin sesión válida se muestra el login.
 *
 * Esto es solo control de interfaz: la autorización real la aplica el
 * backend en cada consulta o mutación.
 */
export function RequireAuth({ children, fallback }: RequireAuthProps) {
  const { status } = useAuth()

  if (status !== 'authenticated') {
    return <>{fallback ?? <LoginPage />}</>
  }

  return <>{children}</>
}
