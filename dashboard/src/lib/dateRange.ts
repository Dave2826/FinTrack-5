/**
 * Utilidades de fechas del dashboard financiero.
 *
 * Todas las fechas se manejan como días completos UTC en formato
 * `YYYY-MM-DD`, igual que el backend. No se usa `new Date('YYYY-MM-DD')`
 * porque el motor lo interpreta como medianoche UTC y luego puede mostrarse
 * como el día anterior o siguiente según la zona horaria local.
 */

export interface DateRange {
  fromDate: string
  toDate: string
}

export type DateRangeError =
  | 'missing-from'
  | 'missing-to'
  | 'invalid-from'
  | 'invalid-to'
  | 'from-after-to'

export type DateRangeValidation =
  | { ok: true; range: DateRange }
  | { ok: false; reason: DateRangeError; message: string }

const ISO_DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/

function pad(value: number, length = 2): string {
  return String(value).padStart(length, '0')
}

function daysInMonth(year: number, month: number): number {
  if (month === 2) {
    const isLeapYear =
      (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0

    return isLeapYear ? 29 : 28
  }

  return [4, 6, 9, 11].includes(month) ? 30 : 31
}

/**
 * Devuelve el día UTC actual en formato `YYYY-MM-DD`.
 *
 * Usa exclusivamente los getters UTC, por lo que el resultado no depende de
 * la zona horaria local del navegador. El parámetro `now` permite inyectar
 * un reloj controlado en las pruebas.
 */
export function getCurrentUtcDate(now: Date = new Date()): string {
  if (!(now instanceof Date) || Number.isNaN(now.getTime())) {
    throw new RangeError('getCurrentUtcDate requiere una fecha válida')
  }

  return [
    pad(now.getUTCFullYear(), 4),
    pad(now.getUTCMonth() + 1),
    pad(now.getUTCDate()),
  ].join('-')
}

/**
 * Devuelve el periodo predeterminado: del primer día del mes UTC actual al
 * día UTC actual, ambos inclusive.
 */
export function getDefaultUtcMonthRange(now: Date = new Date()): DateRange {
  const toDate = getCurrentUtcDate(now)

  return {
    fromDate: `${toDate.slice(0, 8)}01`,
    toDate,
  }
}

/**
 * Indica si `value` es una fecha calendario real en formato `YYYY-MM-DD`.
 *
 * Rechaza formatos alternativos, meses fuera de rango y días imposibles
 * como `2026-02-30` o `2026-04-31`.
 */
export function isValidIsoDate(value: string): boolean {
  const match = ISO_DATE_PATTERN.exec(value)

  if (!match) {
    return false
  }

  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])

  if (year < 1 || month < 1 || month > 12) {
    return false
  }

  return day >= 1 && day <= daysInMonth(year, month)
}

/**
 * Compara dos fechas ISO `YYYY-MM-DD` sin construir objetos `Date`.
 *
 * Al estar en formato canónico con ceros a la izquierda, la comparación
 * lexicográfica equivale a la cronológica y no depende de la zona horaria.
 *
 * @throws {RangeError} Si alguna de las fechas no es válida.
 */
export function compareIsoDates(left: string, right: string): number {
  if (!isValidIsoDate(left) || !isValidIsoDate(right)) {
    throw new RangeError(
      'compareIsoDates requiere fechas ISO YYYY-MM-DD válidas',
    )
  }

  if (left === right) {
    return 0
  }

  return left < right ? -1 : 1
}

/**
 * Valida un rango de fechas para la consulta `generalBalance`.
 *
 * Devuelve una unión discriminada: si el rango es válido incluye el rango
 * normalizado; si no, incluye un motivo estable y un mensaje para la
 * interfaz.
 */
export function validateDateRange(
  fromDate: string,
  toDate: string,
): DateRangeValidation {
  if (!fromDate) {
    return {
      ok: false,
      reason: 'missing-from',
      message: 'Selecciona la fecha inicial.',
    }
  }

  if (!toDate) {
    return {
      ok: false,
      reason: 'missing-to',
      message: 'Selecciona la fecha final.',
    }
  }

  if (!isValidIsoDate(fromDate)) {
    return {
      ok: false,
      reason: 'invalid-from',
      message: 'La fecha inicial no es una fecha válida (YYYY-MM-DD).',
    }
  }

  if (!isValidIsoDate(toDate)) {
    return {
      ok: false,
      reason: 'invalid-to',
      message: 'La fecha final no es una fecha válida (YYYY-MM-DD).',
    }
  }

  if (compareIsoDates(fromDate, toDate) > 0) {
    return {
      ok: false,
      reason: 'from-after-to',
      message: 'La fecha inicial no puede ser posterior a la fecha final.',
    }
  }

  return {
    ok: true,
    range: { fromDate, toDate },
  }
}
