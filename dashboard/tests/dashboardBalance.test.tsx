import type { MockedResponse } from '@apollo/client/testing'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { GraphQLError } from 'graphql'
import { describe, expect, it, vi } from 'vitest'
import { GENERAL_BALANCE_QUERY } from '../src/api/operations/generalBalance'
import { BalanceSummary } from '../src/features/dashboard/components/BalanceSummary'
import { DateRangeFilter } from '../src/features/dashboard/components/DateRangeFilter'
import { getDefaultUtcMonthRange } from '../src/lib/dateRange'
import type { DateRange } from '../src/lib/dateRange'
import type { GeneralBalance } from '../src/types/balance'
import { loginMock, makeJwt } from './helpers/auth'
import { renderApp } from './helpers/renderApp'

const EMAIL = 'admin_a@test.local'
const PASSWORD = 'clave-correcta'

type UserEventApi = ReturnType<typeof userEvent.setup>

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

function periodText(range: DateRange): string {
  return `Periodo consultado: ${range.fromDate} a ${range.toDate} (UTC) · Importes en MXN`
}

async function signIn(user: UserEventApi) {
  await user.type(screen.getByLabelText('Correo electrónico'), EMAIL)
  await user.type(screen.getByLabelText('Contraseña'), PASSWORD)
  await user.click(screen.getByRole('button', { name: 'Entrar' }))
}

function setDate(label: string, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } })
}

async function submitRange(user: UserEventApi) {
  await user.click(screen.getByRole('button', { name: 'Consultar' }))
}

function loginOnly(): MockedResponse[] {
  return [loginMock({ email: EMAIL, password: PASSWORD, token: makeJwt(1800) })]
}

