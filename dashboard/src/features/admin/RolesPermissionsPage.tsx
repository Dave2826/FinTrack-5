import { useApolloClient, useMutation, useQuery } from '@apollo/client'
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  MATRIX_QUERY,
  PREVIEW_ROLE_PERMISSIONS_QUERY,
  ROLE_PERMISSIONS_QUERY,
  SET_ROLE_PERMISSIONS_MUTATION,
} from '../../api/operations/roles'
import { useSessionErrorGuard } from '../../hooks/useSessionErrorGuard'
import { readApiError } from '../../lib/apiErrors'
import type { ApiErrorInfo } from '../../lib/apiErrors'
import {
  grantedPermissionIds,
  groupPermissions,
  isReadOnlyRole,
  permissionLabel,
  permissionWhere,
  roleLabel,
  sameIds,
  sortRoles,
  toPermissionIdList,
} from '../../lib/roleMatrix'
import { useSessionInfo } from '../../session/useSessionInfo'
import type { RoleRef } from '../../types/admin'
import type {
  MatrixResult,
  PermissionCode,
  PreviewResult,
  RolePermissionPlan,
  RolePermissionsResult,
  SetRolePermissionsInput,
  SetRolePermissionsResult,
} from '../../types/roles'
import { AdminSection } from './components/AdminSection'
import { QueryFeedback } from './components/QueryFeedback'

type Columns = Map<number, Set<number>>

interface Notice {
  tone: 'success' | 'info'
  text: string
}

function codes(list: readonly PermissionCode[]): string {
  return list.length > 0 ? list.map((p) => p.code).join(', ') : 'nada'
}

function permisos(count: number): string {
  return count === 1 ? '1 permiso' : `${count} permisos`
}

/** Vista previa de la columna en revisión. No escribe nada. */
function PreviewPanel({
  role,
  plan,
  loading,
  error,
  saving,
  saveError,
  onSave,
  onCancel,
}: {
  role: RoleRef
  plan: RolePermissionPlan | null
  loading: boolean
  error: string | null
  saving: boolean
  saveError: string | null
  onSave: () => void
  onCancel: () => void
}) {
  const label = roleLabel(role)

  return (
    <section
      className="dashboard-panel matrix-preview"
      aria-labelledby="matrix-preview-title"
    >
      <div className="dashboard-panel__heading">
        <h3 id="matrix-preview-title">Vista previa · {label}</h3>
        <p className="dashboard-panel__meta">
          previewRolePermissions · todavía no se guarda nada
        </p>
      </div>

      {loading && !plan ? (
        <p className="dashboard-status" role="status">
          Calculando la vista previa…
        </p>
      ) : null}

      {error ? (
        <div className="alert alert--error admin-alert" role="alert">
          <p>{error}</p>
        </div>
      ) : null}

      {plan ? (
        <dl className="matrix-plan" aria-label={`Vista previa de ${label}`}>
          <div className="matrix-plan__item matrix-plan__item--on">
            <dt>Se activa</dt>
            <dd>{codes(plan.toActivate)}</dd>
          </div>
          <div className="matrix-plan__item matrix-plan__item--off">
            <dt>Se desactiva</dt>
            <dd>{codes(plan.toDeactivate)}</dd>
          </div>
          <div className="matrix-plan__item">
            <dt>Sin cambio</dt>
            <dd>{plan.unchanged.length}</dd>
          </div>
          <div className="matrix-plan__item">
            <dt>Total final</dt>
            <dd>{plan.finalCount}</dd>
          </div>
        </dl>
      ) : null}

      {saveError ? (
        <div className="alert alert--error admin-alert" role="alert">
          <p>{saveError}</p>
        </div>
      ) : null}

      <div className="admin-form__actions">
        <button
          className="button button--primary admin-button"
          type="button"
          onClick={onSave}
          disabled={saving || loading || plan === null}
        >
          {saving ? 'Guardando…' : `Guardar columna ${label}`}
        </button>
        <button
          className="button button--secondary admin-button"
          type="button"
          onClick={onCancel}
          disabled={saving}
        >
          Cancelar
        </button>
      </div>
    </section>
  )
}

/**
 * Roles y permisos: «¿qué puede hacer cada puesto?».
 *
 * Columnas = roles, filas = permisos, celda = la pareja en
 * `role_permissions`. Guardar una columna manda la lista completa a
 * `setRolePermissions` y vuelve a leer esa columna.
 */
