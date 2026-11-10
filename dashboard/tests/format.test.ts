import { describe, expect, it } from 'vitest'
import { formatMxn } from '../src/lib/format'

describe('formatMxn', () => {
  it('formatea cero como $0.00', () => {
    expect(formatMxn('0.00')).toBe('$0.00')
  })

  it('formatea importes positivos', () => {
    expect(formatMxn('1531.00')).toBe('$1,531.00')
    expect(formatMxn('12.50')).toBe('$12.50')
  })

  it('formatea importes negativos con el signo antes del símbolo', () => {
    expect(formatMxn('-200.00')).toBe('-$200.00')
  })

  it('agrupa miles', () => {
    expect(formatMxn('1234.56')).toBe('$1,234.56')
    expect(formatMxn('987654.32')).toBe('$987,654.32')
  })

  it('agrupa millones', () => {
    expect(formatMxn('1000000.00')).toBe('$1,000,000.00')
  })

  it('garantiza dos decimales', () => {
    expect(formatMxn('7')).toBe('$7.00')
    expect(formatMxn('7.5')).toBe('$7.50')
    expect(formatMxn('-3.1')).toBe('-$3.10')
  })

  it('normaliza el cero negativo', () => {
    expect(formatMxn('-0.00')).toBe('$0.00')
    expect(formatMxn('-0.0')).toBe('$0.00')
  })

  it('rechaza la cadena vacía', () => {
    expect(() => formatMxn('')).toThrow(RangeError)
  })

  it('rechaza caracteres inválidos', () => {
    const invalidValues = [
      'abc',
      '$12.00',
      '1,234.00',
      ' 12.00 ',
      '+12.00',
      '1e3',
    ]

    for (const value of invalidValues) {
      expect(() => formatMxn(value)).toThrow(RangeError)
    }
  })

  it('rechaza más de dos decimales', () => {
    expect(() => formatMxn('12.345')).toThrow(RangeError)
  })

  it('rechaza formatos malformados', () => {
    const malformedValues = [
      '12.',
      '.50',
      '1.2.3',
      '--5.00',
      '12,5',
      'NaN',
      'Infinity',
    ]

    for (const value of malformedValues) {
      expect(() => formatMxn(value)).toThrow(RangeError)
    }
  })
})
