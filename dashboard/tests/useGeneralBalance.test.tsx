import {
  ApolloClient,
  ApolloLink,
  ApolloProvider,
  InMemoryCache,
  Observable,
} from '@apollo/client'
import type { FetchResult, NormalizedCacheObject } from '@apollo/client'
import { MockedProvider } from '@apollo/client/testing'
import type { MockedResponse } from '@apollo/client/testing'
import { act, renderHook, waitFor } from '@testing-library/react'
import { GraphQLError } from 'graphql'
import { useMemo } from 'react'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { GENERAL_BALANCE_QUERY } from '../src/api/operations/generalBalance'
import { AuthContext } from '../src/auth/context'
import type { AuthContextValue, SessionStatus } from '../src/auth/context'
import { useGeneralBalance } from '../src/hooks/useGeneralBalance'
import type { DateRange } from '../src/lib/dateRange'
import type { GeneralBalance } from '../src/types/balance'
import { TEST_USER } from './helpers/auth'

const FROM = '2026-11-01'
const TO = '2026-11-10'

const BALANCE: GeneralBalance = {
  companyId: '11',
  fromDate: FROM,
  toDate: TO,
  openingBalance: '0.00',
  totalIncome: '1531.00',
  totalExpense: '300.00',
  profit: '1231.00',
  closingBalance: '1231.00',
  accountsInRed: 0,
  isInRed: false,
  currency: 'MXN',
  accounts: [
    {
      accountId: '34',
      accountName: 'Cuenta Alpha Pruebas',
      isActive: true,
      openingBalance: '0.00',
      totalIncome: '1531.00',
      totalExpense: '300.00',
      profit: '1231.00',
      closingBalance: '1231.00',
      isInRed: false,
      currency: 'MXN',
    },
  ],
}

function balanceMock(
  fromDate: string,
  toDate: string,
  balance: GeneralBalance,
): MockedResponse {
  return {
    request: {
      query: GENERAL_BALANCE_QUERY,
      variables: { fromDate, toDate },
    },
    result: { data: { generalBalance: balance } },
  }
}

function graphQLErrorMock(
  fromDate: string,
  toDate: string,
  message: string,
): MockedResponse {
  return {
    request: {
      query: GENERAL_BALANCE_QUERY,
      variables: { fromDate, toDate },
    },
    result: { errors: [new GraphQLError(message)] },
  }
}

interface AuthWrapperProps {
  status: SessionStatus
  logout?: () => Promise<void>
  children: ReactNode
}

function AuthWrapper({ status, logout, children }: AuthWrapperProps) {
  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user: status === 'authenticated' ? TEST_USER : null,
      expiresAt: null,
      sessionEndReason: null,
      login: async () => undefined,
      logout: logout ?? (async () => undefined),
    }),
    [status, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

function mockedWrapper(
  status: SessionStatus,
  mocks: readonly MockedResponse[],
  logout?: () => Promise<void>,
) {
  const mockList = [...mocks]

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <MockedProvider mocks={mockList} addTypename={false}>
        <AuthWrapper status={status} logout={logout}>
          {children}
        </AuthWrapper>
      </MockedProvider>
    )
  }
}

function clientWrapper(
  client: ApolloClient<NormalizedCacheObject>,
  status: SessionStatus,
  logout?: () => Promise<void>,
) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <ApolloProvider client={client}>
        <AuthWrapper status={status} logout={logout}>
          {children}
        </AuthWrapper>
      </ApolloProvider>
    )
  }
}

function createClient(
  onRequest: (variables: Record<string, unknown>) => void,
  balance: GeneralBalance = BALANCE,
): ApolloClient<NormalizedCacheObject> {
  const link = new ApolloLink((operation) => {
    onRequest(operation.variables as Record<string, unknown>)

    return new Observable<FetchResult>((observer) => {
      const timer = setTimeout(() => {
        observer.next({ data: { generalBalance: balance } })
        observer.complete()
      }, 0)

      return () => {
        clearTimeout(timer)
      }
    })
  })

  return new ApolloClient({ link, cache: new InMemoryCache() })
}

