import { useState } from 'react'
import { decodeJwtPayload } from '../../../auth/jwt'
import { tokenStore } from '../../../auth/tokenStore'
import { useAuth } from '../../../auth/useAuth'
import { BrandMark } from '../../../components/BrandMark'

const timeFormatter = new Intl.DateTimeFormat('es-MX', {
  hour: '2-digit',
  minute: '2-digit',
})

/**
 * Identificador de la empresa de la sesión actual.
 *
 * Se deriva del `companyId` que el backend incluye en el JWT, que vive
 * exclusivamente en memoria. No se consulta al backend ni se acepta como
 * parámetro del cliente.
 */
function getCompanyLabel(): string {
  const token = tokenStore.get()

  if (!token) {
    return 'Empresa no identificada'
  }

  const companyId = decodeJwtPayload(token)?.companyId

  if (typeof companyId !== 'number' || !Number.isFinite(companyId)) {
    return 'Empresa no identificada'
  }

  return `Empresa #${companyId}`
}

export function DashboardHeader() {
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
    <header className="dashboard-header">
      <div className="dashboard-header__brand">
        <BrandMark />
      </div>

      <div className="dashboard-header__identity">
        <p className="eyebrow">Panel financiero</p>
        <h1 className="dashboard-header__title">Dashboard financiero</h1>
        <p className="dashboard-header__company">{getCompanyLabel()}</p>
      </div>

      <div className="dashboard-header__session">
        <div className="dashboard-header__user">
          <p className="dashboard-header__status">Autenticación correcta</p>
          {user ? (
            <>
              <p className="dashboard-header__name">{user.name}</p>
              <p className="dashboard-header__email">{user.email}</p>
            </>
          ) : null}
          {expiresAt !== null ? (
            <p className="dashboard-header__expiry">
              Sesión válida hasta{' '}
              {timeFormatter.format(new Date(expiresAt))}
            </p>
          ) : null}
        </div>

        <button
          className="button button--secondary dashboard-header__logout"
          type="button"
          onClick={() => void handleLogout()}
          disabled={isSigningOut}
        >
          {isSigningOut ? 'Cerrando sesión…' : 'Cerrar sesión'}
        </button>
      </div>
    </header>
  )
}
