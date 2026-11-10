/**
 * Tipos del contrato `generalBalance` expuesto por el backend GraphQL.
 *
 * Los importes viajan como cadenas decimales (`Decimal!` → string) para no
 * perder precisión: el frontend solo los presenta y nunca los recalcula.
 * Las fechas viajan como días completos UTC en formato `YYYY-MM-DD`.
 *
 * No se añaden campos ni argumentos distintos a los del esquema real.
 */

export interface AccountBalance {
  accountId: string
  accountName: string
  isActive: boolean
  openingBalance: string
  totalIncome: string
  totalExpense: string
  profit: string
  closingBalance: string
  isInRed: boolean
  currency: string
}

export interface GeneralBalance {
  companyId: string
  fromDate: string
  toDate: string
  openingBalance: string
  totalIncome: string
  totalExpense: string
  profit: string
  closingBalance: string
  accountsInRed: number
  isInRed: boolean
  currency: string
  accounts: AccountBalance[]
}

export interface GeneralBalanceVariables {
  fromDate: string
  toDate: string
}

export interface GeneralBalanceResult {
  generalBalance: GeneralBalance
}
