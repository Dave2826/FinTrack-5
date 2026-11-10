import { useQuery } from '@apollo/client'
import { useCallback, useMemo } from 'react'
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
  const { status } = useAuth()
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

  return {
    balance: data?.generalBalance ?? null,
    loading,
    isRefetching: loading && data !== undefined,
    error: error ? toBalanceError(error) : null,
    refetch: refetchBalance,
    isRangeValid: validation.ok,
    rangeError: validation.ok ? null : validation,
  }
}
