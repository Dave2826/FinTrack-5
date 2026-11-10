import { useId, useState } from 'react'
import type { FormEvent } from 'react'
import {
  AuthError,
  messageForAuthError,
  toAuthError,
} from '../../auth/authErrors'
import { useAuth } from '../../auth/useAuth'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

interface FieldErrors {
  email?: string
  password?: string
}

export function LoginForm() {
  const { login } = useAuth()
  const emailId = useId()
  const passwordId = useId()
  const formErrorId = useId()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  function validate(): FieldErrors {
    const errors: FieldErrors = {}
    const normalizedEmail = email.trim()

    if (!normalizedEmail) {
      errors.email = 'El correo electrónico es obligatorio.'
    } else if (!EMAIL_PATTERN.test(normalizedEmail)) {
      errors.email = 'Escribe un correo electrónico válido.'
    }

    if (!password) {
      errors.password = 'La contraseña es obligatoria.'
    }

    return errors
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (isSubmitting) {
      return
    }

    const errors = validate()
    setFieldErrors(errors)

    if (Object.keys(errors).length > 0) {
      setFormError(null)
      return
    }

    setFormError(null)
    setIsSubmitting(true)

    try {
      await login({ email: email.trim(), password })
      // En caso de éxito, RequireAuth desmonta este formulario.
    } catch (error) {
      const authError =
        error instanceof AuthError ? error : toAuthError(error)
      setFormError(messageForAuthError(authError))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form
      className="login-form"
      onSubmit={handleSubmit}
      noValidate
      aria-describedby={formError ? formErrorId : undefined}
    >
      {formError ? (
        <p className="alert alert--error" id={formErrorId} role="alert">
          {formError}
        </p>
      ) : null}

      <div className="field">
        <label className="field__label" htmlFor={emailId}>
          Correo electrónico
        </label>
        <input
          id={emailId}
          className="field__input"
          type="email"
          name="email"
          placeholder="nombre@empresa.com"
          autoComplete="username"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          disabled={isSubmitting}
          required
          aria-invalid={fieldErrors.email ? true : undefined}
          aria-describedby={
            fieldErrors.email ? `${emailId}-error` : undefined
          }
        />
        {fieldErrors.email ? (
          <p className="field__error" id={`${emailId}-error`}>
            {fieldErrors.email}
          </p>
        ) : null}
      </div>

      <div className="field">
        <label className="field__label" htmlFor={passwordId}>
          Contraseña
        </label>
        <input
          id={passwordId}
          className="field__input"
          type="password"
          name="password"
          placeholder="••••••••"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          disabled={isSubmitting}
          required
          aria-invalid={fieldErrors.password ? true : undefined}
          aria-describedby={
            fieldErrors.password ? `${passwordId}-error` : undefined
          }
        />
        {fieldErrors.password ? (
          <p className="field__error" id={`${passwordId}-error`}>
            {fieldErrors.password}
          </p>
        ) : null}
      </div>

      <button
        className="button button--primary"
        type="submit"
        disabled={isSubmitting}
        aria-busy={isSubmitting}
      >
        {isSubmitting ? 'Entrando…' : 'Entrar'}
      </button>
    </form>
  )
}
