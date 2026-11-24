import type { MockedResponse } from '@apollo/client/testing'
import { GraphQLError } from 'graphql'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { COMPANY_USERS_QUERY } from '../src/api/operations/admin'
import {
  ACTIVE_ROLES_QUERY,
  ASSIGN_ROLE_MUTATION,
  MATRIX_QUERY,
  PREVIEW_ROLE_PERMISSIONS_QUERY,
  ROLE_PERMISSIONS_QUERY,
  SET_ROLE_PERMISSIONS_MUTATION,
} from '../src/api/operations/roles'
import { ME_QUERY } from '../src/api/operations/session'
import type { CompanyUserRow, SessionInfo } from '../src/types/admin'
import { loginMock, makeJwt } from './helpers/auth'
import { renderApp } from './helpers/renderApp'

const EMAIL = 'admin_a@test.local'
const PASSWORD = 'clave-correcta'
const COMPANY_ID = 11

/** Catálogo como lo deja el seed del Parcial II: `name` igual al código. */
const PERMISSIONS = [
  { id: 1, code: 'company.users.read' },
  { id: 2, code: 'company.users.write' },
  { id: 3, code: 'accounts.read' },
  { id: 4, code: 'accounts.write' },
  { id: 5, code: 'concepts.read' },
  { id: 6, code: 'concepts.write' },
  { id: 7, code: 'transactions.read' },
  { id: 8, code: 'transactions.write' },
  { id: 9, code: 'roles.read' },
  { id: 10, code: 'roles.write' },
].map((p) => ({ ...p, name: p.code }))

const ROLES = [
  { id: 1, code: 'ADMINISTRADOR', name: 'ADMINISTRADOR' },
  { id: 2, code: 'CONTADOR', name: 'CONTADOR' },
  { id: 3, code: 'CAPTURISTA', name: 'CAPTURISTA' },
  { id: 4, code: 'CONSULTA', name: 'CONSULTA' },
]

const CODE_ID = new Map(PERMISSIONS.map((p) => [p.code, p.id]))

/** Matriz inicial (enunciado, sección 2.2). */
const INITIAL: Record<string, string[]> = {
  ADMINISTRADOR: PERMISSIONS.map((p) => p.code),
  CONTADOR: [
    'company.users.read',
    'accounts.read',
    'accounts.write',
    'concepts.read',
    'concepts.write',
    'transactions.read',
    'transactions.write',
    'roles.read',
  ],
  CAPTURISTA: [
    'accounts.read',
    'concepts.read',
    'transactions.read',
    'transactions.write',
  ],
  CONSULTA: [
    'company.users.read',
    'accounts.read',
    'concepts.read',
    'transactions.read',
  ],
}

const ADMIN_PERMISSIONS = INITIAL.ADMINISTRADOR
const CONTADOR_PERMISSIONS = INITIAL.CONTADOR
const CAPTURISTA_PERMISSIONS = INITIAL.CAPTURISTA

type UserEventApi = ReturnType<typeof userEvent.setup>

function session(permissions: string[], roleCode: string): SessionInfo {
  return {
    companyUserId: 1,
    isAdmin: roleCode === 'ADMINISTRADOR',
    permissions,
    company: { id: COMPANY_ID, name: 'FinTrack Demo' },
    user: { id: 1, name: 'Sesión', email: EMAIL },
    role: { id: 1, code: roleCode, name: roleCode },
  }
}

function meMock(info: SessionInfo): MockedResponse {
  return { request: { query: ME_QUERY }, result: { data: { me: info } } }
}

function login(): MockedResponse {
  return loginMock({ email: EMAIL, password: PASSWORD, token: makeJwt(1800) })
}

function matrixMock(
  roles = ROLES,
  permissions = PERMISSIONS,
): MockedResponse {
  // El API puede devolver otro orden: la pantalla impone el del enunciado.
  return {
    request: { query: MATRIX_QUERY },
    result: {
      data: {
        roles: [...roles].reverse(),
        permissions: [...permissions].reverse(),
      },
    },
  }
}

function columnMock(
  roleId: number,
  codes: string[],
  extra: { code: string; isActive: boolean }[] = [],
): MockedResponse {
  const rows = [
    ...codes.map((code) => ({ code, isActive: true })),
    ...extra,
  ].map(({ code, isActive }, index) => {
    const id = CODE_ID.get(code)!
    return {
      id: roleId * 100 + index,
      isActive,
      permissionId: id,
      permission: { id, code },
    }
  })

  return {
    request: { query: ROLE_PERMISSIONS_QUERY, variables: { roleId } },
    result: { data: { rolePermissions: rows } },
  }
}

function initialColumns(): MockedResponse[] {
  return ROLES.map((role) => columnMock(role.id, INITIAL[role.code]))
}

