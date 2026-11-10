import { useRef, useState } from 'react'
import { useGeneralBalance } from '../../hooks/useGeneralBalance'
import type { BalanceError } from '../../lib/balanceErrors'
import { getDefaultUtcMonthRange } from '../../lib/dateRange'
import type { DateRange } from '../../lib/dateRange'
import { AccountsTable } from './components/AccountsTable'
import { BalanceSummary } from './components/BalanceSummary'
import { DashboardHeader } from './components/DashboardHeader'
import { DateRangeFilter } from './components/DateRangeFilter'
import './dashboard.css'

const RETRYABLE_ERRORS = new Set<BalanceError['kind']>([
  'network',
  'graphql',
])

/**
 * Página principal del dashboard financiero.
 *
 * El rango aplicado vive aquí; el filtro solo lo actualiza después de
 * validarlo. La consulta, la sesión y la clasificación de errores las
 * resuelve `useGeneralBalance`.
 */
export function DashboardPage() {
  const [range, setRange] = useState<DateRange>(() =>
    getDefaultUtcMonthRange(),
  )

  const {
    balance,
    loading,
    isRefetching,
    error,
    refetch,
  } = useGeneralBalance(range)

  const showInitialLoading = loading && balance === null
  const showBlockingError = error !== null && balance === null
  const showUpdateError = error !== null && balance !== null
  const summaryTitleRef = useRef<HTMLHeadingElement>(null)

  async function runRefetch(moveFocus: boolean) {
    try {
      await refetch()
    } catch {
      // El resultado del reintento queda reflejado en el estado del hook.
    } finally {
      if (moveFocus) {
        // En los reintentos el botón desaparece al resolverse la consulta;
        // mover el foco al título evita que el usuario de teclado lo pierda.
        summaryTitleRef.current?.focus()
      }
    }
  }

  return (
    <div className="dashboard-page">
      <DashboardHeader />

      <div className="dashboard-main">
        <section
          className="dashboard-content"
          aria-labelledby="dashboard-content-title"
        >
          <div className="dashboard-content__header">
            <p className="eyebrow">Balance general</p>
            <h2 id="dashboard-content-title">Resumen financiero</h2>
            <p className="dashboard-content__lead">
              Consulta los indicadores del periodo seleccionado. Los importes
              los calcula el servidor a partir de los movimientos registrados.
            </p>
          </div>

          <DateRangeFilter
            range={range}
            onApply={setRange}
            isUpdating={loading}
          />

          <section
            className="dashboard-panel"
            aria-labelledby="dashboard-summary-title"
          >
            <div className="dashboard-panel__heading">
              <h3
                id="dashboard-summary-title"
                ref={summaryTitleRef}
                tabIndex={-1}
              >
                Resumen del balance
              </h3>

              {balance !== null ? (
                <button
                  className="button button--secondary dashboard-panel__refresh"
                  type="button"
                  onClick={() => void runRefetch(false)}
                  disabled={loading}
                >
                  Actualizar
                </button>
              ) : null}
            </div>

            {isRefetching ? (
              <p className="dashboard-status" role="status">
                Actualizando balance…
              </p>
            ) : null}

            {showInitialLoading ? (
              <p className="dashboard-status" role="status">
                Cargando balance…
              </p>
            ) : null}

            <div
              className="dashboard-panel__body"
              aria-busy={showInitialLoading || isRefetching}
            >
              {showBlockingError && error ? (
                <div
                  className="alert alert--error dashboard-alert"
                  role="alert"
                >
                  <p>{error.message}</p>
                  {RETRYABLE_ERRORS.has(error.kind) ? (
                    <button
                      className="button button--secondary dashboard-alert__action"
                      type="button"
                      onClick={() => void runRefetch(true)}
                    >
                      Reintentar
                    </button>
                  ) : null}
                </div>
              ) : null}

              {showUpdateError && error && balance ? (
                <div
                  className="alert alert--warning dashboard-alert"
                  role="alert"
                >
                  <p>
                    No se pudo actualizar el balance. Se muestran los datos del
                    periodo {balance.fromDate} a {balance.toDate} (UTC).
                  </p>
                  {RETRYABLE_ERRORS.has(error.kind) ? (
                    <button
                      className="button button--secondary dashboard-alert__action"
                      type="button"
                      onClick={() => void runRefetch(true)}
                    >
                      Reintentar
                    </button>
                  ) : null}
                </div>
              ) : null}

              {showInitialLoading ? (
                <div className="dashboard-summary dashboard-summary--loading">
                  <div
                    className="dashboard-summary__grid"
                    aria-hidden="true"
                  >
                    {Array.from({ length: 5 }, (_, index) => (
                      <div
                        key={index}
                        className="dashboard-summary__item dashboard-summary__skeleton"
                      />
                    ))}
                  </div>
                </div>
              ) : null}

              {!showInitialLoading && balance ? (
                <BalanceSummary balance={balance} />
              ) : null}

              {!showInitialLoading && !balance && !error ? (
                <p className="dashboard-empty">
                  Selecciona un periodo válido para consultar el balance.
                </p>
              ) : null}
            </div>
          </section>

          <section
            className="dashboard-panel dashboard-panel--accounts"
            aria-labelledby="dashboard-accounts-title"
            aria-busy={loading}
          >
            <div className="dashboard-panel__heading">
              <h3 id="dashboard-accounts-title">Detalle de cuentas</h3>
              {balance ? (
                <p className="dashboard-panel__meta">
                  {`Periodo ${balance.fromDate} a ${balance.toDate} (UTC) · Importes en MXN`}
                </p>
              ) : null}
            </div>

            {balance ? (
              <AccountsTable accounts={balance.accounts} />
            ) : error ? (
              <p className="dashboard-empty">
                No se pudieron cargar las cuentas.
              </p>
            ) : (
              <p className="dashboard-empty">
                Las cuentas aparecerán cuando se reciba el balance del
                periodo.
              </p>
            )}
          </section>
        </section>
      </div>
    </div>
  )
}
