import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { tokenStore } from '../src/auth/tokenStore'
import { loginMock, makeJwt } from './helpers/auth'
import { renderApp } from './helpers/renderApp'

const EMAIL = 'admin_a@test.local'
const PASSWORD = 'clave-correcta'

type UserEventApi = ReturnType<typeof userEvent.setup>

async function signIn(user: UserEventApi) {
  await user.type(screen.getByLabelText('Correo electrónico'), EMAIL)
  await user.type(screen.getByLabelText('Contraseña'), PASSWORD)
  await user.click(screen.getByRole('button', { name: 'Entrar' }))
}

function encodeSegment(value: unknown): string {
  return btoa(JSON.stringify(value))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')
}

/** JWT de prueba con una empresa concreta, solo para leer el payload. */
function makeCompanyToken(companyId: number): string {
  const header = { alg: 'HS256', typ: 'JWT' }
  const payload = {
    companyUserId: 7,
    companyId,
    exp: Math.floor(Date.now() / 1000) + 1800,
  }

  return `${encodeSegment(header)}.${encodeSegment(payload)}.firma-de-prueba`
}

describe('dashboard', () => {
  it('renderiza el encabezado y las áreas reservadas tras iniciar sesión', async () => {
    const user = userEvent.setup()

    renderApp([
      loginMock({ email: EMAIL, password: PASSWORD, token: makeJwt(1800) }),
    ])

    await signIn(user)

    expect(
      await screen.findByRole('heading', { name: 'Dashboard financiero' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Empresa #11')).toBeInTheDocument()
    expect(screen.getByText(EMAIL)).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Cerrar sesión' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'Resumen del balance' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'Detalle de cuentas' }),
    ).toBeInTheDocument()
  })

  it('muestra la empresa obtenida del token de la sesión', async () => {
    const user = userEvent.setup()

    renderApp([
      loginMock({
        email: EMAIL,
        password: PASSWORD,
        token: makeCompanyToken(42),
      }),
    ])

    await signIn(user)

    expect(await screen.findByText('Empresa #42')).toBeInTheDocument()
  })

  it('cierra la sesión con el mecanismo existente', async () => {
    const user = userEvent.setup()
    const token = makeJwt(1800)

    renderApp([loginMock({ email: EMAIL, password: PASSWORD, token })])

    await signIn(user)
    await screen.findByText('Empresa #11')

    await user.click(screen.getByRole('button', { name: 'Cerrar sesión' }))

    expect(
      await screen.findByRole('heading', { name: 'Inicia sesión' }),
    ).toBeInTheDocument()
    expect(tokenStore.get()).toBeNull()
    expect(
      screen.queryByText(/Autenticación correcta/i),
    ).not.toBeInTheDocument()
  })

  it('conserva el BrandPanel en la pantalla de login', () => {
    renderApp([])

    expect(
      screen.getByRole('complementary', {
        name: 'Presentación de FinTrack-5',
      }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { level: 1, name: 'FinTrack-5' }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('heading', { name: 'Dashboard financiero' }),
    ).not.toBeInTheDocument()
  })

  it('mantiene el dashboard protegido sin sesión', () => {
    renderApp([])

    expect(
      screen.getByRole('heading', { name: 'Inicia sesión' }),
    ).toBeInTheDocument()
    expect(screen.queryByText(/Empresa #/)).not.toBeInTheDocument()
    expect(
      screen.queryByRole('heading', { name: 'Dashboard financiero' }),
    ).not.toBeInTheDocument()
  })

  it('no muestra importes ni indicadores financieros ficticios', async () => {
    const user = userEvent.setup()

    renderApp([
      loginMock({ email: EMAIL, password: PASSWORD, token: makeJwt(1800) }),
    ])

    await signIn(user)
    await screen.findByRole('heading', { name: 'Dashboard financiero' })

    expect(screen.queryByText(/\$\s?\d/)).not.toBeInTheDocument()
    expect(screen.queryByText(/saldo final/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/ingresos totales/i)).not.toBeInTheDocument()
  })
})
