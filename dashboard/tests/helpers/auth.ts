import type { MockedResponse } from '@apollo/client/testing'
import { LOGIN_MUTATION } from '../../src/api/operations/login'
import type { AuthUser } from '../../src/types/auth'

export const TEST_USER: AuthUser = {
  id: '1',
  name: 'Admin A',
  email: 'admin_a@test.local',
}

function encodeSegment(value: unknown): string {
  return btoa(JSON.stringify(value))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')
}

/**
 * Construye un JWT de prueba con `exp` relativo a ahora.
 * La firma es ficticia: solo se usa para leer el payload en la interfaz.
 */
export function makeJwt(expiresInSeconds: number): string {
  const header = { alg: 'HS256', typ: 'JWT' }
  const payload = {
    companyUserId: 1,
    companyId: 11,
    exp: Math.floor(Date.now() / 1000) + expiresInSeconds,
  }

  return `${encodeSegment(header)}.${encodeSegment(payload)}.firma-de-prueba`
}

interface LoginMockOptions {
  email: string
  password: string
  token: string
  user?: AuthUser
  delay?: number
}

export function loginMock({
  email,
  password,
  token,
  user = TEST_USER,
  delay,
}: LoginMockOptions): MockedResponse {
  return {
    request: {
      query: LOGIN_MUTATION,
      variables: { input: { email, password } },
    },
    result: {
      data: {
        login: {
          token,
          tokenType: 'bearer',
          user,
        },
      },
    },
    ...(delay === undefined ? {} : { delay }),
  }
}
