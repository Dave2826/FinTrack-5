import { useEffect, useRef } from 'react'
import { useAuth } from '../auth/useAuth'
import type { ApiErrorInfo } from '../lib/apiErrors'

/**
 * Si una consulta de administración recibe un rechazo de sesión, se cierra
 * la sesión una sola vez y se vuelve al login (no se deja la tabla a medias).
 */
export function useSessionErrorGuard(error: ApiErrorInfo | null): void {
  const { status, logout } = useAuth()
  const requested = useRef(false)

  useEffect(() => {
    if (status !== 'authenticated') {
      requested.current = false
      return
    }

    if (error?.kind === 'session' && !requested.current) {
      requested.current = true
      void logout('expired')
    }
  }, [error?.kind, status, logout])
}
