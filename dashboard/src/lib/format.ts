/**
 * Formato de importes monetarios MXN.
 *
 * El backend envía los importes como cadenas decimales (`Decimal!` → string)
 * para no perder precisión. Esta utilidad solo los presenta: nunca convierte
 * a `number`, no usa `parseFloat` y no realiza aritmética de punto flotante.
 */

const DECIMAL_PATTERN = /^(-?)(\d+)(?:\.(\d{1,2}))?$/

/**
 * Formatea una cadena decimal como moneda mexicana con dos decimales.
 *
 * Acepta enteros o hasta dos decimales (`"1531"`, `"1531.5"`, `"1531.50"`).
 * Agrupa los miles con comas y coloca el signo negativo antes del símbolo
 * (`-$200.00`). El cero negativo (`"-0.00"`) se normaliza a `"$0.00"`.
 *
 * @throws {RangeError} Si el valor no es una cadena decimal válida. No se
 * oculta un dato incorrecto devolviendo un texto ambiguo.
 */
export function formatMxn(value: string): string {
  if (typeof value !== 'string') {
    throw new RangeError('formatMxn requiere una cadena decimal')
  }

  const match = DECIMAL_PATTERN.exec(value)

  if (!match) {
    throw new RangeError(`Importe inválido: "${value}"`)
  }

  const [, sign, integerPart, decimalPart = ''] = match

  const normalizedInteger = integerPart.replace(/^0+(?=\d)/, '')
  const decimals = decimalPart.padEnd(2, '0')
  const groupedInteger = normalizedInteger.replace(
    /\B(?=(\d{3})+(?!\d))/g,
    ',',
  )
  const isZero = normalizedInteger === '0' && decimals === '00'
  const prefix = sign === '-' && !isZero ? '-$' : '$'

  return `${prefix}${groupedInteger}.${decimals}`
}
