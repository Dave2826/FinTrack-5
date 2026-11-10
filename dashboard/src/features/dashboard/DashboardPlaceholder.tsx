import { useState } from 'react'
import { useAuth } from '../../auth/useAuth'

const timeFormatter = new Intl.DateTimeFormat('es-MX', {
  hour: '2-digit',
  minute: '2-digit',
})

export function DashboardPlaceholder() {
  const { user, expiresAt, logout } = useAuth()
  const [isSigningOut, setIsSigningOut] = useState(false)

  async function handleLogout() {
    if (isSigningOut) {
      return
    }

    setIsSigningOut(true)

    try {
      await logout('manual')
    } finally {
      setIsSigningOut(false)
    }
  }

  return (
    <section className="login-card session-card" aria-labelledby="session-title">
      <div className="login-card__header">
        <p className="eyebrow">Sesión iniciada</p>
        <h2 id="session-title">Acceso concedido</h2>
        <p className="session-lead">
          Autenticación correcta. El dashboard financiero se implementará en la
          siguiente etapa.
        </p>
      </div>

      <dl className="session-details">
        <div>
          <dt>Usuario</dt>
          <dd>{user?.name ?? '—'}</dd>
        </div>
        <div>
          <dt>Correo</dt>
          <dd>{user?.email ?? '—'}</dd>
        </div>
        {expiresAt !== null ? (
          <div>
            <dt>Sesión válida hasta</dt>
            <dd>{timeFormatter.format(new Date(expiresAt))}</dd>
          </div>
        ) : null}
      </dl>

      <button
        className="button button--secondary"
        type="button"
        onClick={() => void handleLogout()}
        disabled={isSigningOut}
      >
        {isSigningOut ? 'Cerrando sesión…' : 'Cerrar sesión'}
      </button>
    </section>
  )
}
