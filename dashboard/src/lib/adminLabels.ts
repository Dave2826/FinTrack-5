import type { AccountType, ConceptType } from '../types/admin'

/** Catálogo de tipos de cuenta del Parcial I con su etiqueta en pantalla. */
export const ACCOUNT_TYPE_LABELS: Record<AccountType, string> = {
  CASH: 'Efectivo',
  DEBIT: 'Débito',
  CREDIT: 'Crédito',
  SAVINGS: 'Ahorro',
  INVESTMENT: 'Inversión',
  WALLET: 'Monedero',
  OTHER: 'Otro',
}

export const ACCOUNT_TYPES = Object.keys(ACCOUNT_TYPE_LABELS) as AccountType[]

export const CONCEPT_TYPE_LABELS: Record<ConceptType, string> = {
  INCOME: 'Ingreso',
  EXPENSE: 'Egreso',
}

export function accountTypeLabel(value: string): string {
  return ACCOUNT_TYPE_LABELS[value as AccountType] ?? value
}

export function conceptTypeLabel(value: string): string {
  return CONCEPT_TYPE_LABELS[value as ConceptType] ?? value
}

/**
 * Referencia corta de una cuenta. Nunca se muestra la CLABE completa:
 * se usan los últimos dígitos de la tarjeta o los últimos 4 de la CLABE.
 */
export function accountReference(account: {
  cardLastDigits: string | null
  clabe: string | null
}): string {
  const card = account.cardLastDigits?.trim()

  if (card) {
    return `Tarjeta •••• ${card.slice(-4)}`
  }

  const clabe = account.clabe?.replace(/\s+/g, '')

  if (clabe) {
    return `CLABE •••• ${clabe.slice(-4)}`
  }

  return '—'
}

/** Coincidencia sin acentos ni mayúsculas para la búsqueda en pantalla. */
export function normalizeSearch(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim()
}
