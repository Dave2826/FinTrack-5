import { ApolloLink, Observable, execute, gql } from '@apollo/client'
import { describe, expect, it } from 'vitest'
import { createAuthLink } from '../src/api/authLink'

const query = gql`
  query Ping {
    ping
  }
`

async function captureHeaders(
  getToken: () => string | null,
): Promise<Record<string, string> | undefined> {
  let captured: Record<string, string> | undefined

  const terminal = new ApolloLink((operation) => {
    captured = operation.getContext().headers as
      | Record<string, string>
      | undefined
    return Observable.of({ data: { ping: 'pong' } })
  })

  const link = createAuthLink(getToken).concat(terminal)

  await new Promise<void>((resolve, reject) => {
    execute(link, { query }).subscribe({
      next: () => undefined,
      error: reject,
      complete: resolve,
    })
  })

  return captured
}

describe('authLink', () => {
  it('agrega la cabecera Bearer cuando existe token', async () => {
    const headers = await captureHeaders(() => 'token-de-prueba')

    expect(headers?.authorization).toBe('Bearer token-de-prueba')
  })

  it('no agrega autorización cuando no existe token', async () => {
    const headers = await captureHeaders(() => null)

    expect(headers).toBeUndefined()
  })

  it('lee el token en cada operación, no al construir el link', async () => {
    let currentToken: string | null = null
    const getToken = () => currentToken

    const first = await captureHeaders(getToken)
    expect(first).toBeUndefined()

    currentToken = 'token-dinamico'
    const second = await captureHeaders(getToken)

    expect(second?.authorization).toBe('Bearer token-dinamico')
  })
})
