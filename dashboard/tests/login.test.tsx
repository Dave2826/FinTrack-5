import { ApolloError } from '@apollo/client'
import type { MockedResponse } from '@apollo/client/testing'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { GraphQLError } from 'graphql'
import { describe, expect, it } from 'vitest'
import { LOGIN_MUTATION } from '../src/api/operations/login'
import { tokenStore } from '../src/auth/tokenStore'
import { loginMock, makeJwt } from './helpers/auth'
import { renderApp } from './helpers/renderApp'

const EMAIL = 'admin_a@test.local'

async function submitLogin(
  user: ReturnType<typeof userEvent.setup>,
  password: string,
) {
  await user.type(screen.getByLabelText('Correo electrónico'), EMAIL)
  await user.type(screen.getByLabelText('Contraseña'), password)
  await user.click(screen.getByRole('button', { name: 'Entrar' }))
}

describe('login', () => {
  it('inicia sesión con credenciales válidas y guarda el token en memoria', async () => {
    const token = makeJwt(1800)
    const user = userEvent.setup()

    renderApp([loginMock({ email: EMAIL, password: 'clave-correcta', token })])

    await submitLogin(user, 'clave-correcta')

    expect(
      await screen.findByText(/Autenticación correcta/i),
    ).toBeInTheDocument()
    expect(screen.getByText(EMAIL)).toBeInTheDocument()
    expect(tokenStore.get()).toBe(token)
  })

  it('muestra un error comprensible con credenciales incorrectas y conserva los datos', async () => {
    const errorMock: MockedResponse = {
      request: {
        query: LOGIN_MUTATION,
        variables: { input: { email: EMAIL, password: 'clave-incorrecta' } },
      },
      error: new ApolloError({
        graphQLErrors: [new GraphQLError('Credenciales inválidas')],
      }),
    }

    const user = userEvent.setup()
    renderApp([errorMock])

    await submitLogin(user, 'clave-incorrecta')

    expect(await screen.findByRole('alert')).toHaveTextContent(
      /correo o la contraseña no son correctos/i,
    )
    expect(screen.getByLabelText('Correo electrónico')).toHaveValue(EMAIL)
    expect(screen.getByLabelText('Contraseña')).toHaveValue('clave-incorrecta')
    expect(tokenStore.get()).toBeNull()
    expect(
      screen.queryByText(/Autenticación correcta/i),
    ).not.toBeInTheDocument()
  })

  it('muestra un error de conexión cuando no hay red', async () => {
    const errorMock: MockedResponse = {
      request: {
        query: LOGIN_MUTATION,
        variables: { input: { email: EMAIL, password: 'clave-correcta' } },
      },
      error: new ApolloError({ networkError: new Error('sin conexión') }),
    }

    const user = userEvent.setup()
    renderApp([errorMock])

    await submitLogin(user, 'clave-correcta')

    expect(await screen.findByRole('alert')).toHaveTextContent(
      /no se pudo conectar con el servidor/i,
    )
  })

  it('deshabilita el botón y los campos mientras procesa la solicitud', async () => {
    const token = makeJwt(1800)
    const user = userEvent.setup()

    renderApp([
      loginMock({ email: EMAIL, password: 'clave-correcta', token, delay: 150 }),
    ])

    await submitLogin(user, 'clave-correcta')

    const pendingButton = screen.getByRole('button', { name: /entrando/i })
    expect(pendingButton).toBeDisabled()
    expect(screen.getByLabelText('Correo electrónico')).toBeDisabled()
    expect(screen.getByLabelText('Contraseña')).toBeDisabled()

    expect(
      await screen.findByText(/Autenticación correcta/i),
    ).toBeInTheDocument()
  })

  it('valida los campos obligatorios antes de enviar', async () => {
    const user = userEvent.setup()
    renderApp([])

    await user.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(screen.getByText('El correo electrónico es obligatorio.')).toBeInTheDocument()
    expect(screen.getByText('La contraseña es obligatoria.')).toBeInTheDocument()
    expect(tokenStore.get()).toBeNull()
  })
})
