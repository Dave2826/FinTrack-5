import { useMutation, useQuery } from '@apollo/client'
import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import {
  COMPANY_USERS_QUERY,
  CREATE_COMPANY_USER_MUTATION,
  DEACTIVATE_COMPANY_USER_MUTATION,
} from '../../api/operations/admin'
import { ACTIVE_ROLES_QUERY } from '../../api/operations/roles'
import { useSessionErrorGuard } from '../../hooks/useSessionErrorGuard'
import { normalizeSearch } from '../../lib/adminLabels'
import { roleLabel, sortRoles } from '../../lib/roleMatrix'
import { readApiError } from '../../lib/apiErrors'
import type { ApiErrorInfo } from '../../lib/apiErrors'
import { useSessionInfo } from '../../session/useSessionInfo'
import type {
  CompanyUserRow,
  CompanyUsersResult,
  CreateCompanyUserInput,
} from '../../types/admin'
import type { ActiveRolesResult } from '../../types/roles'
import { AdminSection } from './components/AdminSection'
import { QueryFeedback } from './components/QueryFeedback'
import { RoleAssignControl } from './components/RoleAssignControl'
import { StatusBadge } from './components/StatusBadge'

const EMPTY_FORM = { name: '', email: '', password: '' }
const MIN_PASSWORD = 8

type FormErrors = Partial<Record<keyof typeof EMPTY_FORM, string>>

function validate(form: typeof EMPTY_FORM): FormErrors {
  const errors: FormErrors = {}

  if (!form.name.trim()) {
    errors.name = 'Escribe el nombre de la persona.'
  }

  if (!form.email.trim()) {
    errors.email = 'Escribe el correo.'
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
    errors.email = 'El correo no tiene un formato válido.'
  }

  if (form.password.length < MIN_PASSWORD) {
    errors.password = `La contraseña debe tener al menos ${MIN_PASSWORD} caracteres.`
  }

  return errors
}

function NewUserForm({
  companyId,
  onCreated,
  onCancel,
}: {
  companyId: number
  onCreated: (email: string) => Promise<void>
  onCancel: () => void
}) {
  const [form, setForm] = useState(EMPTY_FORM)
  const [errors, setErrors] = useState<FormErrors>({})
  const [apiError, setApiError] = useState<string | null>(null)
  const [createUser, { loading }] = useMutation<
    unknown,
    { input: CreateCompanyUserInput }
  >(CREATE_COMPANY_USER_MUTATION)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setApiError(null)

    const nextErrors = validate(form)
    setErrors(nextErrors)

    if (Object.keys(nextErrors).length > 0) {
      return
    }

    try {
      await createUser({
        variables: {
          input: {
            companyId,
            name: form.name.trim(),
            email: form.email.trim(),
            password: form.password,
          },
        },
      })
      const email = form.email.trim()
      // La contraseña no se conserva en el estado después de enviarla.
      setForm(EMPTY_FORM)
      await onCreated(email)
    } catch (error) {
      setApiError(readApiError(error).message)
    }
  }

  function update(field: keyof typeof EMPTY_FORM, value: string) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  return (
    <form
      className="admin-form"
      aria-labelledby="new-user-title"
      noValidate
      onSubmit={(event) => void handleSubmit(event)}
    >
      <h3 id="new-user-title">Nuevo usuario</h3>
      <p className="admin-form__hint">
        La persona se agrega a la empresa de tu sesión sin rol; el puesto se
        asigna después en la columna Rol de esta tabla. No se puede crear un
        segundo administrador principal.
      </p>

      <div className="admin-form__grid">
        <div className="field">
          <label className="field__label" htmlFor="new-user-name">
            Nombre
          </label>
          <input
            id="new-user-name"
            className="field__input"
            value={form.name}
            onChange={(event) => update('name', event.target.value)}
            aria-invalid={errors.name ? true : undefined}
            aria-describedby={errors.name ? 'new-user-name-error' : undefined}
            autoComplete="name"
          />
          {errors.name ? (
            <p className="field__error" id="new-user-name-error">
              {errors.name}
            </p>
          ) : null}
        </div>

        <div className="field">
          <label className="field__label" htmlFor="new-user-email">
            Correo
          </label>
          <input
            id="new-user-email"
            className="field__input"
            type="email"
            value={form.email}
            onChange={(event) => update('email', event.target.value)}
            aria-invalid={errors.email ? true : undefined}
            aria-describedby={errors.email ? 'new-user-email-error' : undefined}
            autoComplete="off"
          />
          {errors.email ? (
            <p className="field__error" id="new-user-email-error">
              {errors.email}
            </p>
          ) : null}
        </div>

        <div className="field">
          <label className="field__label" htmlFor="new-user-password">
            Contraseña
          </label>
          <input
            id="new-user-password"
            className="field__input"
            type="password"
            value={form.password}
            onChange={(event) => update('password', event.target.value)}
            aria-invalid={errors.password ? true : undefined}
            aria-describedby={
              errors.password ? 'new-user-password-error' : undefined
            }
            autoComplete="new-password"
          />
          {errors.password ? (
            <p className="field__error" id="new-user-password-error">
              {errors.password}
            </p>
          ) : null}
        </div>
      </div>

      {apiError ? (
        <div className="alert alert--error admin-alert" role="alert">
          <p>{apiError}</p>
        </div>
      ) : null}

      <div className="admin-form__actions">
        <button
          className="button button--primary admin-button"
          type="submit"
          disabled={loading}
        >
          {loading ? 'Guardando…' : 'Guardar usuario'}
        </button>
        <button
          className="button button--secondary admin-button"
          type="button"
          onClick={onCancel}
          disabled={loading}
        >
          Cancelar
        </button>
      </div>
    </form>
  )
}

