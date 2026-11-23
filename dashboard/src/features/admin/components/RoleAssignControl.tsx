import { useMutation } from '@apollo/client'
import { useState } from 'react'
import { ASSIGN_ROLE_MUTATION } from '../../../api/operations/roles'
import { readApiError } from '../../../lib/apiErrors'
import { roleLabel } from '../../../lib/roleMatrix'
import type { CompanyUserRow, RoleRef } from '../../../types/admin'
import type { AssignRoleInput, AssignRoleResult } from '../../../types/roles'

interface RoleAssignControlProps {
  row: CompanyUserRow
  roles: readonly RoleRef[]
  onAssigned: (message: string) => Promise<void>
}

/**
 * Columna Rol de Usuarios con roles.write: el texto del puesto actual y un
 * selector que llama a `assignRole`. El API deja un solo rol activo y no
 * toca isAdmin. Si rechaza, el error se lee aquí y el puesto anterior se
 * queda.
 */
export function RoleAssignControl({
  row,
  roles,
  onAssigned,
}: RoleAssignControlProps) {
  const currentId = row.role?.id ?? null
  const [selected, setSelected] = useState<string>(
    currentId === null ? '' : String(currentId),
  )
  const [shown, setShown] = useState<RoleRef | null>(row.role)
  const [error, setError] = useState<string | null>(null)
  const [assignRole, { loading }] = useMutation<
    AssignRoleResult,
    { input: AssignRoleInput }
  >(ASSIGN_ROLE_MUTATION)

  const name = row.user?.name ?? `Membresía #${row.id}`
  const selectId = `role-select-${row.id}`
  const unchanged = selected === '' || Number(selected) === shown?.id

  async function save() {
    setError(null)

    try {
      const result = await assignRole({
        variables: {
          input: { companyUserId: row.id, roleId: Number(selected) },
        },
      })
      const role = result.data?.assignRole.role ?? null

      // La celda muestra lo que devolvió la mutación.
      setShown(role)

      if (role) {
        setSelected(String(role.id))
      }

      await onAssigned(
        `${name} ahora tiene el puesto ${role ? roleLabel(role) : 'asignado'}. isAdmin no cambió.`,
      )
    } catch (caught) {
      setError(readApiError(caught).message)
      setSelected(shown === null ? '' : String(shown.id))
    }
  }

  return (
    <div className="role-assign">
      <span className="role-assign__current">
        {shown ? roleLabel(shown) : <span className="admin-muted">Sin rol</span>}
      </span>
      <div className="role-assign__controls">
        <label className="dashboard-visually-hidden" htmlFor={selectId}>
          {`Puesto de ${name}`}
        </label>
        <select
          id={selectId}
          className="field__input role-assign__select"
          value={selected}
          onChange={(event) => {
            setSelected(event.target.value)
            setError(null)
          }}
          disabled={loading}
        >
          {shown === null ? <option value="">Elegir puesto…</option> : null}
          {roles.map((role) => (
            <option key={role.id} value={String(role.id)}>
              {roleLabel(role)}
            </option>
          ))}
        </select>
        <button
          className="button button--secondary admin-button admin-button--small"
          type="button"
          onClick={() => void save()}
          disabled={loading || unchanged}
          aria-label={`Guardar puesto de ${name}`}
        >
          {loading ? 'Guardando…' : 'Guardar'}
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
