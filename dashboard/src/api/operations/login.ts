import { gql } from '@apollo/client'

/**
 * Mutación de autenticación.
 *
 * Contrato exacto del backend: `login(input: LoginInput!)` devuelve
 * `token`, `tokenType` y `user { id name email }`.
 */
export const LOGIN_MUTATION = gql`
  mutation Login($input: LoginInput!) {
    login(input: $input) {
      token
      tokenType
      user {
        id
        name
        email
      }
    }
  }
`
