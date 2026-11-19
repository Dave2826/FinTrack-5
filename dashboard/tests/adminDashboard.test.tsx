import type { MockedResponse } from '@apollo/client/testing'
import { GraphQLError } from 'graphql'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import {
  ACCOUNTS_QUERY,
  ACCOUNT_CONCEPTS_QUERY,
  ASSIGN_CONCEPT_MUTATION,
  COMPANY_USERS_QUERY,
  CONCEPTS_QUERY,
  CREATE_ACCOUNT_MUTATION,
  CREATE_COMPANY_USER_MUTATION,
  DEACTIVATE_COMPANY_USER_MUTATION,
  REMOVE_CONCEPT_MUTATION,
} from '../src/api/operations/admin'
import { ME_QUERY } from '../src/api/operations/session'
import type {
  AdminAccount,
  AdminConcept,
  CompanyUserRow,
  SessionInfo,
} from '../src/types/admin'
import { loginMock, makeJwt } from './helpers/auth'
import { renderApp } from './helpers/renderApp'

const EMAIL = 'admin_a@test.local'
const PASSWORD = 'clave-correcta'
const COMPANY_ID = 11

const ADMIN_PERMISSIONS = [
  'accounts.read',
  'accounts.write',
  'company.users.read',
  'company.users.write',
  'concepts.read',
  'concepts.write',
  'roles.read',
  'roles.write',
  'transactions.read',
  'transactions.write',
]

const CONSULTA_PERMISSIONS = [
  'accounts.read',
  'company.users.read',
  'concepts.read',
  'transactions.read',
]

type UserEventApi = ReturnType<typeof userEvent.setup>

function session(permissions: string[], roleCode = 'ADMINISTRADOR'): SessionInfo {
  return {
    companyUserId: 1,
    isAdmin: roleCode === 'ADMINISTRADOR',
    permissions,
    company: { id: COMPANY_ID, name: 'FinTrack Demo' },
    user: { id: 1, name: 'Admin A', email: EMAIL },
    role: { id: 1, code: roleCode, name: roleCode },
  }
}

function meMock(info: SessionInfo): MockedResponse {
  return { request: { query: ME_QUERY }, result: { data: { me: info } } }
}

const USERS: CompanyUserRow[] = [
  {
    id: 1,
    isAdmin: true,
    isActive: true,
    user: { id: 1, name: 'David Morales', email: 'david.morales@tecdesoftware.edu.mx' },
    role: { id: 1, code: 'ADMINISTRADOR', name: 'ADMINISTRADOR' },
  },
  {
    id: 2,
    isAdmin: false,
    isActive: true,
    user: { id: 2, name: 'Edwuard Chay', email: 'luis.chay@tecdesoftware.edu.mx' },
    role: { id: 4, code: 'CONSULTA', name: 'CONSULTA' },
  },
  {
    id: 3,
    isAdmin: false,
    isActive: false,
    user: { id: 3, name: 'Persona Inactiva', email: 'inactiva@test.local' },
    role: null,
  },
]

function usersMock(rows: CompanyUserRow[]): MockedResponse {
  return {
    request: { query: COMPANY_USERS_QUERY, variables: { companyId: COMPANY_ID } },
    result: { data: { companyUsers: rows } },
  }
}

const ACCOUNTS: AdminAccount[] = [
  {
    id: 1,
    name: 'Caja',
    accountType: 'CASH',
    bankName: null,
    clabe: null,
    cardLastDigits: null,
    shortDescription: null,
    isActive: true,
  },
  {
    id: 2,
    name: 'Banco principal',
    accountType: 'DEBIT',
    bankName: 'Banco Uno',
    clabe: '012345678901234567',
    cardLastDigits: null,
    shortDescription: 'Cuenta de nómina',
    isActive: true,
  },
  {
    id: 3,
    name: 'Tarjeta vieja',
    accountType: 'CREDIT',
    bankName: 'Banco Dos',
    clabe: null,
    cardLastDigits: '9876',
    shortDescription: null,
    isActive: false,
  },
]

function accountsMock(rows: AdminAccount[], activeOnly = false): MockedResponse {
  return {
    request: {
      query: ACCOUNTS_QUERY,
      variables: { companyId: COMPANY_ID, activeOnly },
    },
    result: { data: { accounts: rows } },
  }
}

