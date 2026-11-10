import type { MockedResponse } from '@apollo/client/testing'
import { fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { GraphQLError } from 'graphql'
import { describe, expect, it, vi } from 'vitest'
import { GENERAL_BALANCE_QUERY } from '../src/api/operations/generalBalance'
import { AccountsTable } from '../src/features/dashboard/components/AccountsTable'
import { DateRangeFilter } from '../src/features/dashboard/components/DateRangeFilter'
import { getDefaultUtcMonthRange } from '../src/lib/dateRange'
import type { DateRange } from '../src/lib/dateRange'
import type { AccountBalance, GeneralBalance } from '../src/types/balance'
import { loginMock, makeJwt } from './helpers/auth'
import { renderApp } from './helpers/renderApp'

const EMAIL = 'admin_a@test.local'
const PASSWORD = 'clave-correcta'
const TABLE_NAME = 'Cuentas del balance del periodo'
const DATE_ERROR_ID = 'dashboard-date-range-error'

type UserEventApi = ReturnType<typeof userEvent.setup>

function makeAccount(
  overrides: Partial<AccountBalance> = {},
): AccountBalance {
  return {
    accountId: '1',
    accountName: 'Cuenta Principal',
    isActive: true,
    openingBalance: '0.00',
    totalIncome: '1531.00',
    totalExpense: '300.00',
    profit: '1231.00',
    closingBalance: '1231.00',
    isInRed: false,
    currency: 'MXN',
    ...overrides,
  }
}

function makeBalance(
  range: DateRange,
  overrides: Partial<GeneralBalance> = {},
): GeneralBalance {
  return {
    companyId: '11',
    fromDate: range.fromDate,
    toDate: range.toDate,
    openingBalance: '0.00',
    totalIncome: '1531.00',
    totalExpense: '300.00',
    profit: '1231.00',
    closingBalance: '1231.00',
    accountsInRed: 0,
    isInRed: false,
    currency: 'MXN',
    accounts: [],
    ...overrides,
  }
}

function balanceMock(
  range: DateRange,
  balance: GeneralBalance,
  delay?: number,
): MockedResponse {
  return {
    request: {
      query: GENERAL_BALANCE_QUERY,
      variables: { fromDate: range.fromDate, toDate: range.toDate },
    },
    result: { data: { generalBalance: balance } },
    ...(delay === undefined ? {} : { delay }),
  }
}

function networkErrorMock(range: DateRange): MockedResponse {
  return {
    request: {
      query: GENERAL_BALANCE_QUERY,
      variables: { fromDate: range.fromDate, toDate: range.toDate },
    },
    error: new Error('offline'),
  }
}

function graphQLErrorMock(range: DateRange, message: string): MockedResponse {
  return {
    request: {
      query: GENERAL_BALANCE_QUERY,
      variables: { fromDate: range.fromDate, toDate: range.toDate },
    },
    result: { errors: [new GraphQLError(message)] },
  }
}

function loginOnly(): MockedResponse[] {
  return [loginMock({ email: EMAIL, password: PASSWORD, token: makeJwt(1800) })]
}

async function signIn(user: UserEventApi) {
  await user.type(screen.getByLabelText('Correo electrónico'), EMAIL)
  await user.type(screen.getByLabelText('Contraseña'), PASSWORD)
  await user.click(screen.getByRole('button', { name: 'Entrar' }))
}

describe('dashboard: accesibilidad y mensajes de estado', () => {
  it('expone el filtro con nombre accesible y orden de tabulación lógico', async () => {
    const user = userEvent.setup()
    const range = getDefaultUtcMonthRange()

    renderApp([...loginOnly(), balanceMock(range, makeBalance(range))])

    await signIn(user)

    expect(
      await screen.findByRole('form', { name: 'Rango de fechas' }),
    ).toBeInTheDocument()

    const fromInput = screen.getByLabelText('Fecha inicial')
    fromInput.focus()
    expect(fromInput).toHaveFocus()

    await user.tab()
    expect(screen.getByLabelText('Fecha final')).toHaveFocus()

    await user.tab()
    expect(screen.getByRole('button', { name: 'Consultar' })).toHaveFocus()
  })

  it('lleva el foco al campo inválido y describe el error solo en ese campo', async () => {
    const user = userEvent.setup()
    const onApply = vi.fn()

    render(
      <DateRangeFilter
        range={{ fromDate: '2026-01-01', toDate: '2026-01-31' }}
        onApply={onApply}
      />,
    )

    fireEvent.change(screen.getByLabelText('Fecha final'), {
      target: { value: '' },
    })
    await user.click(screen.getByRole('button', { name: 'Consultar' }))

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Selecciona la fecha final.',
    )

    const fromInput = screen.getByLabelText('Fecha inicial')
    const toInput = screen.getByLabelText('Fecha final')

    expect(toInput).toHaveFocus()
    expect(toInput).toHaveAttribute('aria-invalid', 'true')
    expect(toInput).toHaveAttribute('aria-describedby', DATE_ERROR_ID)
    expect(fromInput).not.toHaveAttribute('aria-invalid')
    expect(fromInput).not.toHaveAttribute('aria-describedby')
    expect(onApply).not.toHaveBeenCalled()

    fireEvent.change(fromInput, { target: { value: '2026-01-02' } })

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(toInput).not.toHaveAttribute('aria-invalid')
    expect(toInput).not.toHaveAttribute('aria-describedby')
  })

  it('no ofrece reintento cuando el backend rechaza el periodo', async () => {
    const user = userEvent.setup()
    const range = getDefaultUtcMonthRange()

    renderApp([
      ...loginOnly(),
      graphQLErrorMock(range, 'El argumento fromDate no es una fecha válida'),
    ])

    await signIn(user)

    expect(
      await screen.findByText(
        'El periodo seleccionado no es válido. Revisa las fechas e inténtalo de nuevo.',
      ),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Reintentar' }),
    ).not.toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Cerrar sesión' }),
    ).toBeInTheDocument()
  })

  it('permite reintentar una actualización fallida y mueve el foco al título', async () => {
    const user = userEvent.setup()
    const range = getDefaultUtcMonthRange()
    const updated = makeBalance(range, { totalIncome: '2000.00' })

    renderApp([
      ...loginOnly(),
      balanceMock(range, makeBalance(range)),
      networkErrorMock(range),
      balanceMock(range, updated),
    ])

    await signIn(user)
    await screen.findByText('$1,531.00')

    await user.click(screen.getByRole('button', { name: 'Actualizar' }))

    expect(
      await screen.findByText(/No se pudo actualizar el balance/),
    ).toHaveTextContent(
      `Se muestran los datos del periodo ${range.fromDate} a ${range.toDate} (UTC).`,
    )
    expect(screen.getByText('$1,531.00')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Reintentar' }),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Reintentar' }))

    expect(await screen.findByText('$2,000.00')).toBeInTheDocument()
    expect(
      screen.queryByText(/No se pudo actualizar el balance/),
    ).not.toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'Resumen del balance' }),
    ).toHaveFocus()
  })

  it('informa que las cuentas no se pudieron cargar ante un error inicial', async () => {
    const user = userEvent.setup()
    const range = getDefaultUtcMonthRange()

    renderApp([...loginOnly(), networkErrorMock(range)])

    await signIn(user)

    expect(
      await screen.findByText('No se pudieron cargar las cuentas.'),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('region', { name: 'Detalle de cuentas' }),
    ).toHaveAttribute('aria-busy', 'false')
  })

  it('marca el panel de cuentas como ocupado mientras carga', async () => {
    const user = userEvent.setup()
    const range = getDefaultUtcMonthRange()
    const balance = makeBalance(range, { accounts: [makeAccount()] })

    renderApp([...loginOnly(), balanceMock(range, balance, 300)])

    await signIn(user)
    await screen.findByText('Cargando balance…')

    const accountsPanel = screen.getByRole('region', {
      name: 'Detalle de cuentas',
    })

    expect(accountsPanel).toHaveAttribute('aria-busy', 'true')

    expect(
      await screen.findByRole('table', { name: TABLE_NAME }),
    ).toBeInTheDocument()
    expect(accountsPanel).toHaveAttribute('aria-busy', 'false')
  })

  it('anuncia el estado vacío de cuentas mediante role status', () => {
    render(<AccountsTable accounts={[]} />)

    expect(screen.getByRole('status')).toHaveTextContent(
      'Esta empresa no tiene cuentas registradas para el periodo consultado.',
    )
  })

  it('asocia encabezados y celdas de la tabla con roles explícitos', () => {
    render(
      <AccountsTable
        accounts={[
          makeAccount({ accountId: '1', accountName: 'Cuenta Alpha' }),
          makeAccount({ accountId: '2', accountName: 'Cuenta Beta' }),
        ]}
      />,
    )

    const table = screen.getByRole('table', { name: TABLE_NAME })

    expect(within(table).getAllByRole('columnheader')).toHaveLength(7)
    expect(within(table).getAllByRole('rowheader')).toHaveLength(2)
    expect(within(table).getAllByRole('cell')).toHaveLength(12)
    expect(within(table).getByRole('rowheader', { name: 'Cuenta Alpha' }))
      .toBeInTheDocument()
  })
})
