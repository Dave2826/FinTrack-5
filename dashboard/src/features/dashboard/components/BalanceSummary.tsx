import { formatMxn } from '../../../lib/format'
import type { GeneralBalance } from '../../../types/balance'

interface BalanceSummaryProps {
  balance: GeneralBalance
}

type IndicatorTone = 'neutral' | 'income' | 'expense' | 'primary' | 'risk'

type RiskTone = 'safe' | 'accounts' | 'global'

interface Indicator {
  key: string
  label: string
  value: string
  tone: IndicatorTone
}

interface RiskStatus {
  tone: RiskTone
  title: string
  accountsLabel: string
  note: string
}

/**
 * Traduce el estado global del backend a textos explícitos.
 *
 * Se usan directamente `isInRed` y `accountsInRed`; no se recalcula el riesgo
 * ni se infiere a partir de los saldos. El caso `isInRed === false` con
 * `accountsInRed > 0` es válido y se presenta como riesgo individual, no como
 * riesgo global.
 */
function getRiskStatus(balance: GeneralBalance): RiskStatus {
  const accountsLabel =
    balance.accountsInRed === 1
      ? '1 cuenta en números rojos'
      : `${balance.accountsInRed} cuentas en números rojos`

  if (balance.isInRed) {
    return {
      tone: 'global',
      title: 'Riesgo financiero global',
      accountsLabel,
      note: 'El saldo final global es negativo.',
    }
  }

  if (balance.accountsInRed > 0) {
    return {
      tone: 'accounts',
      title: 'Sin riesgo global',
      accountsLabel,
      note: 'El saldo final global no es negativo, pero hay cuentas individuales con saldo negativo.',
    }
  }

  return {
    tone: 'safe',
    title: 'Sin riesgo global',
    accountsLabel,
    note: 'El saldo final global no es negativo y ninguna cuenta tiene saldo negativo.',
  }
}

/**
 * Presenta los cinco indicadores calculados por el backend y el estado global
 * de riesgo.
 *
 * No se realiza ninguna operación aritmética: los valores se muestran tal
 * como llegan y solo se les aplica el formato MXN. El tono de la utilidad se
 * deriva del signo recibido y el del saldo final de `isInRed`. El indicador
 * global usa `isInRed` y `accountsInRed` sin recalcularlos.
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

  const risk = getRiskStatus(balance)

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

      <section
        className={`dashboard-summary__risk dashboard-summary__risk--${risk.tone}`}
        aria-labelledby="dashboard-global-risk-title"
      >
        <h4
          id="dashboard-global-risk-title"
          className="dashboard-summary__risk-title"
        >
          {risk.title}
        </h4>
        <p className="dashboard-summary__risk-count">{risk.accountsLabel}</p>
        <p className="dashboard-summary__risk-note">{risk.note}</p>
      </section>
    </div>
  )
}
