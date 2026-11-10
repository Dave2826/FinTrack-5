/**
 * Tipos del contrato de autenticación expuesto por el backend GraphQL.
 *
 * No se añaden campos ni argumentos distintos a los del esquema real.
 */

export interface LoginInput {
  email: string
  password: string
}

export interface AuthUser {
  id: string
  name: string
  email: string
}

export interface LoginPayload {
  token: string
  tokenType: string
  user: AuthUser
}

export interface LoginResult {
  login: LoginPayload
}

export interface LoginVariables {
  input: LoginInput
}
