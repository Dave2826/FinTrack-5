/**
 * Almacén del token JWT.
 *
 * El token vive exclusivamente en memoria: no se usa localStorage,
 * sessionStorage, cookies ni IndexedDB. Al recargar la página el módulo se
 * reinicia y la sesión desaparece.
 */

export type TokenListener = (token: string | null) => void

let currentToken: string | null = null
const listeners = new Set<TokenListener>()

function notify(): void {
  for (const listener of listeners) {
    listener(currentToken)
  }
}

export const tokenStore = {
  get(): string | null {
    return currentToken
  },

  set(token: string): void {
    if (typeof token !== 'string' || token.length === 0) {
      throw new Error('tokenStore.set requiere un token no vacío')
    }

    currentToken = token
    notify()
  },

  clear(): void {
    currentToken = null
    notify()
  },

  subscribe(listener: TokenListener): () => void {
    listeners.add(listener)

    return () => {
      listeners.delete(listener)
    }
  },
}
