import { formatMxn } from '../../../lib/format'
import type { AccountBalance } from '../../../types/balance'

interface AccountsTableProps {
  accounts: readonly AccountBalance[]
}

/**
 * Presenta las cuentas devueltas por el backend para el periodo consultado.
 *
 * Los importes se muestran tal como llegan, únicamente con `formatMxn`. El
 * estado de actividad se toma de `isActive` y el de riesgo de `isInRed`; no se
 * infieren a partir de los importes ni se recalculan saldos o utilidades.
 */
export function AccountsTable({ accounts }: AccountsTableProps) {
  if (accounts.length === 0) {
    return (
      <p className="accounts-empty" role="status">
        Esta empresa no tiene cuentas registradas para el periodo consultado.
      </p>
    )
  }

  return (
    <div className="accounts-table-wrapper">
      <table className="accounts-table" role="table">
        <caption className="dashboard-visually-hidden">
          Cuentas del balance del periodo
        </caption>

        <thead role="rowgroup">
          <tr role="row">
            <th role="columnheader" scope="col">
              Cuenta
            </th>
            <th role="columnheader" scope="col">
              Estado
            </th>
            <th
              role="columnheader"
              scope="col"
              className="accounts-table__amount"
            >
              Saldo inicial
            </th>
            <th
              role="columnheader"
              scope="col"
              className="accounts-table__amount"
            >
              Ingresos
            </th>
            <th
              role="columnheader"
              scope="col"
              className="accounts-table__amount"
            >
              Egresos
            </th>
            <th
              role="columnheader"
              scope="col"
              className="accounts-table__amount"
            >
              Utilidad
            </th>
            <th
              role="columnheader"
              scope="col"
              className="accounts-table__amount"
            >
              Saldo final
            </th>
          </tr>
        </thead>

        <tbody role="rowgroup">
          {accounts.map((account) => (
            <tr key={account.accountId} role="row">
              <th
                role="rowheader"
                scope="row"
                className="accounts-table__account"
              >
                {account.accountName}
              </th>

              <td role="cell" data-label="Estado">
                <div className="accounts-table__statuses">
                  <span
                    className={`accounts-table__badge ${
                      account.isActive
                        ? 'accounts-table__badge--active'
                        : 'accounts-table__badge--inactive'
                    }`}
                  >
                    {account.isActive ? 'Activa' : 'Inactiva'}
                  </span>
                  <span
                    className={`accounts-table__badge ${
                      account.isInRed
                        ? 'accounts-table__badge--risk'
                        : 'accounts-table__badge--safe'
                    }`}
                  >
                    {account.isInRed ? 'En riesgo' : 'Sin riesgo'}
                  </span>
                </div>
              </td>

              <td
                role="cell"
                data-label="Saldo inicial"
                className="accounts-table__amount"
              >
                {formatMxn(account.openingBalance)}
              </td>
              <td
                role="cell"
                data-label="Ingresos"
                className="accounts-table__amount"
              >
                {formatMxn(account.totalIncome)}
              </td>
              <td
                role="cell"
                data-label="Egresos"
                className="accounts-table__amount"
              >
                {formatMxn(account.totalExpense)}
              </td>
              <td
                role="cell"
                data-label="Utilidad"
                className={`accounts-table__amount ${
                  account.profit.startsWith('-')
                    ? 'accounts-table__amount--negative'
                    : ''
                }`}
              >
                {formatMxn(account.profit)}
              </td>
              <td
                role="cell"
                data-label="Saldo final"
                className={`accounts-table__amount accounts-table__closing ${
                  account.isInRed
                    ? 'accounts-table__closing--risk'
                    : ''
                }`}
              >
                {formatMxn(account.closingBalance)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
