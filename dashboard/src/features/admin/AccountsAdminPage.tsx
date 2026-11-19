import { useMutation, useQuery } from '@apollo/client'
import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import {
  ACCOUNTS_QUERY,
  CREATE_ACCOUNT_MUTATION,
} from '../../api/operations/admin'
import { useSessionErrorGuard } from '../../hooks/useSessionErrorGuard'
import {
  ACCOUNT_TYPES,
  ACCOUNT_TYPE_LABELS,
  accountReference,
  accountTypeLabel,
} from '../../lib/adminLabels'
import { readApiError } from '../../lib/apiErrors'
import { useSessionInfo } from '../../session/useSessionInfo'
import type {
  AccountType,
  AdminAccountsResult,
  CreateAccountInput,
} from '../../types/admin'
import { AdminSection } from './components/AdminSection'
import { QueryFeedback } from './components/QueryFeedback'
import { StatusBadge } from './components/StatusBadge'

interface AccountForm {
  name: string
  accountType: AccountType
  bankName: string
  clabe: string
  shortDescription: string
}

const EMPTY_FORM: AccountForm = {
  name: '',
  accountType: 'CASH',
  bankName: '',
  clabe: '',
  shortDescription: '',
}

type FormErrors = Partial<Record<keyof AccountForm, string>>

function validate(form: AccountForm): FormErrors {
  const errors: FormErrors = {}

  if (!form.name.trim()) {
    errors.name = 'Escribe el nombre de la cuenta.'
  }

  const clabe = form.clabe.replace(/\s+/g, '')

  if (clabe && !/^\d{18}$/.test(clabe)) {
    errors.clabe = 'La CLABE tiene 18 dígitos. Déjala vacía si no aplica.'
  }

  return errors
}

function blankToNull(value: string): string | null {
  const trimmed = value.trim()
  return trimmed ? trimmed : null
}

