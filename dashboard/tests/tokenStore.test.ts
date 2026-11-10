import { beforeEach, describe, expect, it, vi } from 'vitest'
import { tokenStore } from '../src/auth/tokenStore'

describe('tokenStore', () => {
  beforeEach(() => {
    tokenStore.clear()
  })

  it('inicia sin token', () => {
    expect(tokenStore.get()).toBeNull()
  })

  it('guarda y consulta el token en memoria', () => {
    tokenStore.set('token-de-prueba')

    expect(tokenStore.get()).toBe('token-de-prueba')
  })

  it('limpia el token', () => {
    tokenStore.set('token-de-prueba')
    tokenStore.clear()

    expect(tokenStore.get()).toBeNull()
  })

  it('notifica a los suscriptores y permite desuscribirse', () => {
    const listener = vi.fn()
    const unsubscribe = tokenStore.subscribe(listener)

    tokenStore.set('token-de-prueba')
    expect(listener).toHaveBeenLastCalledWith('token-de-prueba')

    tokenStore.clear()
    expect(listener).toHaveBeenLastCalledWith(null)
    expect(listener).toHaveBeenCalledTimes(2)

    unsubscribe()
    tokenStore.set('otro-token')

    expect(listener).toHaveBeenCalledTimes(2)
  })

  it('no persiste el token en almacenamiento del navegador', () => {
    tokenStore.set('token-de-prueba')

    expect(localStorage.length).toBe(0)
    expect(sessionStorage.length).toBe(0)
    expect(document.cookie).toBe('')
  })

  it('rechaza tokens vacíos', () => {
    expect(() => tokenStore.set('')).toThrow()
  })
})
