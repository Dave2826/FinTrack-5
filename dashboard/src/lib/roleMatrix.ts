import type { PermissionRef, RolePermissionRow } from '../types/roles'

/**
 * Reglas de presentación de la matriz (enunciado, sección 2).
 *
 * El orden de columnas y de grupos lo fija el enunciado, no el orden en que
 * el API devuelva los registros.
 */

/** Orden de las columnas. Un rol que no esté aquí va al final. */
export const ROLE_ORDER = [
  'ADMINISTRADOR',
  'CONTADOR',
  'CAPTURISTA',
  'CONSULTA',
] as const

/** La columna que se ve y no se edita. setRolePermissions ya la rechaza. */
export const READ_ONLY_ROLE = 'ADMINISTRADOR'

const ROLE_LABELS: Record<string, string> = {
  ADMINISTRADOR: 'Administrador',
  CONTADOR: 'Contador',
  CAPTURISTA: 'Capturista',
  CONSULTA: 'Consulta',
}

export interface PermissionGroupSpec {
  label: string
  codes: readonly string[]
}

/** Grupos por recurso; dentro del grupo, la lectura antes que la escritura. */
export const PERMISSION_GROUPS: readonly PermissionGroupSpec[] = [
  { label: 'Usuarios', codes: ['company.users.read', 'company.users.write'] },
  { label: 'Cuentas', codes: ['accounts.read', 'accounts.write'] },
  { label: 'Conceptos', codes: ['concepts.read', 'concepts.write'] },
  { label: 'Movimientos', codes: ['transactions.read', 'transactions.write'] },
  { label: 'Roles', codes: ['roles.read', 'roles.write'] },
]

/** Nombre de la fila y dónde se nota un «sí» (tabla de la sección 2). */
const PERMISSION_INFO: Record<string, { label: string; where: string }> = {
  'company.users.read': { label: 'Ver usuarios', where: 'Tabla de Usuarios' },
  'company.users.write': {
    label: 'Administrar usuarios',
    where: 'Nuevo usuario y Desactivar',
  },
  'accounts.read': { label: 'Ver cuentas', where: 'Tabla de Cuentas' },
  'accounts.write': { label: 'Crear cuentas', where: 'Nueva cuenta' },
  'concepts.read': {
    label: 'Ver conceptos',
    where: 'Catálogo y lista de la cuenta',
  },
  'concepts.write': {
    label: 'Administrar conceptos',
    where: 'Nuevo concepto, Asignar y Quitar',
  },
  'transactions.read': {
    label: 'Ver movimientos',
    where: 'Dashboard financiero',
  },
  'transactions.write': {
    label: 'Registrar movimientos',
    where: 'Alta de un ingreso o un egreso',
  },
  'roles.read': {
    label: 'Ver la matriz',
    where: 'Esta pantalla, en solo lectura',
  },
  'roles.write': {
    label: 'Cambiar la matriz y asignar puestos',
    where: 'Celdas editables y el selector de Rol',
  },
}

/**
 * Nombre visible de un rol. Si en la base el `name` es solo el código
 * (como en el catálogo inicial del Parcial II), se usa la etiqueta del
 * enunciado; si el equipo le dio un nombre propio, se respeta.
 */
export function roleLabel(role: { code: string; name: string }): string {
  if (role.name && role.name !== role.code) {
    return role.name
  }

  return ROLE_LABELS[role.code] ?? role.name ?? role.code
}

/** Nombre de la fila: el `name` del permiso, o la etiqueta del enunciado. */
export function permissionLabel(permission: {
  code: string
  name: string
}): string {
  if (permission.name && permission.name !== permission.code) {
    return permission.name
  }

  return PERMISSION_INFO[permission.code]?.label ?? permission.code
}

export function permissionWhere(code: string): string | null {
  return PERMISSION_INFO[code]?.where ?? null
}

export function sortRoles<T extends { code: string; id: number }>(
  roles: readonly T[],
): T[] {
  const rank = (code: string) => {
    const index = (ROLE_ORDER as readonly string[]).indexOf(code)
    return index === -1 ? ROLE_ORDER.length : index
  }

  return [...roles].sort(
    (a, b) => rank(a.code) - rank(b.code) || a.id - b.id,
  )
}

export function isReadOnlyRole(role: { code: string }): boolean {
  return role.code === READ_ONLY_ROLE
}

export interface PermissionGroup {
  label: string
  permissions: PermissionRef[]
}

/**
 * Agrupa los permisos activos en el orden del enunciado. Un permiso activo
 * que no pertenezca a ningún grupo conocido se muestra al final en «Otros»,
 * para que ninguna fila de la base quede oculta.
 */
export function groupPermissions(
  permissions: readonly PermissionRef[],
): PermissionGroup[] {
  const byCode = new Map(permissions.map((p) => [p.code, p]))
  const used = new Set<string>()
  const groups: PermissionGroup[] = []

  for (const spec of PERMISSION_GROUPS) {
    const rows = spec.codes
      .map((code) => byCode.get(code))
      .filter((p): p is PermissionRef => p !== undefined)

    rows.forEach((p) => used.add(p.code))

    if (rows.length > 0) {
      groups.push({ label: spec.label, permissions: rows })
    }
  }

  const others = permissions
    .filter((p) => !used.has(p.code))
    .sort((a, b) => a.code.localeCompare(b.code))

  if (others.length > 0) {
    groups.push({ label: 'Otros', permissions: others })
  }

  return groups
}

/**
 * Una celda es «sí» solo si la relación está activa y el permiso sigue
 * activo en el catálogo. Sin fila, o con la fila inactiva, es «no»: la
 * denegación por defecto.
 */
export function grantedPermissionIds(
  relations: readonly RolePermissionRow[],
  activePermissionIds: ReadonlySet<number>,
): Set<number> {
  const granted = new Set<number>()

  for (const relation of relations) {
    const permissionId = relation.permission?.id ?? relation.permissionId

    if (relation.isActive && activePermissionIds.has(permissionId)) {
      granted.add(permissionId)
    }
  }

  return granted
}

export function sameIds(
  a: ReadonlySet<number>,
  b: ReadonlySet<number>,
): boolean {
  if (a.size !== b.size) {
    return false
  }

  for (const id of a) {
    if (!b.has(id)) {
      return false
    }
  }

  return true
}

/** Lista completa que se manda a setRolePermissions, en orden estable. */
export function toPermissionIdList(ids: ReadonlySet<number>): string[] {
  return [...ids].sort((a, b) => a - b).map(String)
}