function NewAccountForm({
  companyId,
  onCreated,
  onCancel,
}: {
  companyId: number
  onCreated: (name: string) => Promise<void>
  onCancel: () => void
}) {
  const [form, setForm] = useState<AccountForm>(EMPTY_FORM)
  const [errors, setErrors] = useState<FormErrors>({})
  const [apiError, setApiError] = useState<string | null>(null)
  const [createAccount, { loading }] = useMutation<
    unknown,
    { input: CreateAccountInput }
  >(CREATE_ACCOUNT_MUTATION)

  function update<K extends keyof AccountForm>(field: K, value: AccountForm[K]) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setApiError(null)

    const nextErrors = validate(form)
    setErrors(nextErrors)

    if (Object.keys(nextErrors).length > 0) {
      return
    }

    try {
      await createAccount({
        variables: {
          input: {
            companyId,
            accountType: form.accountType,
            name: form.name.trim(),
            bankName: blankToNull(form.bankName),
            clabe: blankToNull(form.clabe.replace(/\s+/g, '')),
            shortDescription: blankToNull(form.shortDescription),
          },
        },
      })
      const name = form.name.trim()
      setForm(EMPTY_FORM)
      await onCreated(name)
    } catch (error) {
      setApiError(readApiError(error).message)
    }
  }

  return (
    <form
      className="admin-form"
      aria-labelledby="new-account-title"
      noValidate
      onSubmit={(event) => void handleSubmit(event)}
    >
      <h3 id="new-account-title">Nueva cuenta</h3>
      <p className="admin-form__hint">
        Banco y CLABE pueden quedar vacíos en una cuenta de efectivo, como Caja.
      </p>

      <div className="admin-form__grid">
        <div className="field">
          <label className="field__label" htmlFor="new-account-name">
            Nombre
          </label>
          <input
            id="new-account-name"
            className="field__input"
            value={form.name}
            onChange={(event) => update('name', event.target.value)}
            aria-invalid={errors.name ? true : undefined}
            aria-describedby={errors.name ? 'new-account-name-error' : undefined}
          />
          {errors.name ? (
            <p className="field__error" id="new-account-name-error">
              {errors.name}
            </p>
          ) : null}
        </div>

        <div className="field">
          <label className="field__label" htmlFor="new-account-type">
            Tipo
          </label>
          <select
            id="new-account-type"
            className="field__input"
            value={form.accountType}
            onChange={(event) =>
              update('accountType', event.target.value as AccountType)
            }
          >
            {ACCOUNT_TYPES.map((type) => (
              <option key={type} value={type}>
                {ACCOUNT_TYPE_LABELS[type]}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label className="field__label" htmlFor="new-account-bank">
            Banco
          </label>
          <input
            id="new-account-bank"
            className="field__input"
            value={form.bankName}
            onChange={(event) => update('bankName', event.target.value)}
          />
        </div>

        <div className="field">
          <label className="field__label" htmlFor="new-account-clabe">
            CLABE
          </label>
          <input
            id="new-account-clabe"
            className="field__input"
            inputMode="numeric"
            value={form.clabe}
            onChange={(event) => update('clabe', event.target.value)}
            aria-invalid={errors.clabe ? true : undefined}
            aria-describedby={
              errors.clabe ? 'new-account-clabe-error' : undefined
            }
            autoComplete="off"
          />
          {errors.clabe ? (
            <p className="field__error" id="new-account-clabe-error">
              {errors.clabe}
            </p>
          ) : null}
        </div>

        <div className="field admin-form__wide">
          <label className="field__label" htmlFor="new-account-description">
            Descripción corta
          </label>
          <input
            id="new-account-description"
            className="field__input"
            maxLength={255}
            value={form.shortDescription}
            onChange={(event) => update('shortDescription', event.target.value)}
          />
        </div>
      </div>

      {apiError ? (
        <div className="alert alert--error admin-alert" role="alert">
          <p>{apiError}</p>
        </div>
      ) : null}

      <div className="admin-form__actions">
        <button
          className="button button--primary admin-button"
          type="submit"
          disabled={loading}
        >
          {loading ? 'Guardando…' : 'Guardar cuenta'}
        </button>
        <button
          className="button button--secondary admin-button"
          type="button"
          onClick={onCancel}
          disabled={loading}
        >
          Cancelar
        </button>
      </div>
    </form>
  )
}

/** Cuentas: ¿dónde está el dinero? Lista de `accounts` de la empresa. */
export function AccountsAdminPage() {
  const { companyId, can, loading: sessionLoading } = useSessionInfo()
  const canRead = can('accounts.read')
  const canWrite = can('accounts.write')

  const [typeFilter, setTypeFilter] = useState<AccountType | 'ALL'>('ALL')
  const [activeOnly, setActiveOnly] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  const { data, loading, error, refetch } = useQuery<
    AdminAccountsResult,
    { companyId: number; activeOnly: boolean }
  >(ACCOUNTS_QUERY, {
    variables:
      companyId === null ? undefined : { companyId, activeOnly: false },
    skip: companyId === null || sessionLoading || !canRead,
    fetchPolicy: 'network-only',
    notifyOnNetworkStatusChange: true,
  })

  const apiError = error ? readApiError(error) : null
  useSessionErrorGuard(apiError)

  const rows = useMemo(() => data?.accounts ?? [], [data])
  const visible = useMemo(
    () =>
      rows.filter(
        (row) =>
          (typeFilter === 'ALL' || row.accountType === typeFilter) &&
          (!activeOnly || row.isActive),
      ),
    [rows, typeFilter, activeOnly],
  )

  return (
    <AdminSection
      id="admin-accounts-title"
      eyebrow="Dashboard administrativo"
      title="Cuentas"
      lead="¿Dónde está el dinero? Cuentas de la empresa de tu sesión."
    >
      {!sessionLoading && !canRead ? (
        <div className="alert alert--warning admin-alert" role="alert">
          <p>Tu rol no tiene el permiso accounts.read para ver las cuentas.</p>
        </div>
      ) : null}

      {canRead ? (
        <>
          <div className="admin-toolbar">
            <div className="field admin-toolbar__filter">
              <label className="field__label" htmlFor="accounts-type-filter">
                Tipo
              </label>
              <select
                id="accounts-type-filter"
                className="field__input"
                value={typeFilter}
                onChange={(event) =>
                  setTypeFilter(event.target.value as AccountType | 'ALL')
                }
              >
                <option value="ALL">Todas</option>
                {ACCOUNT_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {ACCOUNT_TYPE_LABELS[type]}
                  </option>
                ))}
              </select>
            </div>

            <label className="admin-check">
              <input
                type="checkbox"
                checked={activeOnly}
                onChange={(event) => setActiveOnly(event.target.checked)}
              />
              Solo activas
            </label>

            {canWrite && !showForm ? (
              <button
                className="button button--primary admin-button"
                type="button"
                onClick={() => {
                  setShowForm(true)
                  setNotice(null)
                }}
              >
                Nueva cuenta
              </button>
            ) : null}
          </div>

          {notice ? (
            <p className="admin-notice" role="status">
              {notice}
            </p>
          ) : null}

          {canWrite && showForm && companyId !== null ? (
            <NewAccountForm
              companyId={companyId}
              onCancel={() => setShowForm(false)}
              onCreated={async (name) => {
                setShowForm(false)
                setNotice(`Se creó la cuenta ${name}.`)
                await refetch()
              }}
            />
          ) : null}

          <section
            className="dashboard-panel"
            aria-labelledby="accounts-admin-table-title"
          >
            <div className="dashboard-panel__heading">
              <h3 id="accounts-admin-table-title">Cuentas registradas</h3>
              {data ? (
                <p className="dashboard-panel__meta">
                  {`${visible.length} de ${rows.length} cuentas`}
                </p>
              ) : null}
            </div>

            <QueryFeedback
              loading={loading || sessionLoading}
              hasData={data !== undefined}
              error={apiError}
              loadingText="Cargando cuentas…"
              onRetry={() => void refetch()}
            />

            {data && rows.length === 0 ? (
              <p className="dashboard-empty" role="status">
                La empresa no tiene cuentas registradas.
              </p>
            ) : null}

            {data && rows.length > 0 && visible.length === 0 ? (
              <p className="dashboard-empty" role="status">
                No hay cuentas con ese filtro.
              </p>
            ) : null}

            {visible.length > 0 ? (
              <div className="accounts-table-wrapper">
                <table className="accounts-table admin-table">
                  <caption className="dashboard-visually-hidden">
                    Cuentas de la empresa
                  </caption>
                  <thead>
                    <tr>
                      <th scope="col">Nombre</th>
                      <th scope="col">Tipo</th>
                      <th scope="col">Banco</th>
                      <th scope="col">Referencia</th>
                      <th scope="col">Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visible.map((row) => (
                      <tr
                        key={row.id}
                        className={row.isActive ? undefined : 'admin-row--inactive'}
                      >
                        <th scope="row" className="accounts-table__account">
                          {row.name}
                          {row.shortDescription ? (
                            <span className="admin-subtext">
                              {row.shortDescription}
                            </span>
                          ) : null}
                        </th>
                        <td data-label="Tipo">{accountTypeLabel(row.accountType)}</td>
                        <td data-label="Banco">
                          {row.bankName || <span className="admin-muted">—</span>}
                        </td>
                        <td data-label="Referencia">{accountReference(row)}</td>
                        <td data-label="Estado">
                          <StatusBadge
                            active={row.isActive}
                            activeLabel="Activa"
                            inactiveLabel="Inactiva"
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </section>
        </>
      ) : null}
    </AdminSection>
  )
}
