import { useApolloClient, useMutation } from '@apollo/client'
import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { LOGIN_MUTATION } from '../api/operations/login'
import type {
  AuthUser,
  LoginInput,
  LoginResult,
  LoginVariables,
} from '../types/auth'
import { AuthError, toAuthError } from './authErrors'
import { AuthContext } from './context'
import type { AuthContextValue, SessionEndReason } from './context'
import { getTokenExpirationMs, isTokenExpired } from './jwt'
import { tokenStore } from './tokenStore'

interface Session {
  user: AuthUser
  expiresAt: number | null
}

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const client = useApolloClient()
  const [session, setSession] = useState<Session | null>(null)
  const [sessionEndReason, setSessionEndReason] =
    useState<SessionEndReason>(null)
  const [loginMutation] = useMutation<LoginResult, LoginVariables>(
    LOGIN_MUTATION,
  )

  const logout = useCallback(
    async (reason: 'manual' | 'expired' = 'manual') => {
      tokenStore.clear()
      setSession(null)
      setSessionEndReason(reason)

      try {
        // La caché contiene datos de la sesión anterior; no debe reutilizarse.
        await client.clearStore()
      } catch {
        // Si el cliente ya no está disponible, la sesión local ya quedó limpia.
      }
    },
    [client],
  )

  const login = useCallback(
    async (input: LoginInput) => {
      setSessionEndReason(null)

      try {
        const result = await loginMutation({ variables: { input } })
        const payload = result.data?.login

        if (!payload || typeof payload.token !== 'string' || !payload.token) {
          throw new AuthError(
            'invalid-response',
            'La respuesta de autenticación está incompleta.',
          )
        }

        if (isTokenExpired(payload.token)) {
          tokenStore.clear()
          throw new AuthError(
            'expired',
            'El token recibido ya no es válido.',
          )
        }

        tokenStore.set(payload.token)
        setSession({
          user: payload.user,
          expiresAt: getTokenExpirationMs(payload.token),
        })
      } catch (error) {
        throw toAuthError(error)
      }
    },
    [loginMutation],
  )

  // Si el token se limpia desde fuera (por ejemplo, un futuro enlace de
  // errores), la interfaz vuelve al login.
  useEffect(() => {
    return tokenStore.subscribe((token) => {
      if (token === null) {
        setSession(null)
      }
    })
  }, [])

  // Cierre de sesión automático cuando vence `exp`. Es solo control de
  // interfaz: el backend sigue validando la firma y la expiración.
  useEffect(() => {
    if (!session || session.expiresAt === null) {
      return
    }

    // Si el token ya venció (por ejemplo, por un ajuste del reloj), el
    // temporizador se programa para el siguiente tick. Así no se llama a
    // setState de forma síncrona dentro del efecto.
    const delay = Math.max(session.expiresAt - Date.now(), 0)

    const timer = setTimeout(() => {
      void logout('expired')
    }, delay)

    return () => {
      clearTimeout(timer)
    }
  }, [session, logout])

  const value = useMemo<AuthContextValue>(
    () => ({
      status: session ? 'authenticated' : 'anonymous',
      user: session?.user ?? null,
      expiresAt: session?.expiresAt ?? null,
      sessionEndReason,
      login,
      logout,
    }),
    [session, sessionEndReason, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