const CONCEPTS: AdminConcept[] = [
  { id: 10, name: 'Ventas', conceptType: 'INCOME', shortDescription: null, isActive: true },
  { id: 11, name: 'Renta', conceptType: 'EXPENSE', shortDescription: null, isActive: true },
  { id: 12, name: 'Viejo', conceptType: 'EXPENSE', shortDescription: null, isActive: false },
]

function conceptsMock(rows: AdminConcept[]): MockedResponse {
  return {
    request: {
      query: CONCEPTS_QUERY,
      variables: { companyId: COMPANY_ID, activeOnly: false },
    },
    result: { data: { concepts: rows } },
  }
}

function relationsMock(accountId: number, conceptIds: number[]): MockedResponse {
  return {
    request: { query: ACCOUNT_CONCEPTS_QUERY, variables: { accountId } },
    result: {
      data: {
        accountConcepts: conceptIds.map((conceptId, index) => {
          const concept = CONCEPTS.find((c) => c.id === conceptId)!
          return {
            id: 100 + index,
            isActive: true,
            concept: {
              id: concept.id,
              name: concept.name,
              conceptType: concept.conceptType,
            },
          }
        }),
      },
    },
  }
}

function startAt(hash: string) {
  window.history.replaceState(null, '', `/${hash}`)
}

async function signIn(user: UserEventApi) {
  await user.type(screen.getByLabelText('Correo electrónico'), EMAIL)
  await user.type(screen.getByLabelText('Contraseña'), PASSWORD)
  await user.click(screen.getByRole('button', { name: 'Entrar' }))
}

function login(): MockedResponse {
  return loginMock({ email: EMAIL, password: PASSWORD, token: makeJwt(1800) })
}

describe('dashboard administrativo: menú y sesión', () => {
  it('distingue el dashboard financiero del administrativo y conserva el cierre de sesión', async () => {
    const user = userEvent.setup()
    startAt('#/admin/usuarios')

    renderApp([login(), meMock(session(ADMIN_PERMISSIONS)), usersMock(USERS)])
    await signIn(user)

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Dashboard administrativo' }),
    ).toBeInTheDocument()
    expect(await screen.findByText('FinTrack Demo')).toBeInTheDocument()

    const nav = screen.getByRole('navigation', { name: 'Secciones' })
    expect(within(nav).getByRole('link', { name: 'Dashboard financiero' })).toBeInTheDocument()
    expect(
      within(nav).getByRole('link', { name: /Usuarios/ }),
    ).toHaveAttribute('aria-current', 'page')
    expect(within(nav).getByRole('link', { name: /Cuentas/ })).toBeInTheDocument()
    expect(within(nav).getByRole('link', { name: /Conceptos/ })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Cerrar sesión' }))

    expect(
      await screen.findByRole('heading', { name: 'Inicia sesión' }),
    ).toBeInTheDocument()
  })

  it('vuelve al login si el API rechaza la sesión', async () => {
    const user = userEvent.setup()
    startAt('#/admin/usuarios')

    renderApp([
      login(),
      {
        request: { query: ME_QUERY },
        result: { errors: [new GraphQLError('Token inválido o expirado')] },
      },
    ])
    await signIn(user)

    expect(
      await screen.findByRole('heading', { name: 'Inicia sesión' }),
    ).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })
})