describe('dashboard: filtro de fechas y resumen financiero', () => {
  it('consulta el periodo UTC predeterminado del mes actual', async () => {
    const user = userEvent.setup()
    const range = getDefaultUtcMonthRange()

    renderApp([...loginOnly(), balanceMock(range, makeBalance(range))])

    await signIn(user)

    expect(await screen.findByText(periodText(range))).toBeInTheDocument()
    expect(screen.getByLabelText('Fecha inicial')).toHaveValue(range.fromDate)
    expect(screen.getByLabelText('Fecha final')).toHaveValue(range.toDate)
  })

  it('muestra los cinco indicadores del balance', async () => {
    const user = userEvent.setup()
    const range = getDefaultUtcMonthRange()

    renderApp([...loginOnly(), balanceMock(range, makeBalance(range))])

    await signIn(user)

    expect(await screen.findByText('Saldo inicial')).toBeInTheDocument()
    expect(screen.getByText('Ingresos')).toBeInTheDocument()
    expect(screen.getByText('Egresos')).toBeInTheDocument()
    expect(screen.getByText('Utilidad')).toBeInTheDocument()
    expect(screen.getByText('Saldo final')).toBeInTheDocument()
    expect(
      screen.getByRole('region', { name: 'Sin riesgo global' }),
    ).toBeInTheDocument()
    expect(screen.getByText('0 cuentas en números rojos')).toBeInTheDocument()
  })

  it('presenta los importes en MXN con dos decimales', async () => {
    const user = userEvent.setup()
    const range = getDefaultUtcMonthRange()
    const balance = makeBalance(range, {
      openingBalance: '1000',
      totalIncome: '1531.5',
      totalExpense: '300',
      profit: '1231.5',
      closingBalance: '2231.5',
    })

    renderApp([...loginOnly(), balanceMock(range, balance)])

    await signIn(user)

    expect(await screen.findByText('$1,000.00')).toBeInTheDocument()
    expect(screen.getByText('$1,531.50')).toBeInTheDocument()
    expect(screen.getByText('$300.00')).toBeInTheDocument()
    expect(screen.getByText('$1,231.50')).toBeInTheDocument()
    expect(screen.getByText('$2,231.50')).toBeInTheDocument()
  })

  it('consulta de nuevo al cambiar la fecha inicial', async () => {
    const user = userEvent.setup()
    const initial = getDefaultUtcMonthRange()
    const changed: DateRange = {
      fromDate: '2000-01-01',
      toDate: initial.toDate,
    }

    renderApp([
      ...loginOnly(),
      balanceMock(initial, makeBalance(initial)),
      balanceMock(changed, makeBalance(changed, { totalIncome: '10.00' })),
    ])

    await signIn(user)
    await screen.findByText('Saldo inicial')

    setDate('Fecha inicial', changed.fromDate)
    await submitRange(user)

    expect(await screen.findByText(periodText(changed))).toBeInTheDocument()
    expect(screen.getByText('$10.00')).toBeInTheDocument()
  })

  it('consulta de nuevo al cambiar la fecha final', async () => {
    const user = userEvent.setup()
    const initial = getDefaultUtcMonthRange()
    const first: DateRange = {
      fromDate: '2000-01-01',
      toDate: initial.toDate,
    }
    const second: DateRange = {
      fromDate: '2000-01-01',
      toDate: '2000-01-31',
    }

    renderApp([
      ...loginOnly(),
      balanceMock(initial, makeBalance(initial)),
      balanceMock(first, makeBalance(first)),
      balanceMock(second, makeBalance(second, { totalIncome: '20.00' })),
    ])

    await signIn(user)
    await screen.findByText('Saldo inicial')

    setDate('Fecha inicial', first.fromDate)
    await submitRange(user)
    await screen.findByText(periodText(first))

    setDate('Fecha final', second.toDate)
    await submitRange(user)

    expect(await screen.findByText(periodText(second))).toBeInTheDocument()
    expect(screen.getByText('$20.00')).toBeInTheDocument()
  })

  it('aplica un rango válido completo', async () => {
    const user = userEvent.setup()
    const initial = getDefaultUtcMonthRange()
    const range: DateRange = {
      fromDate: '2026-10-01',
      toDate: '2026-10-31',
    }

    renderApp([
      ...loginOnly(),
      balanceMock(initial, makeBalance(initial)),
      balanceMock(range, makeBalance(range, { totalIncome: '500.00' })),
    ])

    await signIn(user)
    await screen.findByText('Saldo inicial')

    setDate('Fecha inicial', range.fromDate)
    setDate('Fecha final', range.toDate)
    await submitRange(user)

    expect(await screen.findByText(periodText(range))).toBeInTheDocument()
    expect(screen.getByText('$500.00')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('permite seleccionar fechas iguales', async () => {
    const user = userEvent.setup()
    const initial = getDefaultUtcMonthRange()
    const range: DateRange = {
      fromDate: '2026-10-15',
      toDate: '2026-10-15',
    }

    renderApp([
      ...loginOnly(),
      balanceMock(initial, makeBalance(initial)),
      balanceMock(range, makeBalance(range, { totalIncome: '75.00' })),
    ])

    await signIn(user)
    await screen.findByText('Saldo inicial')

    setDate('Fecha inicial', range.fromDate)
    setDate('Fecha final', range.toDate)
    await submitRange(user)

    expect(await screen.findByText(periodText(range))).toBeInTheDocument()
    expect(screen.getByText('$75.00')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('rechaza un rango invertido con un mensaje claro', async () => {
    const user = userEvent.setup()
    const initial = getDefaultUtcMonthRange()

    renderApp([...loginOnly(), balanceMock(initial, makeBalance(initial))])

    await signIn(user)
    await screen.findByText('Saldo inicial')

    setDate('Fecha inicial', '2026-12-31')
    setDate('Fecha final', '2026-01-01')
    await submitRange(user)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'La fecha inicial no puede ser posterior a la fecha final.',
    )
  })

  it('rechaza una fecha imposible sin aplicar el rango', async () => {
    const user = userEvent.setup()
    const onApply = vi.fn()

    render(
      <DateRangeFilter
        range={{ fromDate: '2026-02-30', toDate: '2026-02-28' }}
        onApply={onApply}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Consultar' }))

    expect(screen.getByRole('alert')).toHaveTextContent(
      'La fecha inicial no es una fecha válida (YYYY-MM-DD).',
    )
    expect(screen.getByLabelText('Fecha inicial')).toHaveAttribute(
      'aria-invalid',
      'true',
    )
    expect(onApply).not.toHaveBeenCalled()
  })

  it('no ejecuta la consulta con un rango inválido', async () => {
    const user = userEvent.setup()
    const initial = getDefaultUtcMonthRange()
    const inverted: DateRange = {
      fromDate: '2026-12-31',
      toDate: '2026-01-01',
    }

    renderApp([
      ...loginOnly(),
      balanceMock(initial, makeBalance(initial)),
      balanceMock(inverted, makeBalance(inverted, { totalIncome: '9999.00' })),
    ])

    await signIn(user)
    await screen.findByText('Saldo inicial')

    setDate('Fecha inicial', inverted.fromDate)
    setDate('Fecha final', inverted.toDate)
    await submitRange(user)

    await screen.findByRole('alert')

    expect(screen.queryByText(periodText(inverted))).not.toBeInTheDocument()
    expect(screen.queryByText('$9,999.00')).not.toBeInTheDocument()
    expect(screen.getByText(periodText(initial))).toBeInTheDocument()
  })

  it('muestra los valores reales en cero de una respuesta válida', async () => {
    const user = userEvent.setup()
    const range = getDefaultUtcMonthRange()
    const zero = makeBalance(range, {
      openingBalance: '0.00',
      totalIncome: '0.00',
      totalExpense: '0.00',
      profit: '0.00',
      closingBalance: '0.00',
    })

    renderApp([...loginOnly(), balanceMock(range, zero)])

    await signIn(user)

    expect(await screen.findByText('Saldo inicial')).toBeInTheDocument()
    expect(screen.getAllByText('$0.00')).toHaveLength(5)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('muestra el estado de carga inicial sin importes ficticios', async () => {
    const user = userEvent.setup()
    const range = getDefaultUtcMonthRange()

    renderApp([
      ...loginOnly(),
      balanceMock(range, makeBalance(range), 300),
    ])

    await signIn(user)

    expect(await screen.findByText('Cargando balance…')).toBeInTheDocument()
    expect(screen.queryByText('Saldo inicial')).not.toBeInTheDocument()
    expect(screen.queryByText(/\$\s?\d/)).not.toBeInTheDocument()

    expect(await screen.findByText('Saldo inicial')).toBeInTheDocument()
  })

  it('identifica la actualización y conserva el periodo de los datos previos', async () => {
    const user = userEvent.setup()
    const range = getDefaultUtcMonthRange()
    const updated = makeBalance(range, { totalIncome: '2000.00' })

    renderApp([
      ...loginOnly(),
      balanceMock(range, makeBalance(range)),
      balanceMock(range, updated, 200),
    ])

    await signIn(user)
    await screen.findByText('$1,531.00')

    await user.click(screen.getByRole('button', { name: 'Actualizar' }))

    expect(await screen.findByText('Actualizando balance…')).toBeInTheDocument()
    expect(screen.getByText(periodText(range))).toBeInTheDocument()
    expect(screen.getByText('$1,531.00')).toBeInTheDocument()

    expect(await screen.findByText('$2,000.00')).toBeInTheDocument()
  })

  it('clasifica un error de red y permite reintentar', async () => {
    const user = userEvent.setup()
    const range = getDefaultUtcMonthRange()

    renderApp([
      ...loginOnly(),
      networkErrorMock(range),
      balanceMock(range, makeBalance(range)),
    ])

    await signIn(user)

    expect(
      await screen.findByText(
        'No fue posible conectar con el servidor. Revisa tu conexión e inténtalo de nuevo.',
      ),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Reintentar' }))

    expect(await screen.findByText('Saldo inicial')).toBeInTheDocument()
    expect(
      screen.queryByText(/No fue posible conectar con el servidor/),
    ).not.toBeInTheDocument()
  })

  it('muestra el error de permisos sin ofrecer reintento ni cerrar sesión', async () => {
    const user = userEvent.setup()
    const range = getDefaultUtcMonthRange()

    renderApp([
      ...loginOnly(),
      graphQLErrorMock(
        range,
        'El rol no tiene el permiso transactions.read',
      ),
    ])

    await signIn(user)

    expect(
      await screen.findByText(
        'No tienes permisos para consultar el balance de esta empresa.',
      ),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Reintentar' }),
    ).not.toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Cerrar sesión' }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('heading', { name: 'Inicia sesión' }),
    ).not.toBeInTheDocument()
  })

  it('muestra el error de autenticación sin ofrecer reintento', async () => {
    const user = userEvent.setup()
    const range = getDefaultUtcMonthRange()

    renderApp([
      ...loginOnly(),
      graphQLErrorMock(range, 'Token inválido o expirado'),
    ])

    await signIn(user)

    expect(
      await screen.findByText(
        'Tu sesión expiró o el token no es válido. Inicia sesión de nuevo.',
      ),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Reintentar' }),
    ).not.toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Cerrar sesión' }),
    ).toBeInTheDocument()
  })

  it('no presenta información financiera ficticia antes de recibir datos', async () => {
    const user = userEvent.setup()
    const range = getDefaultUtcMonthRange()

    renderApp([
      ...loginOnly(),
      balanceMock(range, makeBalance(range), 300),
    ])

    await signIn(user)
    await screen.findByText('Cargando balance…')

    expect(screen.queryByText(/\$\s?\d/)).not.toBeInTheDocument()
    expect(screen.queryByText('Saldo inicial')).not.toBeInTheDocument()
    expect(screen.queryByText('Ingresos')).not.toBeInTheDocument()
    expect(screen.queryByText('Egresos')).not.toBeInTheDocument()
    expect(screen.queryByText('Utilidad')).not.toBeInTheDocument()
    expect(screen.queryByText('Saldo final')).not.toBeInTheDocument()

    expect(await screen.findByText('Saldo inicial')).toBeInTheDocument()
  })
})

describe('dashboard: indicador global de riesgo', () => {
  const range: DateRange = {
    fromDate: '2026-01-01',
    toDate: '2026-01-31',
  }

  function renderRisk(
    overrides: Partial<GeneralBalance>,
  ): HTMLElement {
    render(<BalanceSummary balance={makeBalance(range, overrides)} />)

    return screen.getByRole('region', { name: /global/i })
  }

  it('presenta sin riesgo global cuando isInRed es falso y no hay cuentas en rojo', () => {
    const region = renderRisk({ isInRed: false, accountsInRed: 0 })

    expect(region).toHaveClass('dashboard-summary__risk--safe')
    expect(
      within(region).getByRole('heading', { name: 'Sin riesgo global' }),
    ).toBeInTheDocument()
    expect(
      within(region).getByText('0 cuentas en números rojos'),
    ).toBeInTheDocument()
    expect(
      within(region).getByText(
        'El saldo final global no es negativo y ninguna cuenta tiene saldo negativo.',
      ),
    ).toBeInTheDocument()
  })

  it('presenta riesgo global y una cuenta en rojo cuando isInRed es verdadero', () => {
    const region = renderRisk({ isInRed: true, accountsInRed: 1 })

    expect(region).toHaveClass('dashboard-summary__risk--global')
    expect(
      within(region).getByRole('heading', {
        name: 'Riesgo financiero global',
      }),
    ).toBeInTheDocument()
    expect(
      within(region).getByText('1 cuenta en números rojos'),
    ).toBeInTheDocument()
    expect(
      within(region).getByText('El saldo final global es negativo.'),
    ).toBeInTheDocument()
  })

  it('usa el plural cuando hay más de una cuenta en rojo', () => {
    const region = renderRisk({ isInRed: true, accountsInRed: 3 })

    expect(region).toHaveClass('dashboard-summary__risk--global')
    expect(
      within(region).getByText('3 cuentas en números rojos'),
    ).toBeInTheDocument()
    expect(
      within(region).queryByText('1 cuenta en números rojos'),
    ).not.toBeInTheDocument()
  })

  it('no contradice el caso válido sin riesgo global con una cuenta en rojo', () => {
    const region = renderRisk({ isInRed: false, accountsInRed: 1 })

    expect(region).toHaveClass('dashboard-summary__risk--accounts')
    expect(
      within(region).getByRole('heading', { name: 'Sin riesgo global' }),
    ).toBeInTheDocument()
    expect(
      within(region).getByText('1 cuenta en números rojos'),
    ).toBeInTheDocument()
    expect(
      within(region).getByText(
        'El saldo final global no es negativo, pero hay cuentas individuales con saldo negativo.',
      ),
    ).toBeInTheDocument()
    expect(
      within(region).queryByText('Riesgo financiero global'),
    ).not.toBeInTheDocument()
  })

  it('mantiene el singular y el plural diferenciados', () => {
    const singular = renderRisk({ isInRed: false, accountsInRed: 1 })
    expect(
      within(singular).getByText('1 cuenta en números rojos'),
    ).toBeInTheDocument()

    cleanup()

    const plural = renderRisk({ isInRed: false, accountsInRed: 2 })
    expect(
      within(plural).getByText('2 cuentas en números rojos'),
    ).toBeInTheDocument()
  })
})
