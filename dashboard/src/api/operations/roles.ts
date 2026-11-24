import { gql } from '@apollo/client'

/**
 * Operaciones de la matriz de roles y permisos (Unidad III, Actividad 14).
 *
 * El token viaja en `Authorization` (authLink). Ninguna operación recibe
 * `actorCompanyUserId`: el backend saca la membresía del token y vuelve a
 * leer el rol en la base en cada petición.
 */

/** Columnas (roles) y filas (permisos) activas de la matriz. */
export const MATRIX_QUERY = gql`
  query Matriz {
    roles(activeOnly: true) {
      id
      code
      name
    }
    permissions(activeOnly: true) {
      id
      code
      name
    }
  }
`

/** Una columna: las relaciones activas del rol en `role_permissions`. */
export const ROLE_PERMISSIONS_QUERY = gql`
  query ListaDelRol($roleId: Int!) {
    rolePermissions(roleId: $roleId) {
      id
      isActive
      permissionId
      permission {
        id
        code
      }
    }
  }
`

/** Vista previa de la lista completa de una columna. No escribe. */
export const PREVIEW_ROLE_PERMISSIONS_QUERY = gql`
  query VistaPrevia($input: SetRolePermissionsInput!) {
    previewRolePermissions(input: $input) {
      toActivate {
        id
        code
      }
      toDeactivate {
        id
        code
      }
      unchanged {
        id
        code
      }
      finalCount
    }
  }
`

/** Guarda la lista completa de permisos activos de una columna. */
export const SET_ROLE_PERMISSIONS_MUTATION = gql`
  mutation GuardarColumna($input: SetRolePermissionsInput!) {
    setRolePermissions(input: $input) {
      activated {
        id
        code
      }
      deactivated {
        id
        code
      }
      finalCount
      changed
    }
  }
`

/** Roles activos para el selector de la columna Rol en Usuarios. */
export const ACTIVE_ROLES_QUERY = gql`
  query RolesActivos {
    roles(activeOnly: true) {
      id
      code
      name
    }
  }
`

/** Cambia el puesto de una membresía. El API deja un solo rol activo. */
export const ASSIGN_ROLE_MUTATION = gql`
  mutation AsignarPuesto($input: AssignRoleInput!) {
    assignRole(input: $input) {
      id
      isActive
      role {
        id
        code
        name
      }
    }
  }
`
