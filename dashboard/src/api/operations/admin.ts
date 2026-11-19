import { gql } from '@apollo/client'

/**
 * Operaciones del dashboard administrativo (Unidad III, Actividad 13).
 *
 * Cada tabla es una query y cada botón Guardar es una mutation del esquema
 * existente. `companyId` sale de la sesión (`me`), nunca de un campo libre.
 * Ninguna consulta pide la contraseña: el campo no existe en el esquema.
 */

export const COMPANY_USERS_QUERY = gql`
  query CompanyUsers($companyId: Int!) {
    companyUsers(companyId: $companyId, activeOnly: false) {
      id
      isAdmin
      isActive
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

export const CREATE_COMPANY_USER_MUTATION = gql`
  mutation CreateCompanyUser($input: CreateCompanyUserInput!) {
    createCompanyUser(input: $input) {
      id
      isAdmin
      isActive
      user {
        id
        name
        email
      }
    }
  }
`

export const DEACTIVATE_COMPANY_USER_MUTATION = gql`
  mutation DeactivateCompanyUser($companyUserId: Int!) {
    deactivateCompanyUser(companyUserId: $companyUserId) {
      id
      isActive
    }
  }
`

export const ACCOUNTS_QUERY = gql`
  query AdminAccounts($companyId: Int!, $activeOnly: Boolean!) {
    accounts(companyId: $companyId, activeOnly: $activeOnly) {
      id
      name
      accountType
      bankName
      clabe
      cardLastDigits
      shortDescription
      isActive
    }
  }
`

export const CREATE_ACCOUNT_MUTATION = gql`
  mutation NuevaCuenta($input: CreateAccountInput!) {
    createAccount(input: $input) {
      id
      name
      accountType
      isActive
    }
  }
`

export const CONCEPTS_QUERY = gql`
  query AdminConcepts($companyId: Int!, $activeOnly: Boolean!) {
    concepts(companyId: $companyId, activeOnly: $activeOnly) {
      id
      name
      conceptType
      shortDescription
      isActive
    }
  }
`

export const CREATE_CONCEPT_MUTATION = gql`
  mutation NuevoConcepto($input: CreateConceptInput!) {
    createConcept(input: $input) {
      id
      name
      conceptType
      isActive
    }
  }
`

export const ACCOUNT_CONCEPTS_QUERY = gql`
  query AccountConcepts($accountId: Int!) {
    accountConcepts(accountId: $accountId) {
      id
      isActive
      concept {
        id
        name
        conceptType
      }
    }
  }
`

export const ASSIGN_CONCEPT_MUTATION = gql`
  mutation AssignConceptToAccount($input: AssignConceptToAccountInput!) {
    assignConceptToAccount(input: $input) {
      id
      isActive
    }
  }
`

export const REMOVE_CONCEPT_MUTATION = gql`
  mutation RemoveConceptFromAccount($accountId: Int!, $conceptId: Int!) {
    removeConceptFromAccount(accountId: $accountId, conceptId: $conceptId) {
      id
      isActive
    }
  }
`
