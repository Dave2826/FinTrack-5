import { useAuth } from '../../auth/useAuth'
import { LoginForm } from './LoginForm'

export function LoginPage() {
  const { sessionEndReason } = useAuth()

  return (
    <section className="login-card" aria-labelledby="login-title">
      <div className="login-card__header">
        <p className="eyebrow">Acceso seguro</p>
        <h2 id="login-title">Inicia sesión</h2>
        <p className="login-card__lead">
          Ingresa con tu cuenta corporativa para consultar el panel financiero.
        </p>
      </div>

      {sessionEndReason === 'expired' ? (
        <p className="alert alert--warning" role="alert">
          Tu sesión expiró por seguridad. Vuelve a iniciar sesión.
        </p>
      ) : null}

      <LoginForm />

      <p className="login-note">
        La sesión se mantiene solo en esta pestaña y se cierra al recargar la
        página.
      </p>
    </section>
  )
}
