/**
 * Tipos del contrato GraphQL de la matriz de roles y permisos.
 * Reflejan los campos que piden las operaciones de `api/operations/roles.ts`.
 */

import type { RoleRef } from './admin'

export interface PermissionRef {
  id: number
  code: string
  name: string
}

export interface MatrixResult {
  roles: RoleRef[]
  permissions: PermissionRef[]
}

export interface RolePermissionRow {
  id: number
  isActive: boolean
  permissionId: number
  permission: { id: number; code: string } | null
}

export interface RolePermissionsResult {
  rolePermissions: RolePermissionRow[]
}

/** `SetRolePermissionsInput`: los id viajan como `ID` (texto). */
export interface SetRolePermissionsInput {
  roleId: string
  permissionIds: string[]
}

export interface PermissionCode {
  id: number
  code: string
}

export interface RolePermissionPlan {
  toActivate: PermissionCode[]
  toDeactivate: PermissionCode[]
  unchanged: PermissionCode[]
  finalCount: number
}

export interface PreviewResult {
  previewRolePermissions: RolePermissionPlan | null
}

export interface RolePermissionUpdate {
  activated: PermissionCode[]
  deactivated: PermissionCode[]
  finalCount: number
  changed: boolean
}

export interface SetRolePermissionsResult {
  setRolePermissions: RolePermissionUpdate | null
}

export interface ActiveRolesResult {
  roles: RoleRef[]
}

export interface AssignRoleInput {
  companyUserId: number
  roleId: number
}

export interface AssignRoleResult {
  assignRole: {
    id: number
    isActive: boolean
    role: RoleRef | null
  }
}
