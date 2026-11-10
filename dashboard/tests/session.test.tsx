import {
  ApolloClient,
  ApolloLink,
  ApolloProvider,
  InMemoryCache,
  Observable,
  gql,
} from '@apollo/client'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import App from '../src/App'
import { tokenStore } from '../src/auth/tokenStore'
import { TEST_USER, loginMock, makeJwt } from './helpers/auth'
import { renderApp } from './helpers/renderApp'

const EMAIL = 'admin_a@test.local'
const PASSWORD = 'clave-correcta'

type UserEventApi = ReturnType<typeof userEvent.setup>

async function signIn(user: UserEventApi) {
  await user.type(screen.getByLabelText('Correo electrónico'), EMAIL)
  await user.type(screen.getByLabelText('Contraseña'), PASSWORD)
  await user.click(screen.getByRole('button', { name: 'Entrar' }))
}

describe('protección de sesión', () => {
  it('muestra el login cuando no hay sesión', () => {
    renderApp([])

    expect(
      screen.getByRole('heading', { name: 'Inicia sesión' }),
    ).toBeInTheDocument()
    expect(
      screen.queryByText(/Autenticación correcta/i),
    ).not.toBeInTheDocument()
  })

  it('cierra sesión, elimina el token y vuelve al login', async () => {
    const token = makeJwt(1800)
    const user = userEvent.setup()

    renderApp([loginMock({ email: EMAIL, password: PASSWORD, token })])

    await signIn(user)
    expect(
      await screen.findByText(/Autenticación correcta/i),
    ).toBeInTheDocument()
    expect(tokenStore.get()).toBe(token)

    await user.click(screen.getByRole('button', { name: 'Cerrar sesión' }))

    expect(
      await screen.findByRole('heading', { name: 'Inicia sesión' }),
    ).toBeInTheDocument()
    expect(tokenStore.get()).toBeNull()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('no persiste la sesión: al recargar se vuelve al login', async () => {
    const token = makeJwt(1800)
    const user = userEvent.setup()

    const { unmount } = renderApp([
      loginMock({ email: EMAIL, password: PASSWORD, token }),
    ])

    await signIn(user)
    expect(
      await screen.findByText(/Autenticación correcta/i),
    ).toBeInTheDocument()

    expect(localStorage.length).toBe(0)
    expect(sessionStorage.length).toBe(0)
    expect(document.cookie).toBe('')

    unmount()
    // Una recarga real reinicia el módulo y, con él, el token en memoria.
    tokenStore.clear()

    renderApp([])

    expect(
      screen.getByRole('heading', { name: 'Inicia sesión' }),
    ).toBeInTheDocument()
    expect(tokenStore.get()).toBeNull()
  })

  it('cierra la sesión automáticamente cuando el JWT expira', async () => {
    const token = makeJwt(2)
    const user = userEvent.setup()

    renderApp([loginMock({ email: EMAIL, password: PASSWORD, token })])

    await signIn(user)
    expect(
      await screen.findByText(/Autenticación correcta/i),
    ).toBeInTheDocument()

    expect(
      await screen.findByRole(
        'heading',
        { name: 'Inicia sesión' },
        { timeout: 4000 },
      ),
    ).toBeInTheDocument()
    expect(tokenStore.get()).toBeNull()
    expect(screen.getByRole('alert')).toHaveTextContent(/sesión expiró/i)
  })

  it('limpia la caché de Apollo al cerrar sesión', async () => {
    const token = makeJwt(1800)

    const loginLink = new ApolloLink((operation) => {
      if (operation.operationName === 'Login') {
        return Observable.of({
          data: {
            login: {
              token,
              tokenType: 'bearer',
              user: TEST_USER,
            },
          },
        })
      }

      return Observable.of({ data: {} })
    })

    const client = new ApolloClient({
      link: loginLink,
      cache: new InMemoryCache(),
    })

    client.writeQuery({
      query: gql`
        query CachedValue {
          cachedValue
        }
      `,
      data: { cachedValue: 'dato-de-la-sesión' },
    })

    expect(client.cache.extract()).toHaveProperty('ROOT_QUERY')

    const user = userEvent.setup()

    render(
      <ApolloProvider client={client}>
        <App />
      </ApolloProvider>,
    )

    await signIn(user)
    expect(
      await screen.findByText(/Autenticación correcta/i),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Cerrar sesión' }))

    await waitFor(() => {
      expect(client.cache.extract()).toEqual({})
    })
  })
})
