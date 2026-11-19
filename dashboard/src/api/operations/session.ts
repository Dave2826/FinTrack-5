import { gql } from '@apollo/client'

/**
 * Identidad de la sesión: empresa, persona, rol y permisos efectivos.
 *
 * El dashboard la usa para pintar el nombre de la empresa y decidir qué
 * acciones de alta dibuja. El backend sigue autorizando cada operación.
 */
export const ME_QUERY = gql`
  query Me {
    me {
      companyUserId
      isAdmin
      permissions
      company {
        id
        name
      }
      user {
        id
        name
        email
      }
      role {
        id
        code
        name
      }
    }
  }
`
