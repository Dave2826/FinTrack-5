import { describe, expect, it } from 'vitest'
import {
  decodeJwtPayload,
  getTokenExpirationMs,
  isTokenExpired,
} from '../src/auth/jwt'
import { makeJwt } from './helpers/auth'

describe('jwt', () => {
  it('lee el payload y la expiración', () => {
    const token = makeJwt(600)
    const payload = decodeJwtPayload(token)

    expect(payload?.companyId).toBe(11)
    expect(typeof payload?.exp).toBe('number')
    expect(getTokenExpirationMs(token)).toBe((payload?.exp as number) * 1000)
  })

  it('considera expirado un token vencido', () => {
    const token = makeJwt(-60)

    expect(isTokenExpired(token)).toBe(true)
  })

  it('considera vigente un token futuro', () => {
    const token = makeJwt(600)

    expect(isTokenExpired(token)).toBe(false)
  })

  it('no falla con tokens malformados', () => {
    expect(decodeJwtPayload('no-es-un-jwt')).toBeNull()
    expect(getTokenExpirationMs('a.b.c')).toBeNull()
    expect(isTokenExpired('no-es-un-jwt')).toBe(true)
  })
})
