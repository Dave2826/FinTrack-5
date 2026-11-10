import { formatMxn } from '../../../lib/format'
import type { GeneralBalance } from '../../../types/balance'

interface BalanceSummaryProps {
  balance: GeneralBalance
}

type IndicatorTone = 'neutral' | 'income' | 'expense' | 'primary' | 'risk'

interface Indicator {
  key: string
  label: string
  value: string
  tone: IndicatorTone
}

/**
 * Presenta los cinco indicadores calculados por el backend.
 *
 * No se realiza ninguna operación aritmética: los valores se muestran tal
 * como llegan y solo se les aplica el formato MXN. El tono de la utilidad se
 * deriva del signo recibido y el del saldo final de `isInRed`.
 */
export function BalanceSummary({ balance }: BalanceSummaryProps) {
  const indicators: Indicator[] = [
    {
      key: 'opening',
      label: 'Saldo inicial',
      value: balance.openingBalance,
      tone: 'neutral',
    },
    {
      key: 'income',
      label: 'Ingresos',
      value: balance.totalIncome,
      tone: 'income',
    },
    {
      key: 'expense',
      label: 'Egresos',
      value: balance.totalExpense,
      tone: 'expense',
    },
    {
      key: 'profit',
      label: 'Utilidad',
      value: balance.profit,
      tone: balance.profit.startsWith('-') ? 'expense' : 'income',
    },
    {
      key: 'closing',
      label: 'Saldo final',
      value: balance.closingBalance,
      tone: balance.isInRed ? 'risk' : 'primary',
    },
  ]

  return (
    <div className="dashboard-summary">
      <p className="dashboard-summary__period">
        {`Periodo consultado: ${balance.fromDate} a ${balance.toDate} (UTC) · Importes en MXN`}
      </p>

      <dl className="dashboard-summary__grid">
        {indicators.map((indicator) => (
          <div
            key={indicator.key}
            className={`dashboard-summary__item dashboard-summary__item--${indicator.tone}`}
          >
            <dt>{indicator.label}</dt>
            <dd>{formatMxn(indicator.value)}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