describe('dashboard administrativo: usuarios', () => {
  it('muestra las membresías, los conteos y filtra en pantalla', async () => {
    const user = userEvent.setup()
    startAt('#/admin/usuarios')

    renderApp([login(), meMock(session(ADMIN_PERMISSIONS)), usersMock(USERS)])
    await signIn(user)

    const table = await screen.findByRole('table', { name: 'Usuarios de la empresa' })
    expect(within(table).getByText('David Morales')).toBeInTheDocument()
    expect(within(table).getByText('Sin rol')).toBeInTheDocument()
    expect(within(table).getByText('Inactivo')).toBeInTheDocument()
    expect(within(table).queryByText(/contraseña/i)).not.toBeInTheDocument()

    const counters = screen.getByLabelText('Conteos de usuarios')
    expect(within(counters).getByText('Usuarios activos').nextSibling).toHaveTextContent('2')
    expect(within(counters).getByText('Administrador principal').nextSibling).toHaveTextContent('1')
    expect(within(counters).getByText('Inactivos').nextSibling).toHaveTextContent('1')

    await user.type(screen.getByLabelText('Buscar por nombre o correo'), 'chay')
    expect(within(table).queryByText('David Morales')).not.toBeInTheDocument()
    expect(within(table).getByText('Edwuard Chay')).toBeInTheDocument()

    await user.clear(screen.getByLabelText('Buscar por nombre o correo'))
    await user.click(screen.getByLabelText('Solo activos'))
    expect(within(table).queryByText('Persona Inactiva')).not.toBeInTheDocument()
  })

  it('señala un error de datos si hay más de un administrador principal', async () => {
    const user = userEvent.setup()
    startAt('#/admin/usuarios')
    const twoAdmins = USERS.map((row) => (row.id === 2 ? { ...row, isAdmin: true } : row))

    renderApp([login(), meMock(session(ADMIN_PERMISSIONS)), usersMock(twoAdmins)])
    await signIn(user)

    expect(
      await screen.findByText(/2 administradores principales activos/),
    ).toBeInTheDocument()
  })

  it('da de alta un usuario, vuelve a consultar la tabla y muestra el correo duplicado', async () => {
    const user = userEvent.setup()
    startAt('#/admin/usuarios')

    const nuevo: CompanyUserRow = {
      id: 4,
      isAdmin: false,
      isActive: true,
      user: { id: 4, name: 'Nueva Persona', email: 'nueva@test.local' },
      role: null,
    }
    const input = {
      companyId: COMPANY_ID,
      name: 'Nueva Persona',
      email: 'nueva@test.local',
      password: 'clave-segura-1',
    }

    renderApp([
      login(),
      meMock(session(ADMIN_PERMISSIONS)),
      usersMock(USERS),
      {
        request: { query: CREATE_COMPANY_USER_MUTATION, variables: { input } },
        result: {
          data: {
            createCompanyUser: {
              id: 4,
              isAdmin: false,
              isActive: true,
              user: nuevo.user,
            },
          },
        },
      },
      usersMock([...USERS, nuevo]),
      {
        request: { query: CREATE_COMPANY_USER_MUTATION, variables: { input } },
        result: { errors: [new GraphQLError('Ya existe un usuario con ese correo')] },
      },
    ])
    await signIn(user)

    await screen.findByRole('table', { name: 'Usuarios de la empresa' })
    await user.click(screen.getByRole('button', { name: 'Nuevo usuario' }))

    const form = screen.getByRole('form', { name: 'Nuevo usuario' })
    expect(within(form).queryByLabelText(/admin/i)).not.toBeInTheDocument()

    await user.click(within(form).getByRole('button', { name: 'Guardar usuario' }))
    expect(within(form).getByText('Escribe el nombre de la persona.')).toBeInTheDocument()

    await user.type(within(form).getByLabelText('Nombre'), input.name)
    await user.type(within(form).getByLabelText('Correo'), input.email)
    await user.type(within(form).getByLabelText('Contraseña'), input.password)
    await user.click(within(form).getByRole('button', { name: 'Guardar usuario' }))

    expect(await screen.findByText('Se agregó a nueva@test.local.')).toBeInTheDocument()
    const table = screen.getByRole('table', { name: 'Usuarios de la empresa' })
    expect(await within(table).findByText('Nueva Persona')).toBeInTheDocument()
    expect(screen.queryByText(input.password)).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Nuevo usuario' }))
    const again = screen.getByRole('form', { name: 'Nuevo usuario' })
    await user.type(within(again).getByLabelText('Nombre'), input.name)
    await user.type(within(again).getByLabelText('Correo'), input.email)
    await user.type(within(again).getByLabelText('Contraseña'), input.password)
    await user.click(within(again).getByRole('button', { name: 'Guardar usuario' }))

    expect(
      await within(again).findByText('Ya existe un usuario con ese correo'),
    ).toBeInTheDocument()
  })

  it('desactiva con una baja lógica y vuelve a consultar', async () => {
    const user = userEvent.setup()
    startAt('#/admin/usuarios')

    renderApp([
      login(),
      meMock(session(ADMIN_PERMISSIONS)),
      usersMock(USERS),
      {
        request: {
          query: DEACTIVATE_COMPANY_USER_MUTATION,
          variables: { companyUserId: 2 },
        },
        result: { data: { deactivateCompanyUser: { id: 2, isActive: false } } },
      },
      usersMock(USERS.map((row) => (row.id === 2 ? { ...row, isActive: false } : row))),
    ])
    await signIn(user)

    await user.click(
      await screen.findByRole('button', { name: 'Desactivar a Edwuard Chay' }),
    )
    expect(screen.getByText(/historial se conservan/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Confirmar' }))

    expect(
      await screen.findByText('Edwuard Chay quedó inactivo. Su historial se conserva.'),
    ).toBeInTheDocument()
    const row = (await screen.findByText('Edwuard Chay')).closest('tr')!
    await waitFor(() => expect(within(row).getByText('Inactivo')).toBeInTheDocument())
  })

  it('un rol de solo consulta ve la tabla pero no las acciones de alta ni de baja', async () => {
    const user = userEvent.setup()
    startAt('#/admin/usuarios')

    renderApp([
      login(),
      meMock(session(CONSULTA_PERMISSIONS, 'CONSULTA')),
      usersMock(USERS),
    ])
    await signIn(user)

    expect(
      await screen.findByRole('table', { name: 'Usuarios de la empresa' }),
    ).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Nuevo usuario' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Desactivar/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('columnheader', { name: 'Acciones' })).not.toBeInTheDocument()
  })
})

describe('dashboard administrativo: cuentas', () => {
  it('muestra etiquetas de tipo, enmascara la referencia y filtra', async () => {
    const user = userEvent.setup()
    startAt('#/admin/cuentas')

    renderApp([login(), meMock(session(ADMIN_PERMISSIONS)), accountsMock(ACCOUNTS)])
    await signIn(user)

    const table = await screen.findByRole('table', { name: 'Cuentas de la empresa' })
    expect(within(table).getByText('Efectivo')).toBeInTheDocument()
    expect(within(table).getByText('Débito')).toBeInTheDocument()
    expect(within(table).getByText('CLABE •••• 4567')).toBeInTheDocument()
    expect(within(table).getByText('Tarjeta •••• 9876')).toBeInTheDocument()
    expect(within(table).queryByText('012345678901234567')).not.toBeInTheDocument()
    expect(within(table).getByText('Inactiva')).toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText('Tipo'), 'DEBIT')
    expect(within(table).queryByText('Caja')).not.toBeInTheDocument()
    expect(within(table).getByText('Banco principal')).toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText('Tipo'), 'ALL')
    await user.click(screen.getByLabelText('Solo activas'))
    expect(within(table).queryByText('Tarjeta vieja')).not.toBeInTheDocument()
  })

  it('crea una cuenta y vuelve a consultar la lista', async () => {
    const user = userEvent.setup()
    startAt('#/admin/cuentas')
    const nueva: AdminAccount = {
      id: 4,
      name: 'Monedero digital',
      accountType: 'WALLET',
      bankName: null,
      clabe: null,
      cardLastDigits: null,
      shortDescription: null,
      isActive: true,
    }

    renderApp([
      login(),
      meMock(session(ADMIN_PERMISSIONS)),
      accountsMock(ACCOUNTS),
      {
        request: {
          query: CREATE_ACCOUNT_MUTATION,
          variables: {
            input: {
              companyId: COMPANY_ID,
              accountType: 'WALLET',
              name: 'Monedero digital',
              bankName: null,
              clabe: null,
              shortDescription: null,
            },
          },
        },
        result: {
          data: {
            createAccount: {
              id: 4,
              name: 'Monedero digital',
              accountType: 'WALLET',
              isActive: true,
            },
          },
        },
      },
      accountsMock([...ACCOUNTS, nueva]),
    ])
    await signIn(user)

    await screen.findByRole('table', { name: 'Cuentas de la empresa' })
    await user.click(screen.getByRole('button', { name: 'Nueva cuenta' }))
    const form = screen.getByRole('form', { name: 'Nueva cuenta' })

    await user.type(within(form).getByLabelText('CLABE'), '123')
    await user.click(within(form).getByRole('button', { name: 'Guardar cuenta' }))
    expect(within(form).getByText(/18 dígitos/)).toBeInTheDocument()

    await user.clear(within(form).getByLabelText('CLABE'))
    await user.type(within(form).getByLabelText('Nombre'), 'Monedero digital')
    await user.selectOptions(within(form).getByLabelText('Tipo'), 'WALLET')
    await user.click(within(form).getByRole('button', { name: 'Guardar cuenta' }))

    expect(await screen.findByText('Se creó la cuenta Monedero digital.')).toBeInTheDocument()
    const table = screen.getByRole('table', { name: 'Cuentas de la empresa' })
    expect(await within(table).findByText('Monedero digital')).toBeInTheDocument()
    expect(within(table).getByText('Monedero')).toBeInTheDocument()
  })

  it('muestra el estado vacío y oculta Nueva cuenta sin accounts.write', async () => {
    const user = userEvent.setup()
    startAt('#/admin/cuentas')

    renderApp([
      login(),
      meMock(session(CONSULTA_PERMISSIONS, 'CONSULTA')),
      accountsMock([]),
    ])
    await signIn(user)

    expect(
      await screen.findByText('La empresa no tiene cuentas registradas.'),
    ).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Nueva cuenta' })).not.toBeInTheDocument()
  })
})

