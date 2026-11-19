/**
 * Tipos del contrato GraphQL del dashboard administrativo.
 * Reflejan exactamente los campos que piden las operaciones de `admin.ts`.
 */

export type AccountType =
  | 'CASH'
  | 'DEBIT'
  | 'CREDIT'
  | 'SAVINGS'
  | 'INVESTMENT'
  | 'WALLET'
  | 'OTHER'

export type ConceptType = 'INCOME' | 'EXPENSE'

export interface RoleRef {
  id: number
  code: string
  name: string
}

export interface SessionInfo {
  companyUserId: number
  isAdmin: boolean
  permissions: string[]
  company: { id: number; name: string }
  user: { id: number; name: string; email: string }
  role: RoleRef | null
}

export interface MeResult {
  me: SessionInfo
}

export interface CompanyUserRow {
  id: number
  isAdmin: boolean
  isActive: boolean
  user: { id: number; name: string; email: string } | null
  role: RoleRef | null
}

export interface CompanyUsersResult {
  companyUsers: CompanyUserRow[]
}

export interface CreateCompanyUserInput {
  companyId: number
  name: string
  email: string
  password: string
}

export interface AdminAccount {
  id: number
  name: string
  accountType: AccountType
  bankName: string | null
  clabe: string | null
  cardLastDigits: string | null
  shortDescription: string | null
  isActive: boolean
}

export interface AdminAccountsResult {
  accounts: AdminAccount[]
}

export interface CreateAccountInput {
  companyId: number
  accountType: AccountType
  name: string
  bankName?: string | null
  clabe?: string | null
  shortDescription?: string | null
}

export interface AdminConcept {
  id: number
  name: string
  conceptType: ConceptType
  shortDescription: string | null
  isActive: boolean
}

export interface AdminConceptsResult {
  concepts: AdminConcept[]
}

export interface CreateConceptInput {
  companyId: number
  conceptType: ConceptType
  name: string
  shortDescription?: string | null
}

export interface AccountConceptRow {
  id: number
  isActive: boolean
  concept: { id: number; name: string; conceptType: ConceptType } | null
}

export interface AccountConceptsResult {
  accountConcepts: AccountConceptRow[]
}
