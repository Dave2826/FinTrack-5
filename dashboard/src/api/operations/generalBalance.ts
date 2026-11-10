import { gql } from '@apollo/client'

/**
 * Consulta del balance general de la empresa autenticada.
 *
 * Contrato exacto del backend: `generalBalance(fromDate: Date!, toDate: Date!)`.
 * La empresa se obtiene de la identidad del token; `companyId` es solo un
 * campo de salida y nunca viaja como argumento. Los importes se reciben como
 * cadenas decimales y las fechas como días completos UTC (`YYYY-MM-DD`).
 */
export const GENERAL_BALANCE_QUERY = gql`
  query GeneralBalance($fromDate: Date!, $toDate: Date!) {
    generalBalance(fromDate: $fromDate, toDate: $toDate) {
      companyId
      fromDate
      toDate
      openingBalance
      totalIncome
      totalExpense
      profit
      closingBalance
      accountsInRed
      isInRed
      currency
      accounts {
        accountId
        accountName
        isActive
        openingBalance
        totalIncome
        totalExpense
        profit
        closingBalance
        isInRed
        currency
      }
    }
  }
`