describe('dashboard administrativo: conceptos', () => {
  it('filtra el catálogo por tipo y lista los conceptos de la cuenta elegida', async () => {
    const user = userEvent.setup()
    startAt('#/admin/conceptos')

    renderApp([
      login(),
      meMock(session(ADMIN_PERMISSIONS)),
      conceptsMock(CONCEPTS),
      accountsMock(ACCOUNTS.filter((a) => a.isActive), true),
      relationsMock(2, [10]),
    ])
    await signIn(user)

    const table = await screen.findByRole('table', { name: 'Catálogo de conceptos' })
    expect(within(table).getAllByText('Egreso')).toHaveLength(2)

    await user.click(screen.getByRole('button', { name: 'Ingreso' }))
    expect(within(table).queryByText('Renta')).not.toBeInTheDocument()
    expect(within(table).getByText('Ventas')).toBeInTheDocument()

    await user.selectOptions(await screen.findByLabelText('Cuenta'), '2')
    const list = await screen.findByRole('list', { name: 'Conceptos permitidos' })
    expect(within(list).getByText('Ventas')).toBeInTheDocument()
  })

  it('muestra el duplicado al asignar y quita sin borrar del catálogo', async () => {
    const user = userEvent.setup()
    startAt('#/admin/conceptos')

    renderApp([
      login(),
      meMock(session(ADMIN_PERMISSIONS)),
      conceptsMock(CONCEPTS),
      accountsMock(ACCOUNTS.filter((a) => a.isActive), true),
      relationsMock(2, [10]),
      {
        request: {
          query: ASSIGN_CONCEPT_MUTATION,
          variables: { input: { accountId: 2, conceptId: 10 } },
        },
        result: {
          errors: [new GraphQLError('El concepto ya está asignado a esta cuenta')],
        },
      },
      {
        request: {
          query: REMOVE_CONCEPT_MUTATION,
          variables: { accountId: 2, conceptId: 10 },
        },
        result: { data: { removeConceptFromAccount: { id: 100, isActive: false } } },
      },
      relationsMock(2, []),
    ])
    await signIn(user)

    await user.selectOptions(await screen.findByLabelText('Cuenta'), '2')
    await screen.findByRole('list', { name: 'Conceptos permitidos' })

    await user.selectOptions(screen.getByLabelText('Concepto a asignar'), '10')
    await user.click(screen.getByRole('button', { name: 'Asignar' }))
    expect(
      await screen.findByText('El concepto ya está asignado a esta cuenta'),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Quitar Ventas de la cuenta' }))
    expect(
      await screen.findByText('Esta cuenta todavía no tiene conceptos permitidos.'),
    ).toBeInTheDocument()
    const table = screen.getByRole('table', { name: 'Catálogo de conceptos' })
    expect(within(table).getByText('Ventas')).toBeInTheDocument()
  })

  it('sin concepts.write no aparecen Nuevo concepto, Asignar ni Quitar', async () => {
    const user = userEvent.setup()
    startAt('#/admin/conceptos')

    renderApp([
      login(),
      meMock(session(CONSULTA_PERMISSIONS, 'CONSULTA')),
      conceptsMock(CONCEPTS),
      accountsMock(ACCOUNTS.filter((a) => a.isActive), true),
      relationsMock(2, [10]),
    ])
    await signIn(user)

    await screen.findByRole('table', { name: 'Catálogo de conceptos' })
    await user.selectOptions(await screen.findByLabelText('Cuenta'), '2')
    await screen.findByRole('list', { name: 'Conceptos permitidos' })

    expect(screen.queryByRole('button', { name: 'Nuevo concepto' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Asignar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Quitar/ })).not.toBeInTheDocument()
  })
})