function ids(codes: string[]): string[] {
  return codes.map((code) => CODE_ID.get(code)!).sort((a, b) => a - b).map(String)
}

function ref(code: string) {
  return { id: CODE_ID.get(code)!, code }
}

const CAPTURISTA_PLUS = [...INITIAL.CAPTURISTA, 'accounts.write']

function previewMock(): MockedResponse {
  return {
    request: {
      query: PREVIEW_ROLE_PERMISSIONS_QUERY,
      variables: { input: { roleId: '3', permissionIds: ids(CAPTURISTA_PLUS) } },
    },
    result: {
      data: {
        previewRolePermissions: {
          toActivate: [ref('accounts.write')],
          toDeactivate: [],
          unchanged: INITIAL.CAPTURISTA.map(ref),
          finalCount: 5,
        },
      },
    },
  }
}

function saveMock(changed: boolean, list: string[]): MockedResponse {
  return {
    request: {
      query: SET_ROLE_PERMISSIONS_MUTATION,
      variables: { input: { roleId: '3', permissionIds: ids(list) } },
    },
    result: {
      data: {
        setRolePermissions: {
          activated: changed ? [ref('accounts.write')] : [],
          deactivated: [],
          finalCount: list.length,
          changed,
        },
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

async function findMatrix() {
  return screen.findByRole('table', { name: 'Matriz de roles y permisos' })
}

describe('roles y permisos: matriz', () => {
  it('abre con la matriz inicial, en el orden del enunciado y con Administrador en solo lectura', async () => {
    const user = userEvent.setup()
    startAt('#/admin/roles')

    renderApp([
      login(),
      meMock(session(ADMIN_PERMISSIONS, 'ADMINISTRADOR')),
      matrixMock(),
      ...initialColumns(),
    ])
    await signIn(user)

    const table = await findMatrix()
    const nav = screen.getByRole('navigation', { name: 'Secciones' })
    expect(
      within(nav).getByRole('link', { name: /Roles y permisos/ }),
    ).toHaveAttribute('aria-current', 'page')

    const headers = within(table)
      .getAllByRole('columnheader')
      .filter((th) => th.getAttribute('scope') === 'col')
      .map((th) => th.textContent)
    expect(headers).toEqual([
      'Permiso',
      'AdministradorADMINISTRADORSolo lectura',
      'ContadorCONTADOR',
      'CapturistaCAPTURISTA',
      'ConsultaCONSULTA',
    ])

    const groups = within(table)
      .getAllByRole('columnheader')
      .filter((th) => th.getAttribute('scope') === 'colgroup')
      .map((th) => th.textContent)
    expect(groups).toEqual([
      'Usuarios',
      'Cuentas',
      'Conceptos',
      'Movimientos',
      'Roles',
    ])

    // Cada celda coincide con la tabla de la sección 2.2.
    for (const role of ROLES) {
      const label = role.name.charAt(0) + role.name.slice(1).toLowerCase()
      for (const permission of PERMISSIONS) {
        const rowLabel = within(table)
          .getByText(permission.code, { exact: false })
          .closest('th')!
          .querySelector('span')!.textContent
        const box = within(table).getByRole('checkbox', {
          name: `${label}: ${rowLabel}`,
        })
        expect(box).toHaveProperty(
          'checked',
          INITIAL[role.code].includes(permission.code),
        )
        if (role.code === 'ADMINISTRADOR') {
          expect(box).toBeDisabled()
        } else {
          expect(box).toBeEnabled()
        }
      }
    }

    expect(within(table).getByText('Crear cuentas')).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Revisar y guardar Administrador' }),
    ).not.toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Revisar y guardar Capturista' }),
    ).toBeInTheDocument()
  })

  it('una fila inactiva se lee como «no»', async () => {
    const user = userEvent.setup()
    startAt('#/admin/roles')

    renderApp([
      login(),
      meMock(session(ADMIN_PERMISSIONS, 'ADMINISTRADOR')),
      matrixMock(),
      columnMock(1, INITIAL.ADMINISTRADOR),
      columnMock(2, INITIAL.CONTADOR),
      columnMock(3, INITIAL.CAPTURISTA),
      columnMock(4, INITIAL.CONSULTA, [
        { code: 'transactions.write', isActive: false },
      ]),
    ])
    await signIn(user)

    await findMatrix()
    expect(
      screen.getByRole('checkbox', { name: 'Consulta: Registrar movimientos' }),
    ).not.toBeChecked()
  })

  it('Capturista + Crear cuentas: vista previa, guardar, releer la columna y changed en false al repetir', async () => {
    const user = userEvent.setup()
    startAt('#/admin/roles')

    renderApp([
      login(),
      meMock(session(ADMIN_PERMISSIONS, 'ADMINISTRADOR')),
      matrixMock(),
      ...initialColumns(),
      previewMock(),
      saveMock(true, CAPTURISTA_PLUS),
      columnMock(3, CAPTURISTA_PLUS),
      // Segundo guardado de la misma columna, sin cambios.
      {
        ...previewMock(),
        result: {
          data: {
            previewRolePermissions: {
              toActivate: [],
              toDeactivate: [],
              unchanged: CAPTURISTA_PLUS.map(ref),
              finalCount: 5,
            },
          },
        },
      },
      saveMock(false, CAPTURISTA_PLUS),
      columnMock(3, CAPTURISTA_PLUS),
    ])
    await signIn(user)
    await findMatrix()

    await user.click(
      screen.getByRole('checkbox', { name: 'Capturista: Crear cuentas' }),
    )
    expect(screen.getByText('Sin guardar')).toBeInTheDocument()

    await user.click(
      screen.getByRole('button', { name: 'Revisar y guardar Capturista' }),
    )

    const preview = await screen.findByLabelText('Vista previa de Capturista')
    expect(within(preview).getByText('accounts.write')).toBeInTheDocument()
    expect(within(preview).getByText('nada')).toBeInTheDocument()
    expect(within(preview).getByText('4')).toBeInTheDocument()
    expect(within(preview).getByText('5')).toBeInTheDocument()

    await user.click(
      screen.getByRole('button', { name: 'Guardar columna Capturista' }),
    )

    expect(
      await screen.findByText(/Se guardó la columna Capturista/),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('checkbox', { name: 'Capturista: Crear cuentas' }),
    ).toBeChecked()
    expect(screen.queryByText('Sin guardar')).not.toBeInTheDocument()

    await user.click(
      screen.getByRole('button', { name: 'Revisar y guardar Capturista' }),
    )
    await screen.findByLabelText('Vista previa de Capturista')
    await waitFor(() =>
      expect(
        screen.getByRole('button', { name: 'Guardar columna Capturista' }),
      ).toBeEnabled(),
    )
    await user.click(
      screen.getByRole('button', { name: 'Guardar columna Capturista' }),
    )

    expect(await screen.findByText(/changed: false/)).toBeInTheDocument()
  })

  it('muestra el error del API y conserva la columna sin guardar', async () => {
    const user = userEvent.setup()
    startAt('#/admin/roles')

    renderApp([
      login(),
      meMock(session(ADMIN_PERMISSIONS, 'ADMINISTRADOR')),
      matrixMock(),
      ...initialColumns(),
      previewMock(),
      {
        request: saveMock(true, CAPTURISTA_PLUS).request,
        result: {
          errors: [new GraphQLError('El rol no tiene el permiso roles.write')],
        },
      },
    ])
    await signIn(user)
    await findMatrix()

    await user.click(
      screen.getByRole('checkbox', { name: 'Capturista: Crear cuentas' }),
    )
    await user.click(
      screen.getByRole('button', { name: 'Revisar y guardar Capturista' }),
    )
    await screen.findByLabelText('Vista previa de Capturista')
    await user.click(
      screen.getByRole('button', { name: 'Guardar columna Capturista' }),
    )

    expect(await screen.findByText(/Tu rol no permite/)).toBeInTheDocument()
    expect(screen.getByText('Sin guardar')).toBeInTheDocument()
  })

  it('el contador ve la matriz deshabilitada y no puede guardar', async () => {
    const user = userEvent.setup()
    startAt('#/admin/roles')

    renderApp([
      login(),
      meMock(session(CONTADOR_PERMISSIONS, 'CONTADOR')),
      matrixMock(),
      ...initialColumns(),
    ])
    await signIn(user)

    const table = await findMatrix()
    for (const box of within(table).getAllByRole('checkbox')) {
      expect(box).toBeDisabled()
    }
    expect(
      screen.queryByRole('button', { name: /Revisar y guardar/ }),
    ).not.toBeInTheDocument()
    expect(screen.getByText(/roles.read sin roles.write/)).toBeInTheDocument()
  })

  it('el capturista no ve el ítem del menú y la URL directa no consulta la matriz', async () => {
    const user = userEvent.setup()
    startAt('#/admin/roles')

    renderApp([login(), meMock(session(CAPTURISTA_PERMISSIONS, 'CAPTURISTA'))])
    await signIn(user)

    expect(
      await screen.findByText(/no tiene el permiso roles.read/),
    ).toBeInTheDocument()
    const nav = screen.getByRole('navigation', { name: 'Secciones' })
    expect(
      within(nav).queryByRole('link', { name: /Roles y permisos/ }),
    ).not.toBeInTheDocument()
    expect(
      within(nav).queryByRole('link', { name: /Usuarios/ }),
    ).not.toBeInTheDocument()
    expect(within(nav).getByRole('link', { name: /Cuentas/ })).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('avisa si el catálogo no está cargado', async () => {
    const user = userEvent.setup()
    startAt('#/admin/roles')

    renderApp([
      login(),
      meMock(session(ADMIN_PERMISSIONS, 'ADMINISTRADOR')),
      matrixMock([], []),
    ])
    await signIn(user)

    expect(
      await screen.findByText('El catálogo de roles y permisos no está cargado.'),
    ).toBeInTheDocument()
  })
})

const USERS: CompanyUserRow[] = [
  {
    id: 1,
    isAdmin: true,
    isActive: true,
    user: { id: 1, name: 'David Morales', email: 'david@test.local' },
    role: ROLES[0],
  },
  {
    id: 2,
    isAdmin: false,
    isActive: true,
    user: { id: 2, name: 'Edwuard Chay', email: 'luis@test.local' },
    role: ROLES[3],
  },
]

function usersMock(rows: CompanyUserRow[]): MockedResponse {
  return {
    request: { query: COMPANY_USERS_QUERY, variables: { companyId: COMPANY_ID } },
    result: { data: { companyUsers: rows } },
  }
}

function rolesMock(): MockedResponse {
  return {
    request: { query: ACTIVE_ROLES_QUERY },
    result: { data: { roles: ROLES } },
  }
}

describe('roles y permisos: puesto en Usuarios', () => {
  it('asigna Capturista a quien estaba en Consulta con assignRole', async () => {
    const user = userEvent.setup()
    startAt('#/admin/usuarios')

    renderApp([
      login(),
      meMock(session(ADMIN_PERMISSIONS, 'ADMINISTRADOR')),
      usersMock(USERS),
      rolesMock(),
      {
        request: {
          query: ASSIGN_ROLE_MUTATION,
          variables: { input: { companyUserId: 2, roleId: 3 } },
        },
        result: {
          data: { assignRole: { id: 50, isActive: true, role: ROLES[2] } },
        },
      },
      usersMock([USERS[0], { ...USERS[1], role: ROLES[2] }]),
    ])
    await signIn(user)

    const select = await screen.findByLabelText('Puesto de Edwuard Chay')
    // El administrador principal no tiene selector: isAdmin no se toca.
    expect(screen.queryByLabelText('Puesto de David Morales')).not.toBeInTheDocument()
    expect(within(select).getAllByRole('option').map((o) => o.textContent)).toEqual([
      'Administrador',
      'Contador',
      'Capturista',
      'Consulta',
    ])

    const save = screen.getByRole('button', { name: 'Guardar puesto de Edwuard Chay' })
    expect(save).toBeDisabled()

    await user.selectOptions(select, '3')
    await user.click(save)

    expect(
      await screen.findByText(
        'Edwuard Chay ahora tiene el puesto Capturista. isAdmin no cambió.',
      ),
    ).toBeInTheDocument()
    const row = screen.getByText('Edwuard Chay').closest('tr')!
    expect(within(row).getByText('Capturista', { selector: 'span' })).toBeInTheDocument()
    expect(within(row).getByText('No')).toBeInTheDocument()
  })

  it('si el API rechaza, se lee el error y el puesto anterior se queda', async () => {
    const user = userEvent.setup()
    startAt('#/admin/usuarios')

    renderApp([
      login(),
      meMock(session(ADMIN_PERMISSIONS, 'ADMINISTRADOR')),
      usersMock(USERS),
      rolesMock(),
      {
        request: {
          query: ASSIGN_ROLE_MUTATION,
          variables: { input: { companyUserId: 2, roleId: 2 } },
        },
        result: { errors: [new GraphQLError('El rol no está activo')] },
      },
    ])
    await signIn(user)

    const select = await screen.findByLabelText('Puesto de Edwuard Chay')
    await user.selectOptions(select, '2')
    await user.click(
      screen.getByRole('button', { name: 'Guardar puesto de Edwuard Chay' }),
    )

    expect(await screen.findByText('El rol no está activo')).toBeInTheDocument()
    expect(select).toHaveValue('4')
  })

  it('sin roles.write la columna Rol es solo texto', async () => {
    const user = userEvent.setup()
    startAt('#/admin/usuarios')

    renderApp([
      login(),
      meMock(session(CONTADOR_PERMISSIONS, 'CONTADOR')),
      usersMock(USERS),
    ])
    await signIn(user)

    const row = (await screen.findByText('Edwuard Chay')).closest('tr')!
    expect(within(row).getByText('Consulta')).toBeInTheDocument()
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
  })
})
