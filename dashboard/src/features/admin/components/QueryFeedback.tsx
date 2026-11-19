import type { ApiErrorInfo } from '../../../lib/apiErrors'

interface QueryFeedbackProps {
  loading: boolean
  hasData: boolean
  error: ApiErrorInfo | null
  loadingText: string
  onRetry: () => void
}

/** Carga, error de lectura y reintento, comunes a las tablas. */
export function QueryFeedback({
  loading,
  hasData,
  error,
  loadingText,
  onRetry,
}: QueryFeedbackProps) {
  if (error?.kind === 'session') {
    return (
      <p className="dashboard-status" role="status">
        Cerrando sesión…
      </p>
    )
  }

  if (error) {
    return (
      <div className="alert alert--error admin-alert" role="alert">
        <p>{error.message}</p>
        {error.kind === 'network' ? (
          <button
            className="button button--secondary admin-button"
            type="button"
            onClick={onRetry}
          >
            Reintentar
          </button>
        ) : null}
      </div>
    )
  }

  if (loading && !hasData) {
    return (
      <p className="dashboard-status" role="status">
        {loadingText}
      </p>
    )
  }

  return null
}