describe('useGeneralBalance', () => {
  it('consulta el balance y expone los datos', async () => {
    const { result } = renderHook(
      () => useGeneralBalance({ fromDate: FROM, toDate: TO }),
      {
        wrapper: mockedWrapper('authenticated', [
          balanceMock(FROM, TO, BALANCE),
        ]),
      },
    )

    await waitFor(() => {
      expect(result.current.balance).toEqual(BALANCE)
    })

    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBeNull()
    expect(result.current.isRangeValid).toBe(true)
    expect(result.current.rangeError).toBeNull()
  })

  it('envía exclusivamente fromDate y toDate', async () => {
    const captured: Record<string, unknown>[] = []
    const client = createClient((variables) => {
      captured.push(variables)
    })

    const { result } = renderHook(
      () => useGeneralBalance({ fromDate: FROM, toDate: TO }),
      { wrapper: clientWrapper(client, 'authenticated') },
    )

    await waitFor(() => {
      expect(result.current.balance).toEqual(BALANCE)
    })

    expect(captured).toHaveLength(1)
    expect(captured[0]).toEqual({ fromDate: FROM, toDate: TO })
    expect(Object.keys(captured[0])).toEqual(['fromDate', 'toDate'])
  })

  it('expone el estado de carga inicial', async () => {
    const { result } = renderHook(
      () => useGeneralBalance({ fromDate: FROM, toDate: TO }),
      {
        wrapper: mockedWrapper('authenticated', [
          balanceMock(FROM, TO, BALANCE),
        ]),
      },
    )

    expect(result.current.loading).toBe(true)
    expect(result.current.balance).toBeNull()
    expect(result.current.error).toBeNull()
    expect(result.current.isRefetching).toBe(false)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })
  })

  it('clasifica un error de red', async () => {
    const mock: MockedResponse = {
      request: {
        query: GENERAL_BALANCE_QUERY,
        variables: { fromDate: FROM, toDate: TO },
      },
      error: new Error('offline'),
    }

    const { result } = renderHook(
      () => useGeneralBalance({ fromDate: FROM, toDate: TO }),
      { wrapper: mockedWrapper('authenticated', [mock]) },
    )

    await waitFor(() => {
      expect(result.current.error?.kind).toBe('network')
    })

    expect(result.current.loading).toBe(false)
    expect(result.current.balance).toBeNull()
  })

  it.each([
    ['Usuario no autenticado', 'unauthenticated'],
    ['Token inválido o expirado', 'expired'],
    ['El rol no tiene el permiso transactions.read', 'forbidden'],
    ['fromDate no puede ser posterior a toDate', 'invalid-dates'],
  ] as const)(
    'clasifica el error GraphQL "%s" como %s',
    async (message, kind) => {
      const { result } = renderHook(
        () => useGeneralBalance({ fromDate: FROM, toDate: TO }),
        {
          wrapper: mockedWrapper('authenticated', [
            graphQLErrorMock(FROM, TO, message),
          ]),
        },
      )

      await waitFor(() => {
        expect(result.current.error?.kind).toBe(kind)
      })
    },
  )

  it('no cierra la sesión ante un error de permisos', async () => {
    const logout = vi.fn(async () => undefined)

    const { result } = renderHook(
      () => useGeneralBalance({ fromDate: FROM, toDate: TO }),
      {
        wrapper: mockedWrapper(
          'authenticated',
          [
            graphQLErrorMock(
              FROM,
              TO,
              'El rol no tiene el permiso transactions.read',
            ),
          ],
          logout,
        ),
      },
    )

    await waitFor(() => {
      expect(result.current.error?.kind).toBe('forbidden')
    })

    expect(logout).not.toHaveBeenCalled()
  })

  it('omite la consulta sin sesión autenticada', () => {
    let calls = 0
    const client = createClient(() => {
      calls += 1
    })

    const { result } = renderHook(
      () => useGeneralBalance({ fromDate: FROM, toDate: TO }),
      { wrapper: clientWrapper(client, 'anonymous') },
    )

    expect(calls).toBe(0)
    expect(result.current.loading).toBe(false)
    expect(result.current.balance).toBeNull()
    expect(result.current.error).toBeNull()
  })

  it('omite la consulta con un rango inválido', () => {
    let calls = 0
    const client = createClient(() => {
      calls += 1
    })

    const { result } = renderHook(
      () =>
        useGeneralBalance({
          fromDate: '2026-12-31',
          toDate: '2026-01-01',
        }),
      { wrapper: clientWrapper(client, 'authenticated') },
    )

    expect(calls).toBe(0)
    expect(result.current.isRangeValid).toBe(false)
    expect(result.current.rangeError?.reason).toBe('from-after-to')
    expect(result.current.loading).toBe(false)
    expect(result.current.balance).toBeNull()
  })

  it('omite la consulta cuando falta una fecha', () => {
    let calls = 0
    const client = createClient(() => {
      calls += 1
    })

    const { result } = renderHook(
      () => useGeneralBalance({ fromDate: '', toDate: TO }),
      { wrapper: clientWrapper(client, 'authenticated') },
    )

    expect(calls).toBe(0)
    expect(result.current.isRangeValid).toBe(false)
    expect(result.current.rangeError?.reason).toBe('missing-from')
  })

  it('permite refetch manual y actualiza los datos', async () => {
    const updated: GeneralBalance = { ...BALANCE, totalIncome: '99.00' }
    const mocks = [
      balanceMock(FROM, TO, BALANCE),
      balanceMock(FROM, TO, updated),
    ]

    const { result } = renderHook(
      () => useGeneralBalance({ fromDate: FROM, toDate: TO }),
      { wrapper: mockedWrapper('authenticated', mocks) },
    )

    await waitFor(() => {
      expect(result.current.balance?.totalIncome).toBe('1531.00')
    })

    await act(async () => {
      await result.current.refetch()
    })

    await waitFor(() => {
      expect(result.current.balance?.totalIncome).toBe('99.00')
    })
  })

  it('vuelve a consultar cuando cambia el rango', async () => {
    const october: GeneralBalance = {
      ...BALANCE,
      fromDate: '2026-10-01',
      toDate: '2026-10-31',
      totalIncome: '500.00',
    }
    const mocks = [
      balanceMock(FROM, TO, BALANCE),
      balanceMock('2026-10-01', '2026-10-31', october),
    ]

    const { result, rerender } = renderHook(
      ({ range }: { range: DateRange }) => useGeneralBalance(range),
      {
        initialProps: { range: { fromDate: FROM, toDate: TO } },
        wrapper: mockedWrapper('authenticated', mocks),
      },
    )

    await waitFor(() => {
      expect(result.current.balance?.fromDate).toBe(FROM)
    })

    rerender({ range: { fromDate: '2026-10-01', toDate: '2026-10-31' } })

    await waitFor(() => {
      expect(result.current.balance?.fromDate).toBe('2026-10-01')
    })

    expect(result.current.balance?.totalIncome).toBe('500.00')
  })
})