function DeactivateAction({
  row,
  onDone,
}: {
  row: CompanyUserRow
  onDone: (message: string) => Promise<void>
}) {
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [deactivate, { loading }] = useMutation<
    unknown,
    { companyUserId: number }
  >(DEACTIVATE_COMPANY_USER_MUTATION)
  const name = row.user?.name ?? `Membresía #${row.id}`

  async function confirm() {
    setError(null)

    try {
      await deactivate({ variables: { companyUserId: row.id } })
      setConfirming(false)
      await onDone(`${name} quedó inactivo. Su historial se conserva.`)
    } catch (caught) {
      setError(readApiError(caught).message)
    }
  }

  if (!confirming) {
    return (
      <button
        className="button button--secondary admin-button admin-button--small"
        type="button"
        onClick={() => setConfirming(true)}
        aria-label={`Desactivar a ${name}`}
      >
        Desactivar
      </button>
    )
  }

  return (
    <div className="admin-confirm" role="group" aria-label={`Desactivar a ${name}`}>
      <p>
        {name} dejará de operar en la empresa. La fila y su historial se
        conservan.
      </p>
      <div className="admin-confirm__actions">
        <button
          className="button button--primary admin-button admin-button--small"
          type="button"
          onClick={() => void confirm()}
          disabled={loading}
        >
          {loading ? 'Desactivando…' : 'Confirmar'}
        </button>
        <button
          className="button button--secondary admin-button admin-button--small"
          type="button"
          onClick={() => {
            setConfirming(false)
            setError(null)
          }}
          disabled={loading}
        >
          Cancelar
        </button>
      </div>
      {error ? (
        <p className="field__error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  )
}

/**
 * Usuarios: membresías de la empresa de la sesión (`companyUsers`).
 * Responde "¿quién pertenece?".
 */
export function UsersAdminPage() {
  const { companyId, can, info, loading: sessionLoading } = useSessionInfo()
  const canRead = can('company.users.read')
  const canWrite = can('company.users.write')
  // Actividad 14: con roles.write la columna Rol llama a assignRole.
  const canAssign = can('roles.write')

  const [search, setSearch] = useState('')
  const [activeOnly, setActiveOnly] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  const { data, loading, error, refetch } = useQuery<
    CompanyUsersResult,
    { companyId: number }
  >(COMPANY_USERS_QUERY, {
    variables: companyId === null ? undefined : { companyId },
    skip: companyId === null || sessionLoading || !canRead,
    fetchPolicy: 'network-only',
    notifyOnNetworkStatusChange: true,
  })

  const { data: rolesData } = useQuery<ActiveRolesResult>(ACTIVE_ROLES_QUERY, {
    skip: sessionLoading || !canRead || !canAssign,
    fetchPolicy: 'network-only',
  })
  const roleOptions = useMemo(
    () => sortRoles(rolesData?.roles ?? []),
    [rolesData],
  )

  const apiError: ApiErrorInfo | null = error ? readApiError(error) : null
  useSessionErrorGuard(apiError)

  const rows = useMemo(() => data?.companyUsers ?? [], [data])

  const counts = useMemo(
    () => ({
      active: rows.filter((row) => row.isActive).length,
      admins: rows.filter((row) => row.isActive && row.isAdmin).length,
      inactive: rows.filter((row) => !row.isActive).length,
    }),
    [rows],
  )

  const visible = useMemo(() => {
    const term = normalizeSearch(search)

    return rows.filter((row) => {
      if (activeOnly && !row.isActive) {
        return false
      }

      if (!term) {
        return true
      }

      return (
        normalizeSearch(row.user?.name ?? '').includes(term) ||
        normalizeSearch(row.user?.email ?? '').includes(term)
      )
    })
  }, [rows, search, activeOnly])

  async function reload(message: string) {
    setNotice(message)
    await refetch()
  }

  return (
    <AdminSection
      id="admin-users-title"
      eyebrow="Dashboard administrativo"
      title="Usuarios"
      lead="¿Quién pertenece a la empresa? Cada fila es una membresía de la empresa de tu sesión."
    >
      {!sessionLoading && !canRead ? (
        <div className="alert alert--warning admin-alert" role="alert">
          <p>Tu rol no tiene el permiso company.users.read para ver los usuarios.</p>
        </div>
      ) : null}

      {canRead ? (
        <>
          <dl className="admin-counters" aria-label="Conteos de usuarios">
            <div className="admin-counter">
              <dt>Usuarios activos</dt>
              <dd>{data ? counts.active : '—'}</dd>
            </div>
            <div
              className={
                counts.admins > 1
                  ? 'admin-counter admin-counter--danger'
                  : 'admin-counter'
              }
            >
              <dt>Administrador principal</dt>
              <dd>{data ? counts.admins : '—'}</dd>
            </div>
            <div className="admin-counter">
              <dt>Inactivos</dt>
              <dd>{data ? counts.inactive : '—'}</dd>
            </div>
          </dl>

          {counts.admins > 1 ? (
            <div className="alert alert--error admin-alert" role="alert">
              <p>
                Error de datos: la empresa tiene {counts.admins} administradores
                principales activos. Debe haber uno solo.
              </p>
            </div>
          ) : null}

          <div className="admin-toolbar">
            <div className="field admin-toolbar__search">
              <label className="field__label" htmlFor="users-search">
                Buscar por nombre o correo
              </label>
              <input
                id="users-search"
                className="field__input"
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>

            <label className="admin-check">
              <input
                type="checkbox"
                checked={activeOnly}
                onChange={(event) => setActiveOnly(event.target.checked)}
              />
              Solo activos
            </label>

            {canWrite && !showForm ? (
              <button
                className="button button--primary admin-button"
                type="button"
                onClick={() => {
                  setShowForm(true)
                  setNotice(null)
                }}
              >
                Nuevo usuario
              </button>
            ) : null}
          </div>

          {notice ? (
            <p className="admin-notice" role="status">
              {notice}
            </p>
          ) : null}

          {canWrite && showForm && companyId !== null ? (
            <NewUserForm
              companyId={companyId}
              onCancel={() => setShowForm(false)}
              onCreated={async (email) => {
                setShowForm(false)
                await reload(`Se agregó a ${email}.`)
              }}
            />
          ) : null}

          <section className="dashboard-panel" aria-labelledby="users-table-title">
            <div className="dashboard-panel__heading">
              <h3 id="users-table-title">Membresías</h3>
              {data ? (
                <p className="dashboard-panel__meta">
                  {`${visible.length} de ${rows.length} membresías`}
                </p>
              ) : null}
            </div>

            <QueryFeedback
              loading={loading || sessionLoading}
              hasData={data !== undefined}
              error={apiError}
              loadingText="Cargando usuarios…"
              onRetry={() => void refetch()}
            />

            {data && rows.length === 0 ? (
              <p className="dashboard-empty" role="status">
                La empresa no tiene usuarios registrados.
              </p>
            ) : null}

            {data && rows.length > 0 && visible.length === 0 ? (
              <p className="dashboard-empty" role="status">
                Ningún usuario coincide con la búsqueda.
              </p>
            ) : null}

            {visible.length > 0 ? (
              <div className="accounts-table-wrapper">
                <table className="accounts-table admin-table">
                  <caption className="dashboard-visually-hidden">
                    Usuarios de la empresa
                  </caption>
                  <thead>
                    <tr>
                      <th scope="col">Nombre</th>
                      <th scope="col">Correo</th>
                      <th scope="col">Rol</th>
                      <th scope="col">Administrador</th>
                      <th scope="col">Estado</th>
                      {canWrite ? <th scope="col">Acciones</th> : null}
                    </tr>
                  </thead>
                  <tbody>
                    {visible.map((row) => (
                      <tr
                        key={row.id}
                        className={row.isActive ? undefined : 'admin-row--inactive'}
                      >
                        <th scope="row" className="accounts-table__account">
                          {row.user?.name ?? '—'}
                        </th>
                        <td data-label="Correo">{row.user?.email ?? '—'}</td>
                        <td data-label="Rol">
                          {canAssign &&
                          row.isActive &&
                          !row.isAdmin &&
                          roleOptions.length > 0 ? (
                            <RoleAssignControl
                              row={row}
                              roles={roleOptions}
                              onAssigned={(message) => reload(message)}
                            />
                          ) : row.role ? (
                            roleLabel(row.role)
                          ) : (
                            <span className="admin-muted">Sin rol</span>
                          )}
                        </td>
                        <td data-label="Administrador">
                          {row.isAdmin ? 'Sí' : 'No'}
                        </td>
                        <td data-label="Estado">
                          <StatusBadge active={row.isActive} />
                        </td>
                        {canWrite ? (
                          <td data-label="Acciones">
                            {row.isActive &&
                            !row.isAdmin &&
                            row.id !== info?.companyUserId ? (
                              <DeactivateAction
                                row={row}
                                onDone={(message) => reload(message)}
                              />
                            ) : (
                              <span className="admin-muted">—</span>
                            )}
                          </td>
                        ) : null}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </section>
        </>
      ) : null}
    </AdminSection>
  )
}