export function RolesPermissionsPage() {
  const client = useApolloClient()
  const { can, loading: sessionLoading } = useSessionInfo()
  const canRead = can('roles.read')
  const canWrite = can('roles.write')

  const {
    data,
    loading,
    error,
    refetch,
  } = useQuery<MatrixResult>(MATRIX_QUERY, {
    skip: sessionLoading || !canRead,
    fetchPolicy: 'network-only',
  })

  const matrixError: ApiErrorInfo | null = error ? readApiError(error) : null

  const roles = useMemo(() => sortRoles(data?.roles ?? []), [data])
  const groups = useMemo(
    () => groupPermissions(data?.permissions ?? []),
    [data],
  )
  const activePermissionIds = useMemo(
    () => new Set((data?.permissions ?? []).map((p) => p.id)),
    [data],
  )

  // Columnas leídas de la base, ligadas a la lista de roles que las pidió.
  const [columnsState, setColumnsState] = useState<{
    key: string
    map: Columns | null
    error: ApiErrorInfo | null
  }>({ key: '', map: null, error: null })
  const [drafts, setDrafts] = useState<Columns>(() => new Map())
  const [reviewRoleId, setReviewRoleId] = useState<number | null>(null)
  // Vista previa ligada a la columna y a la lista exacta que se revisó.
  const [planState, setPlanState] = useState<{
    key: string
    plan: RolePermissionPlan | null
    error: string | null
  }>({ key: '', plan: null, error: null })
  const [saveError, setSaveError] = useState<string | null>(null)
  const [notice, setNotice] = useState<Notice | null>(null)

  const [saveColumn, { loading: saving }] = useMutation<
    SetRolePermissionsResult,
    { input: SetRolePermissionsInput }
  >(SET_ROLE_PERMISSIONS_MUTATION)


  const readColumn = useCallback(
    async (roleId: number) => {
      const result = await client.query<
        RolePermissionsResult,
        { roleId: number }
      >({
        query: ROLE_PERMISSIONS_QUERY,
        variables: { roleId },
        fetchPolicy: 'network-only',
      })

      return grantedPermissionIds(
        result.data.rolePermissions,
        activePermissionIds,
      )
    },
    [client, activePermissionIds],
  )

  const rolesKey = roles.map((role) => role.id).join(',')
  const columns = columnsState.key === rolesKey ? columnsState.map : null
  const columnsError =
    columnsState.key === rolesKey ? columnsState.error : null

  useSessionErrorGuard(matrixError ?? columnsError)

  // rolePermissions se consulta por columna.
  useEffect(() => {
    if (roles.length === 0) {
      return
    }

    let cancelled = false
    const key = roles.map((role) => role.id).join(',')

    Promise.all(
      roles.map(async (role) => [role.id, await readColumn(role.id)] as const),
    )
      .then((entries) => {
        if (!cancelled) {
          setColumnsState({ key, map: new Map(entries), error: null })
        }
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setColumnsState({ key, map: null, error: readApiError(caught) })
        }
      })

    return () => {
      cancelled = true
    }
  }, [roles, readColumn])

  const reviewRole = roles.find((role) => role.id === reviewRoleId) ?? null

  function listFor(roleId: number): Set<number> {
    return drafts.get(roleId) ?? columns?.get(roleId) ?? new Set()
  }

  const reviewList =
    reviewRoleId === null ? null : toPermissionIdList(listFor(reviewRoleId))
  const reviewKey = reviewList?.join(',') ?? null
  const planKey = reviewRoleId === null ? '' : `${reviewRoleId}:${reviewKey}`
  const planCurrent = planKey !== '' && planState.key === planKey
  const plan = planCurrent ? planState.plan : null
  const planError = planCurrent ? planState.error : null
  const planLoading = planKey !== '' && !planCurrent

  // La vista previa se recalcula cada vez que cambia la lista en revisión.
  useEffect(() => {
    if (reviewRoleId === null || reviewKey === null) {
      return
    }

    let cancelled = false
    const key = `${reviewRoleId}:${reviewKey}`

    client
      .query<PreviewResult, { input: SetRolePermissionsInput }>({
        query: PREVIEW_ROLE_PERMISSIONS_QUERY,
        variables: {
          input: {
            roleId: String(reviewRoleId),
            permissionIds: reviewKey ? reviewKey.split(',') : [],
          },
        },
        fetchPolicy: 'network-only',
      })
      .then((result) => {
        if (!cancelled) {
          setPlanState({
            key,
            plan: result.data.previewRolePermissions,
            error: null,
          })
        }
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setPlanState({ key, plan: null, error: readApiError(caught).message })
        }
      })

    return () => {
      cancelled = true
    }
  }, [client, reviewRoleId, reviewKey])

  function toggle(role: RoleRef, permissionId: number) {
    if (!canWrite || isReadOnlyRole(role) || saving) {
      return
    }

    setNotice(null)
    setSaveError(null)

    const next = new Set(listFor(role.id))

    if (next.has(permissionId)) {
      next.delete(permissionId)
    } else {
      next.add(permissionId)
    }

    setDrafts((current) => {
      const copy = new Map(current)
      const saved = columns?.get(role.id)

      if (saved && sameIds(saved, next)) {
        copy.delete(role.id)
      } else {
        copy.set(role.id, next)
      }

      return copy
    })
  }

  function discard(roleId: number) {
    setDrafts((current) => {
      const copy = new Map(current)
      copy.delete(roleId)
      return copy
    })

    if (reviewRoleId === roleId) {
      setReviewRoleId(null)
    }
  }

  async function save() {
    if (reviewRole === null || reviewList === null) {
      return
    }

    setSaveError(null)
    const label = roleLabel(reviewRole)

    try {
      const result = await saveColumn({
        variables: {
          input: {
            roleId: String(reviewRole.id),
            permissionIds: reviewList,
          },
        },
      })
      const summary = result.data?.setRolePermissions

      // Si salió bien, la columna se vuelve a leer de la base.
      const fresh = await readColumn(reviewRole.id)
      setColumnsState((current) => {
        const copy = new Map(current.map ?? [])
        copy.set(reviewRole.id, fresh)
        return { ...current, map: copy }
      })
      discard(reviewRole.id)
      setReviewRoleId(null)

      if (!summary) {
        setNotice({ tone: 'info', text: `Se guardó la columna ${label}.` })
      } else if (!summary.changed) {
        setNotice({
          tone: 'info',
          text: `${label}: la columna ya tenía esa lista. setRolePermissions respondió changed: false y no se duplicaron filas. Total final: ${summary.finalCount}.`,
        })
      } else {
        setNotice({
          tone: 'success',
          text: `Se guardó la columna ${label}. Se activó: ${codes(summary.activated)}. Se desactivó: ${codes(summary.deactivated)}. Total final: ${summary.finalCount}. Aplica a todas las personas con ese puesto.`,
        })
      }
    } catch (caught) {
      setSaveError(readApiError(caught).message)
    }
  }

  const catalogEmpty =
    data !== undefined && (roles.length === 0 || groups.length === 0)
  const ready = data !== undefined && !catalogEmpty && columns !== null

  return (
    <AdminSection
      id="admin-roles-title"
      eyebrow="Dashboard administrativo"
      title="Roles y permisos"
      lead="¿Qué puede hacer cada puesto? Cada celda es la pareja (rol, permiso) en role_permissions."
    >
      {!sessionLoading && !canRead ? (
        <div className="alert alert--warning admin-alert" role="alert">
          <p>Tu rol no tiene el permiso roles.read para ver la matriz.</p>
        </div>
      ) : null}

      {canRead ? (
        <>
          <div className="alert alert--info admin-alert matrix-shared">
            <p>
              <strong>Catálogo compartido.</strong> La lista de cada puesto vale
              en todas las empresas: cambiar una columna cambia las pantallas de
              todas las personas con ese puesto. El puesto de una persona se
              cambia en Usuarios, columna Rol.
            </p>
          </div>

          {!canWrite ? (
            <p className="admin-notice matrix-readonly" role="status">
              Tu rol tiene roles.read sin roles.write: ves la matriz en solo
              lectura y no puedes guardarla.
            </p>
          ) : null}

          {notice ? (
            <p
              className={
                notice.tone === 'success'
                  ? 'admin-notice'
                  : 'admin-notice admin-notice--info'
              }
              role="status"
            >
              {notice.text}
            </p>
          ) : null}

          <section
            className="dashboard-panel"
            aria-labelledby="matrix-table-title"
          >
            <div className="dashboard-panel__heading">
              <h3 id="matrix-table-title">Matriz</h3>
              {data && !catalogEmpty ? (
                <p className="dashboard-panel__meta">
                  {`${roles.length} roles · ${data.permissions.length} permisos activos`}
                </p>
              ) : null}
            </div>

            <QueryFeedback
              loading={loading || sessionLoading}
              hasData={data !== undefined}
              error={matrixError}
              loadingText="Cargando la matriz…"
              onRetry={() => void refetch()}
            />

            {catalogEmpty ? (
              <p className="dashboard-empty" role="status">
                El catálogo de roles y permisos no está cargado.
              </p>
            ) : null}

            {columnsError ? (
              <QueryFeedback
                loading={false}
                hasData={false}
                error={columnsError}
                loadingText=""
                onRetry={() => void refetch()}
              />
            ) : null}

            {data && !catalogEmpty && columns === null && !columnsError ? (
              <p className="dashboard-status" role="status">
                Cargando las columnas…
              </p>
            ) : null}

            {ready ? (
              <div className="matrix-wrapper">
                <table className="matrix-table">
                  <caption className="dashboard-visually-hidden">
                    Matriz de roles y permisos
                  </caption>
                  <thead>
                    <tr>
                      <th scope="col" className="matrix-table__corner">
                        Permiso
                      </th>
                      {roles.map((role) => (
                        <th
                          key={role.id}
                          scope="col"
                          className={
                            isReadOnlyRole(role)
                              ? 'matrix-table__role matrix-table__role--locked'
                              : 'matrix-table__role'
                          }
                        >
                          <span>{roleLabel(role)}</span>
                          <span className="admin-subtext">{role.code}</span>
                          {isReadOnlyRole(role) ? (
                            <span className="matrix-lock">Solo lectura</span>
                          ) : null}
                        </th>
                      ))}
                    </tr>
                  </thead>

                  {groups.map((group) => (
                    <tbody key={group.label}>
                      <tr className="matrix-table__group">
                        <th scope="colgroup" colSpan={roles.length + 1}>
                          {group.label}
                        </th>
                      </tr>
                      {group.permissions.map((permission) => {
                        const rowLabel = permissionLabel(permission)
                        const where = permissionWhere(permission.code)

                        return (
                          <tr key={permission.id}>
                            <th scope="row" className="matrix-table__permission">
                              <span>{rowLabel}</span>
                              <span className="admin-subtext">
                                {permission.code}
                                {where ? ` · ${where}` : ''}
                              </span>
                            </th>
                            {roles.map((role) => {
                              const saved =
                                columns.get(role.id)?.has(permission.id) ?? false
                              const current = listFor(role.id).has(permission.id)
                              const locked =
                                !canWrite || isReadOnlyRole(role) || saving
                              const changed = current !== saved

                              return (
                                <td
                                  key={role.id}
                                  className={[
                                    'matrix-cell',
                                    current ? 'matrix-cell--yes' : 'matrix-cell--no',
                                    changed ? 'matrix-cell--changed' : '',
                                    isReadOnlyRole(role) ? 'matrix-cell--locked' : '',
                                  ]
                                    .filter(Boolean)
                                    .join(' ')}
                                >
                                  <label className="matrix-cell__control">
                                    <input
                                      type="checkbox"
                                      checked={current}
                                      disabled={locked}
                                      onChange={() => toggle(role, permission.id)}
                                      aria-label={`${roleLabel(role)}: ${rowLabel}`}
                                    />
                                    <span aria-hidden="true">
                                      {current ? 'Sí' : 'No'}
                                    </span>
                                  </label>
                                </td>
                              )
                            })}
                          </tr>
                        )
                      })}
                    </tbody>
                  ))}

                  <tfoot>
                    <tr>
                      <th scope="row">Total y acciones</th>
                      {roles.map((role) => {
                        const pending = drafts.has(role.id)
                        const editable = canWrite && !isReadOnlyRole(role)
                        const label = roleLabel(role)

                        return (
                          <td key={role.id} className="matrix-table__actions">
                            <span className="matrix-total">
                              {permisos(listFor(role.id).size)}
                            </span>
                            {pending ? (
                              <span className="matrix-pending">Sin guardar</span>
                            ) : null}
                            {editable ? (
                              <>
                                <button
                                  className="button button--primary admin-button admin-button--small"
                                  type="button"
                                  onClick={() => {
                                    setNotice(null)
                                    setSaveError(null)
                                    setReviewRoleId(role.id)
                                  }}
                                  disabled={saving}
                                  aria-label={`Revisar y guardar ${label}`}
                                >
                                  Revisar y guardar
                                </button>
                                {pending ? (
                                  <button
                                    className="button button--secondary admin-button admin-button--small"
                                    type="button"
                                    onClick={() => discard(role.id)}
                                    disabled={saving}
                                    aria-label={`Descartar cambios de ${label}`}
                                  >
                                    Descartar
                                  </button>
                                ) : null}
                              </>
                            ) : null}
                          </td>
                        )
                      })}
                    </tr>
                  </tfoot>
                </table>
              </div>
            ) : null}
          </section>

          {canWrite && reviewRole ? (
            <PreviewPanel
              role={reviewRole}
              plan={plan}
              loading={planLoading}
              error={planError}
              saving={saving}
              saveError={saveError}
              onSave={() => void save()}
              onCancel={() => {
                setReviewRoleId(null)
                setSaveError(null)
              }}
            />
          ) : null}
        </>
      ) : null}
    </AdminSection>
  )
}
