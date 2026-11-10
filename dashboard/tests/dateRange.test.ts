import { describe, expect, it } from 'vitest'
import {
  compareIsoDates,
  getCurrentUtcDate,
  getDefaultUtcMonthRange,
  isValidIsoDate,
  validateDateRange,
} from '../src/lib/dateRange'

describe('getCurrentUtcDate', () => {
  it('devuelve el día UTC actual con mes y día de dos dígitos', () => {
    expect(getCurrentUtcDate(new Date('2026-01-05T12:00:00Z'))).toBe(
      '2026-01-05',
    )
    expect(getCurrentUtcDate(new Date('2026-11-09T23:59:59Z'))).toBe(
      '2026-11-09',
    )
  })

  it('no depende de la zona horaria local', () => {
    expect(getCurrentUtcDate(new Date('2026-03-01T02:30:00Z'))).toBe(
      '2026-03-01',
    )
    expect(getCurrentUtcDate(new Date('2026-02-28T23:30:00Z'))).toBe(
      '2026-02-28',
    )
  })

  it('rechaza una fecha inválida', () => {
    expect(() => getCurrentUtcDate(new Date('fecha inválida'))).toThrow(
      RangeError,
    )
  })
})

describe('getDefaultUtcMonthRange', () => {
  it('usa el primer día del mes UTC como inicio y el día actual como fin', () => {
    expect(getDefaultUtcMonthRange(new Date('2026-11-10T15:00:00Z'))).toEqual({
      fromDate: '2026-11-01',
      toDate: '2026-11-10',
    })
  })

  it('funciona el primer día del mes', () => {
    expect(getDefaultUtcMonthRange(new Date('2026-03-01T00:00:00Z'))).toEqual({
      fromDate: '2026-03-01',
      toDate: '2026-03-01',
    })
  })

  it('cambia de mes correctamente', () => {
    expect(getDefaultUtcMonthRange(new Date('2026-02-28T10:00:00Z'))).toEqual({
      fromDate: '2026-02-01',
      toDate: '2026-02-28',
    })
  })

  it('cambia de año correctamente', () => {
    expect(getDefaultUtcMonthRange(new Date('2025-12-31T23:30:00Z'))).toEqual({
      fromDate: '2025-12-01',
      toDate: '2025-12-31',
    })
    expect(getDefaultUtcMonthRange(new Date('2026-01-01T00:00:00Z'))).toEqual({
      fromDate: '2026-01-01',
      toDate: '2026-01-01',
    })
  })
})

describe('isValidIsoDate', () => {
  it('acepta fechas calendario válidas', () => {
    expect(isValidIsoDate('2026-01-01')).toBe(true)
    expect(isValidIsoDate('2026-11-10')).toBe(true)
    expect(isValidIsoDate('2024-02-29')).toBe(true)
  })

  it('rechaza fechas imposibles', () => {
    expect(isValidIsoDate('2026-02-30')).toBe(false)
    expect(isValidIsoDate('2026-02-29')).toBe(false)
    expect(isValidIsoDate('2026-04-31')).toBe(false)
    expect(isValidIsoDate('2026-13-01')).toBe(false)
    expect(isValidIsoDate('2026-00-10')).toBe(false)
    expect(isValidIsoDate('0000-01-01')).toBe(false)
  })

  it('rechaza formatos distintos a YYYY-MM-DD', () => {
    expect(isValidIsoDate('')).toBe(false)
    expect(isValidIsoDate('2026-1-01')).toBe(false)
    expect(isValidIsoDate('01/02/2026')).toBe(false)
    expect(isValidIsoDate('2026-01-01T00:00:00Z')).toBe(false)
    expect(isValidIsoDate(' 2026-01-01')).toBe(false)
  })
})

describe('compareIsoDates', () => {
  it('compara fechas sin depender de la zona horaria', () => {
    expect(compareIsoDates('2026-01-01', '2026-01-02')).toBe(-1)
    expect(compareIsoDates('2026-01-02', '2026-01-02')).toBe(0)
    expect(compareIsoDates('2026-02-01', '2026-01-31')).toBe(1)
  })

  it('rechaza fechas inválidas', () => {
    expect(() => compareIsoDates('2026-02-30', '2026-03-01')).toThrow(
      RangeError,
    )
  })
})

describe('validateDateRange', () => {
  it('acepta un rango válido', () => {
    expect(validateDateRange('2026-01-01', '2026-12-31')).toEqual({
      ok: true,
      range: { fromDate: '2026-01-01', toDate: '2026-12-31' },
    })
  })

  it('acepta fechas iguales', () => {
    expect(validateDateRange('2026-11-10', '2026-11-10')).toEqual({
      ok: true,
      range: { fromDate: '2026-11-10', toDate: '2026-11-10' },
    })
  })

  it('rechaza un rango invertido', () => {
    const result = validateDateRange('2026-12-31', '2026-01-01')

    expect(result.ok).toBe(false)

    if (!result.ok) {
      expect(result.reason).toBe('from-after-to')
      expect(result.message).toContain('posterior')
    }
  })

  it('rechaza fechas ausentes', () => {
    const missingFrom = validateDateRange('', '2026-01-01')

    expect(missingFrom.ok).toBe(false)

    if (!missingFrom.ok) {
      expect(missingFrom.reason).toBe('missing-from')
    }

    const missingTo = validateDateRange('2026-01-01', '')

    expect(missingTo.ok).toBe(false)

    if (!missingTo.ok) {
      expect(missingTo.reason).toBe('missing-to')
    }
  })

  it('rechaza fechas inválidas', () => {
    const invalidFrom = validateDateRange('2026-02-30', '2026-03-01')

    expect(invalidFrom.ok).toBe(false)

    if (!invalidFrom.ok) {
      expect(invalidFrom.reason).toBe('invalid-from')
    }

    const invalidTo = validateDateRange('2026-03-01', '2026-02-30')

    expect(invalidTo.ok).toBe(false)

    if (!invalidTo.ok) {
      expect(invalidTo.reason).toBe('invalid-to')
    }
  })
})
