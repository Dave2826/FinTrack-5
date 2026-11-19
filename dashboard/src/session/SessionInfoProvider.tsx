import { useQuery } from '@apollo/client'
import { useCallback, useEffect, useMemo, useRef } from 'react'
import type { ReactNode } from 'react'
import { ME_QUERY } from '../api/operations/session'
import { decodeJwtPayload } from '../auth/jwt'
import { tokenStore } from '../auth/tokenStore'
import { useAuth } from '../auth/useAuth'
import { readApiError } from '../lib/apiErrors'
import type { MeResult } from '../types/admin'
import { SessionInfoContext } from './context'
import type { SessionInfoValue } from './context'

function companyIdFromToken(): number | null {
  const token = tokenStore.get()
  const companyId = token ? decodeJwtPayload(token)?.companyId : undefined

  return typeof companyId === 'number' && Number.isFinite(companyId)
    ? companyId
    : null
}

/**
 * Consulta `me` una vez por sesión y comparte empresa, rol y permisos.
 *
 * Si el backend rechaza la sesión se cierra, igual que en el dashboard
 * financiero: no se deja una pantalla a medias.
 */
export function SessionInfoProvider({ children }: { children: ReactNode }) {
  const { status, logout } = useAuth()
  const { data, loading, error } = useQuery<MeResult>(ME_QUERY, {
    skip: status !== 'authenticated',
    fetchPolicy: 'network-only',
  })

  const apiError = error ? readApiError(error) : null
  const logoutRequested = useRef(false)

  useEffect(() => {
    if (status !== 'authenticated') {
      logoutRequested.current = false
      return
    }

    if (apiError?.kind === 'session' && !logoutRequested.current) {
      logoutRequested.current = true
      void logout('expired')
    }
  }, [apiError?.kind, status, logout])

  const info = data?.me ?? null
  const permissions = info?.permissions

  const can = useCallback(
    (permission: string) => permissions?.includes(permission) ?? false,
    [permissions],
  )

  const value = useMemo<SessionInfoValue>(
    () => ({
      info,
      loading,
      error: apiError && apiError.kind !== 'session' ? apiError.message : null,
      companyId: info?.company.id ?? companyIdFromToken(),
      can,
    }),
    [info, loading, apiError, can],
  )

  return (
    <SessionInfoContext.Provider value={value}>
      {children}
    </SessionInfoContext.Provider>
  )
}
