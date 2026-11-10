import type { MockedResponse } from '@apollo/client/testing'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { GENERAL_BALANCE_QUERY } from '../src/api/operations/generalBalance'
import { AccountsTable } from '../src/features/dashboard/components/AccountsTable'
import { getDefaultUtcMonthRange } from '../src/lib/dateRange'
import type { DateRange } from '../src/lib/dateRange'
import type { AccountBalance, GeneralBalance } from '../src/types/balance'
import { loginMock, makeJwt } from './helpers/auth'
import { renderApp } from './helpers/renderApp'

const EMAIL = 'admin_a@test.local'
const PASSWORD = 'clave-correcta'
const TABLE_NAME = 'Cuentas del balance del periodo'

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
  accounts: AccountBalance[],
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
    accounts,
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

function periodText(range: DateRange): string {
  return `Periodo consultado: ${range.fromDate} a ${range.toDate} (UTC) · Importes en MXN`
}

async function signIn(user: UserEventApi) {
  await user.type(screen.getByLabelText('Correo electrónico'), EMAIL)
  await user.type(screen.getByLabelText('Contraseña'), PASSWORD)
  await user.click(screen.getByRole('button', { name: 'Entrar' }))
}

describe('AccountsTable', () => {
  it('renderiza una cuenta con su nombre', () => {
    render(
      <AccountsTable
        accounts={[makeAccount({ accountName: 'Cuenta Principal' })]}
      />,
    )

    expect(
      screen.getByRole('table', { name: TABLE_NAME }),
    ).toBeInTheDocument()
    expect(screen.getByText('Cuenta Principal')).toBeInTheDocument()
  })

  it('renderiza varias cuentas', () => {
    render(
      <AccountsTable
        accounts={[
          makeAccount({ accountId: '1', accountName: 'Cuenta Alpha' }),
          makeAccount({ accountId: '2', accountName: 'Cuenta Beta' }),
          makeAccount({ accountId: '3', accountName: 'Cuenta Gamma' }),
        ]}
      />,
    )

    expect(screen.getByText('Cuenta Alpha')).toBeInTheDocument()
    expect(screen.getByText('Cuenta Beta')).toBeInTheDocument()
    expect(screen.getByText('Cuenta Gamma')).toBeInTheDocument()
  })

  it('presenta los cinco importes de la cuenta', () => {
    render(
      <AccountsTable
        accounts={[
          makeAccount({
            openingBalance: '1000',
            totalIncome: '1531.5',
            totalExpense: '300',
            profit: '1231.5',
            closingBalance: '2231.5',
          }),
        ]}
      />,
    )

    expect(screen.getByText('$1,000.00')).toBeInTheDocument()
    expect(screen.getByText('$1,531.50')).toBeInTheDocument()
    expect(screen.getByText('$300.00')).toBeInTheDocument()
    expect(screen.getByText('$1,231.50')).toBeInTheDocument()
    expect(screen.getByText('$2,231.50')).toBeInTheDocument()
  })

  it('formatea los importes en MXN con agrupación y dos decimales', () => {
    render(
      <AccountsTable
        accounts={[
          makeAccount({
            openingBalance: '1234567.5',
            totalIncome: '0.5',
            totalExpense: '1000000',
            profit: '-2500.25',
            closingBalance: '987654.75',
          }),
        ]}
      />,
    )

    expect(screen.getByText('$1,234,567.50')).toBeInTheDocument()
    expect(screen.getByText('$0.50')).toBeInTheDocument()
    expect(screen.getByText('$1,000,000.00')).toBeInTheDocument()
    expect(screen.getByText('-$2,500.25')).toBeInTheDocument()
    expect(screen.getByText('$987,654.75')).toBeInTheDocument()
  })

  it('identifica una cuenta activa', () => {
    render(<AccountsTable accounts={[makeAccount({ isActive: true })]} />)

    expect(screen.getByText('Activa')).toBeInTheDocument()
    expect(screen.queryByText('Inactiva')).not.toBeInTheDocument()
  })

  it('identifica una cuenta inactiva', () => {
    render(<AccountsTable accounts={[makeAccount({ isActive: false })]} />)

    expect(screen.getByText('Inactiva')).toBeInTheDocument()
    expect(screen.queryByText('Activa')).not.toBeInTheDocument()
  })

  it('identifica una cuenta en riesgo', () => {
    render(<AccountsTable accounts={[makeAccount({ isInRed: true })]} />)

    expect(screen.getByText('En riesgo')).toBeInTheDocument()
    expect(screen.queryByText('Sin riesgo')).not.toBeInTheDocument()
  })

  it('representa una cuenta activa y en riesgo', () => {
    render(
      <AccountsTable
        accounts={[makeAccount({ isActive: true, isInRed: true })]}
      />,
    )

    expect(screen.getByText('Activa')).toBeInTheDocument()
    expect(screen.getByText('En riesgo')).toBeInTheDocument()
  })

  it('representa una cuenta inactiva sin riesgo', () => {
    render(
      <AccountsTable
        accounts={[makeAccount({ isActive: false, isInRed: false })]}
      />,
    )

    expect(screen.getByText('Inactiva')).toBeInTheDocument()
    expect(screen.getByText('Sin riesgo')).toBeInTheDocument()
  })

  it('muestra una cuenta sin movimientos con valores reales en cero', () => {
    render(
      <AccountsTable
        accounts={[
          makeAccount({
            openingBalance: '0.00',
            totalIncome: '0.00',
            totalExpense: '0.00',
            profit: '0.00',
            closingBalance: '0.00',
          }),
        ]}
      />,
    )

    expect(screen.getByText('Cuenta Principal')).toBeInTheDocument()
    expect(screen.getAllByText('$0.00')).toHaveLength(5)
  })

  it('muestra un estado vacío informativo cuando no hay cuentas', () => {
    render(<AccountsTable accounts={[]} />)

    expect(
      screen.getByText(
        'Esta empresa no tiene cuentas registradas para el periodo consultado.',
      ),
    ).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('conserva todas las cuentas recibidas, incluidas las inactivas', () => {
    const accounts = [
      makeAccount({ accountId: '1', accountName: 'Cuenta Alpha' }),
      makeAccount({
        accountId: '2',
        accountName: 'Cuenta Beta',
        isActive: false,
      }),
      makeAccount({
        accountId: '3',
        accountName: 'Cuenta Gamma',
        isInRed: true,
      }),
      makeAccount({
        accountId: '4',
        accountName: 'Cuenta Delta',
        isActive: false,
        isInRed: true,
      }),
    ]

    render(<AccountsTable accounts={accounts} />)

    for (const account of accounts) {
      expect(screen.getByText(account.accountName)).toBeInTheDocument()
    }

    expect(screen.getAllByRole('row')).toHaveLength(accounts.length + 1)
  })

  it('presenta los importes recibidos sin recalcularlos', () => {
    render(
      <AccountsTable
        accounts={[
          makeAccount({
            openingBalance: '10.00',
            totalIncome: '99.00',
            totalExpense: '1.00',
            profit: '500.00',
            closingBalance: '777.00',
          }),
        ]}
      />,
    )

    expect(screen.getByText('$10.00')).toBeInTheDocument()
    expect(screen.getByText('$99.00')).toBeInTheDocument()
    expect(screen.getByText('$1.00')).toBeInTheDocument()
    expect(screen.getByText('$500.00')).toBeInTheDocument()
    expect(screen.getByText('$777.00')).toBeInTheDocument()

    expect(screen.queryByText('$98.00')).not.toBeInTheDocument()
    expect(screen.queryByText('$510.00')).not.toBeInTheDocument()
  })

  it('se integra con el dashboard junto al resumen y el filtro', async () => {
    const user = userEvent.setup()
    const range = getDefaultUtcMonthRange()
    const balance = makeBalance(range, [
      makeAccount({ accountId: '1', accountName: 'Cuenta Alpha Pruebas' }),
      makeAccount({
        accountId: '2',
        accountName: 'Cuenta Beta Inactiva',
        isActive: false,
      }),
    ])

    renderApp([
      loginMock({ email: EMAIL, password: PASSWORD, token: makeJwt(1800) }),
      balanceMock(range, balance),
    ])

    await signIn(user)

    const table = await screen.findByRole('table', { name: TABLE_NAME })

    expect(
      within(table).getByText('Cuenta Alpha Pruebas'),
    ).toBeInTheDocument()
    expect(
      within(table).getByText('Cuenta Beta Inactiva'),
    ).toBeInTheDocument()
    expect(within(table).getByText('Inactiva')).toBeInTheDocument()
    expect(screen.getByText(periodText(range))).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Consultar' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Cerrar sesión' }),
    ).toBeInTheDocument()
  })

  it('no muestra cuentas ni importes ficticios durante la carga', async () => {
    const user = userEvent.setup()
    const range = getDefaultUtcMonthRange()
    const balance = makeBalance(range, [
      makeAccount({ accountName: 'Cuenta Alpha Pruebas' }),
    ])

    renderApp([
      loginMock({ email: EMAIL, password: PASSWORD, token: makeJwt(1800) }),
      balanceMock(range, balance, 300),
    ])

    await signIn(user)
    await screen.findByText('Cargando balance…')

    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(
      screen.queryByText('Cuenta Alpha Pruebas'),
    ).not.toBeInTheDocument()
    expect(screen.queryByText(/\$\s?\d/)).not.toBeInTheDocument()

    const table = await screen.findByRole('table', { name: TABLE_NAME })

    expect(
      within(table).getByText('Cuenta Alpha Pruebas'),
    ).toBeInTheDocument()
  })
})
