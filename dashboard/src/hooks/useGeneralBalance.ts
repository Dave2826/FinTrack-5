import { useQuery } from '@apollo/client'
import { useCallback, useEffect, useMemo, useRef } from 'react'
import { GENERAL_BALANCE_QUERY } from '../api/operations/generalBalance'
import { useAuth } from '../auth/useAuth'
import { toBalanceError } from '../lib/balanceErrors'
import type { BalanceError } from '../lib/balanceErrors'
import { validateDateRange } from '../lib/dateRange'
import type { DateRange, DateRangeValidation } from '../lib/dateRange'
import type {
  GeneralBalance,
  GeneralBalanceResult,
  GeneralBalanceVariables,
} from '../types/balance'

export type InvalidDateRange = Extract<DateRangeValidation, { ok: false }>

export interface UseGeneralBalanceResult {
  /** Balance devuelto por el backend, o `null` si aún no hay datos. */
  balance: GeneralBalance | null
  /** Carga inicial de la consulta. */
  loading: boolean
  /** Actualización o refetch mientras se conservan los datos previos. */
  isRefetching: boolean
  /** Error normalizado, listo para que la interfaz elija el mensaje. */
  error: BalanceError | null
  /** Repite la consulta con el rango actual. No hace nada si está omitida. */
  refetch: () => Promise<void>
  /** Indica si el rango recibido pasó la validación local. */
  isRangeValid: boolean
  /** Motivo y mensaje cuando el rango no es válido. */
  rangeError: InvalidDateRange | null
}

/**
 * Consulta el balance general de la empresa autenticada.
 *
 * La empresa la determina el backend a partir del token que inyecta
 * `authLink`; el hook nunca envía `companyId` ni gestiona la autenticación.
 * La consulta se omite si no hay sesión o si el rango de fechas no es válido.
 *
 * Se usa `network-only` porque un dashboard financiero no debe mostrar datos
 * de una sesión o empresa anterior: el cierre de sesión ya limpia la caché y
 * esta política evita reutilizarla incluso si el cambio de sesión ocurriera
 * por otra vía.
 */
export function useGeneralBalance(range: DateRange): UseGeneralBalanceResult {
  const { status, logout } = useAuth()
  const { fromDate, toDate } = range

  const validation = useMemo(
    () => validateDateRange(fromDate, toDate),
    [fromDate, toDate],
  )

  const variables = useMemo<GeneralBalanceVariables | undefined>(() => {
    if (!validation.ok) {
      return undefined
    }

    return {
      fromDate: validation.range.fromDate,
      toDate: validation.range.toDate,
    }
  }, [validation])

  const enabled = status === 'authenticated' && validation.ok

  const { data, loading, error, refetch } = useQuery<
    GeneralBalanceResult,
    GeneralBalanceVariables
  >(GENERAL_BALANCE_QUERY, {
    variables,
    skip: !enabled,
    fetchPolicy: 'network-only',
    notifyOnNetworkStatusChange: true,
  })

  const refetchBalance = useCallback(async () => {
    if (!enabled) {
      return
    }

    await refetch()
  }, [enabled, refetch])

  const balanceError = useMemo(
    () => (error ? toBalanceError(error) : null),
    [error],
  )

  // Un rechazo de autenticación invalida la sesión completa, no solo la
  // consulta. Se cierra sesión una sola vez para evitar ciclos de logout.
  const sessionInvalid =
    balanceError?.kind === 'expired' ||
    balanceError?.kind === 'unauthenticated'
  const logoutRequested = useRef(false)

  useEffect(() => {
    // El guard se reinicia solo al terminar la sesión autenticada, no
    // cuando el error desaparece de forma transitoria durante un refetch.
    if (status !== 'authenticated') {
      logoutRequested.current = false
      return
    }

    if (!sessionInvalid || logoutRequested.current) {
      return
    }

    logoutRequested.current = true
    void logout('expired')
  }, [sessionInvalid, status, logout])

  return {
    // Nunca se conservan importes de una sesión rechazada, ni siquiera
    // durante el render previo a que `logout` cambie el estado global.
    balance: sessionInvalid ? null : (data?.generalBalance ?? null),
    loading,
    isRefetching: loading && data !== undefined,
    error: balanceError,
    refetch: refetchBalance,
    isRangeValid: validation.ok,
    rangeError: validation.ok ? null : validation,
  }
}
