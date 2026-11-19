import { useMutation, useQuery } from '@apollo/client'
import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import {
  ACCOUNTS_QUERY,
  ACCOUNT_CONCEPTS_QUERY,
  ASSIGN_CONCEPT_MUTATION,
  CONCEPTS_QUERY,
  CREATE_CONCEPT_MUTATION,
  REMOVE_CONCEPT_MUTATION,
} from '../../api/operations/admin'
import { useSessionErrorGuard } from '../../hooks/useSessionErrorGuard'
import { CONCEPT_TYPE_LABELS, conceptTypeLabel } from '../../lib/adminLabels'
import { readApiError } from '../../lib/apiErrors'
import { useSessionInfo } from '../../session/useSessionInfo'
import type {
  AccountConceptsResult,
  AdminAccountsResult,
  AdminConcept,
  AdminConceptsResult,
  ConceptType,
  CreateConceptInput,
} from '../../types/admin'
import { AdminSection } from './components/AdminSection'
import { QueryFeedback } from './components/QueryFeedback'
import { StatusBadge } from './components/StatusBadge'

interface ConceptForm {
  name: string
  conceptType: ConceptType | ''
  shortDescription: string
}

const EMPTY_FORM: ConceptForm = {
  name: '',
  conceptType: '',
  shortDescription: '',
}

function NewConceptForm({
  companyId,
  onCreated,
  onCancel,
}: {
  companyId: number
  onCreated: (name: string) => Promise<void>
  onCancel: () => void
}) {
  const [form, setForm] = useState<ConceptForm>(EMPTY_FORM)
  const [errors, setErrors] = useState<{ name?: string; conceptType?: string }>(
    {},
  )
  const [apiError, setApiError] = useState<string | null>(null)
  const [createConcept, { loading }] = useMutation<
    unknown,
    { input: CreateConceptInput }
  >(CREATE_CONCEPT_MUTATION)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setApiError(null)

    const nextErrors: typeof errors = {}

    if (!form.name.trim()) {
      nextErrors.name = 'Escribe el nombre del concepto.'
    }

    if (!form.conceptType) {
      nextErrors.conceptType = 'Elige si es de ingreso o de egreso.'
    }

    setErrors(nextErrors)

    if (Object.keys(nextErrors).length > 0 || !form.conceptType) {
      return
    }

    try {
      await createConcept({
        variables: {
          input: {
            companyId,
            conceptType: form.conceptType,
            name: form.name.trim(),
            shortDescription: form.shortDescription.trim() || null,
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
      aria-labelledby="new-concept-title"
      noValidate
      onSubmit={(event) => void handleSubmit(event)}
    >
      <h3 id="new-concept-title">Nuevo concepto</h3>
      <p className="admin-form__hint">
        Un concepto es de ingreso o de egreso, nunca de las dos cosas.
      </p>

      <div className="admin-form__grid">
        <div className="field">
          <label className="field__label" htmlFor="new-concept-name">
            Nombre
          </label>
          <input
            id="new-concept-name"
            className="field__input"
            value={form.name}
            onChange={(event) =>
              setForm((current) => ({ ...current, name: event.target.value }))
            }
            aria-invalid={errors.name ? true : undefined}
            aria-describedby={errors.name ? 'new-concept-name-error' : undefined}
          />
          {errors.name ? (
            <p className="field__error" id="new-concept-name-error">
              {errors.name}
            </p>
          ) : null}
        </div>

        <fieldset
          className="admin-fieldset"
          aria-describedby={
            errors.conceptType ? 'new-concept-type-error' : undefined
          }
        >
          <legend className="field__label">Tipo</legend>
          {(Object.keys(CONCEPT_TYPE_LABELS) as ConceptType[]).map((type) => (
            <label key={type} className="admin-check">
              <input
                type="radio"
                name="new-concept-type"
                value={type}
                checked={form.conceptType === type}
                onChange={() =>
                  setForm((current) => ({ ...current, conceptType: type }))
                }
              />
              {CONCEPT_TYPE_LABELS[type]}
            </label>
          ))}
          {errors.conceptType ? (
            <p className="field__error" id="new-concept-type-error">
              {errors.conceptType}
            </p>
          ) : null}
        </fieldset>

        <div className="field admin-form__wide">
          <label className="field__label" htmlFor="new-concept-description">
            Descripción corta
          </label>
          <input
            id="new-concept-description"
            className="field__input"
            maxLength={255}
            value={form.shortDescription}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                shortDescription: event.target.value,
              }))
            }
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
          {loading ? 'Guardando…' : 'Guardar concepto'}
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

function AccountConceptsPanel({
  companyId,
  concepts,
  canWrite,
}: {
  companyId: number
  concepts: readonly AdminConcept[]
  canWrite: boolean
}) {
  const [accountId, setAccountId] = useState<number | null>(null)
  const [conceptToAssign, setConceptToAssign] = useState<string>('')
  const [message, setMessage] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const accountsQuery = useQuery<
    AdminAccountsResult,
    { companyId: number; activeOnly: boolean }
  >(ACCOUNTS_QUERY, {
    variables: { companyId, activeOnly: true },
    fetchPolicy: 'network-only',
  })

  const relationsQuery = useQuery<
    AccountConceptsResult,
    { accountId: number }
  >(ACCOUNT_CONCEPTS_QUERY, {
    variables: accountId === null ? undefined : { accountId },
    skip: accountId === null,
    fetchPolicy: 'network-only',
    notifyOnNetworkStatusChange: true,
  })

  const accountsError = accountsQuery.error
    ? readApiError(accountsQuery.error)
    : null
  const relationsError = relationsQuery.error
    ? readApiError(relationsQuery.error)
    : null
  useSessionErrorGuard(accountsError ?? relationsError)

  const [assign, assignState] = useMutation<
    unknown,
    { input: { accountId: number; conceptId: number } }
  >(ASSIGN_CONCEPT_MUTATION)
  const [remove, removeState] = useMutation<
    unknown,
    { accountId: number; conceptId: number }
  >(REMOVE_CONCEPT_MUTATION)

  const accounts = accountsQuery.data?.accounts ?? []
  const relations = relationsQuery.data?.accountConcepts ?? []
  const activeConcepts = concepts.filter((concept) => concept.isActive)
  const busy = assignState.loading || removeState.loading

  async function handleAssign(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setMessage(null)
    setActionError(null)

    if (accountId === null || !conceptToAssign) {
      setActionError('Elige un concepto para asignar.')
      return
    }

    try {
      await assign({
        variables: {
          input: { accountId, conceptId: Number(conceptToAssign) },
        },
      })
      const name =
        concepts.find((concept) => String(concept.id) === conceptToAssign)
          ?.name ?? 'El concepto'
      setMessage(`${name} quedó permitido en la cuenta.`)
      await relationsQuery.refetch()
    } catch (error) {
      setActionError(readApiError(error).message)
    }
  }

  async function handleRemove(conceptId: number, name: string) {
    if (accountId === null) {
      return
    }

    setMessage(null)
    setActionError(null)

    try {
      await remove({ variables: { accountId, conceptId } })
      setMessage(
        `${name} ya no está permitido en la cuenta. Sigue en el catálogo y los movimientos anteriores no cambian.`,
      )
      await relationsQuery.refetch()
    } catch (error) {
      setActionError(readApiError(error).message)
    }
  }

  return (
    <section
      className="dashboard-panel admin-side-panel"
      aria-labelledby="account-concepts-title"
    >
      <div className="dashboard-panel__heading">
        <h3 id="account-concepts-title">Conceptos de una cuenta</h3>
      </div>
      <p className="admin-form__hint">
        Un movimiento solo puede usar un concepto asignado a su cuenta.
      </p>

      <QueryFeedback
        loading={accountsQuery.loading}
        hasData={accountsQuery.data !== undefined}
        error={accountsError}
        loadingText="Cargando cuentas…"
        onRetry={() => void accountsQuery.refetch()}
      />

      {accountsQuery.data && accounts.length === 0 ? (
        <p className="dashboard-empty" role="status">
          No hay cuentas activas. Crea una en la sección Cuentas.
        </p>
      ) : null}

      {accounts.length > 0 ? (
        <div className="field">
          <label className="field__label" htmlFor="account-concepts-account">
            Cuenta
          </label>
          <select
            id="account-concepts-account"
            className="field__input"
            value={accountId ?? ''}
            onChange={(event) => {
              setAccountId(event.target.value ? Number(event.target.value) : null)
              setMessage(null)
              setActionError(null)
            }}
          >
            <option value="">Elige una cuenta</option>
            {accounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.name}
              </option>
            ))}
          </select>
        </div>
      ) : null}

      {accountId !== null ? (
        <>
          <QueryFeedback
            loading={relationsQuery.loading}
            hasData={relationsQuery.data !== undefined}
            error={relationsError}
            loadingText="Cargando conceptos permitidos…"
            onRetry={() => void relationsQuery.refetch()}
          />

          {relationsQuery.data && relations.length === 0 ? (
            <p className="dashboard-empty" role="status">
              Esta cuenta todavía no tiene conceptos permitidos.
            </p>
          ) : null}

          {relations.length > 0 ? (
            <ul className="admin-relations" aria-label="Conceptos permitidos">
              {relations.map((relation) => {
                const concept = relation.concept
                const name = concept?.name ?? `Concepto #${relation.id}`

                return (
                  <li key={relation.id} className="admin-relation">
                    <span>
                      <strong>{name}</strong>
                      {concept ? (
                        <span className="admin-subtext">
                          {conceptTypeLabel(concept.conceptType)}
                        </span>
                      ) : null}
                    </span>
                    {canWrite && concept ? (
                      <button
                        className="button button--secondary admin-button admin-button--small"
                        type="button"
                        disabled={busy}
                        onClick={() => void handleRemove(concept.id, name)}
                        aria-label={`Quitar ${name} de la cuenta`}
                      >
                        Quitar
                      </button>
                    ) : null}
                  </li>
                )
              })}
            </ul>
          ) : null}

          {canWrite ? (
            <form
              className="admin-assign"
              onSubmit={(event) => void handleAssign(event)}
            >
              <div className="field">
                <label className="field__label" htmlFor="assign-concept">
                  Concepto a asignar
                </label>
                <select
                  id="assign-concept"
                  className="field__input"
                  value={conceptToAssign}
                  onChange={(event) => setConceptToAssign(event.target.value)}
                >
                  <option value="">Elige un concepto</option>
                  {activeConcepts.map((concept) => (
                    <option key={concept.id} value={concept.id}>
                      {`${concept.name} (${conceptTypeLabel(concept.conceptType)})`}
                    </option>
                  ))}
                </select>
              </div>
              <button
                className="button button--primary admin-button"
                type="submit"
                disabled={busy}
              >
                {assignState.loading ? 'Asignando…' : 'Asignar'}
              </button>
            </form>
          ) : null}

          {message ? (
            <p className="admin-notice" role="status">
              {message}
            </p>
          ) : null}

          {actionError ? (
            <div className="alert alert--error admin-alert" role="alert">
              <p>{actionError}</p>
            </div>
          ) : null}
        </>
      ) : null}
    </section>
  )
}

/**
 * Conceptos: ¿por qué se mueve el dinero y en qué cuenta se permite?
 * Catálogo (`concepts`) y conceptos de una cuenta (`accountConcepts`).
 */
export function ConceptsAdminPage() {
  const { companyId, can, loading: sessionLoading } = useSessionInfo()
  const canRead = can('concepts.read')
  const canReadAccounts = can('accounts.read')
  const canWrite = can('concepts.write')

  const [typeFilter, setTypeFilter] = useState<ConceptType | 'ALL'>('ALL')
  const [activeOnly, setActiveOnly] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  const { data, loading, error, refetch } = useQuery<
    AdminConceptsResult,
    { companyId: number; activeOnly: boolean }
  >(CONCEPTS_QUERY, {
    variables:
      companyId === null ? undefined : { companyId, activeOnly: false },
    skip: companyId === null || sessionLoading || !canRead,
    fetchPolicy: 'network-only',
    notifyOnNetworkStatusChange: true,
  })

  const apiError = error ? readApiError(error) : null
  useSessionErrorGuard(apiError)

  const rows = useMemo(() => data?.concepts ?? [], [data])
  const visible = useMemo(
    () =>
      rows.filter(
        (row) =>
          (typeFilter === 'ALL' || row.conceptType === typeFilter) &&
          (!activeOnly || row.isActive),
      ),
    [rows, typeFilter, activeOnly],
  )

  const filters: { value: ConceptType | 'ALL'; label: string }[] = [
    { value: 'ALL', label: 'Todos' },
    { value: 'INCOME', label: 'Ingreso' },
    { value: 'EXPENSE', label: 'Egreso' },
  ]

  return (
    <AdminSection
      id="admin-concepts-title"
      eyebrow="Dashboard administrativo"
      title="Conceptos"
      lead="¿Por qué entra o sale el dinero, y en qué cuenta se permite cada concepto?"
    >
      {!sessionLoading && !canRead ? (
        <div className="alert alert--warning admin-alert" role="alert">
          <p>Tu rol no tiene el permiso concepts.read para ver los conceptos.</p>
        </div>
      ) : null}

      {canRead ? (
        <div className="admin-split">
          <div className="admin-split__main">
            <div className="admin-toolbar">
              <div
                className="admin-segmented"
                role="group"
                aria-label="Filtrar por tipo"
              >
                {filters.map((filter) => (
                  <button
                    key={filter.value}
                    type="button"
                    className={
                      typeFilter === filter.value
                        ? 'admin-segmented__option admin-segmented__option--active'
                        : 'admin-segmented__option'
                    }
                    aria-pressed={typeFilter === filter.value}
                    onClick={() => setTypeFilter(filter.value)}
                  >
                    {filter.label}
                  </button>
                ))}
              </div>

              <label className="admin-check">
                <input
                  type="checkbox"
                  checked={activeOnly}
                  onChange={(event) => setActiveOnly(event.target.checked)}
                />
                Solo activos
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
                  Nuevo concepto
                </button>
              ) : null}
            </div>

            {notice ? (
              <p className="admin-notice" role="status">
                {notice}
              </p>
            ) : null}

            {canWrite && showForm && companyId !== null ? (
              <NewConceptForm
                companyId={companyId}
                onCancel={() => setShowForm(false)}
                onCreated={async (name) => {
                  setShowForm(false)
                  setNotice(`Se creó el concepto ${name}.`)
                  await refetch()
                }}
              />
            ) : null}

            <section
              className="dashboard-panel"
              aria-labelledby="concepts-table-title"
            >
              <div className="dashboard-panel__heading">
                <h3 id="concepts-table-title">Catálogo de conceptos</h3>
                {data ? (
                  <p className="dashboard-panel__meta">
                    {`${visible.length} de ${rows.length} conceptos`}
                  </p>
                ) : null}
              </div>

              <QueryFeedback
                loading={loading || sessionLoading}
                hasData={data !== undefined}
                error={apiError}
                loadingText="Cargando conceptos…"
                onRetry={() => void refetch()}
              />

              {data && rows.length === 0 ? (
                <p className="dashboard-empty" role="status">
                  La empresa no tiene conceptos registrados.
                </p>
              ) : null}

              {data && rows.length > 0 && visible.length === 0 ? (
                <p className="dashboard-empty" role="status">
                  No hay conceptos con ese filtro.
                </p>
              ) : null}

              {visible.length > 0 ? (
                <div className="accounts-table-wrapper">
                  <table className="accounts-table admin-table admin-table--compact">
                    <caption className="dashboard-visually-hidden">
                      Catálogo de conceptos
                    </caption>
                    <thead>
                      <tr>
                        <th scope="col">Concepto</th>
                        <th scope="col">Tipo</th>
                        <th scope="col">Estado</th>
                      </tr>
                    </thead>
                    <tbody>
                      {visible.map((row) => (
                        <tr
                          key={row.id}
                          className={
                            row.isActive ? undefined : 'admin-row--inactive'
                          }
                        >
                          <th scope="row" className="accounts-table__account">
                            {row.name}
                            {row.shortDescription ? (
                              <span className="admin-subtext">
                                {row.shortDescription}
                              </span>
                            ) : null}
                          </th>
                          <td data-label="Tipo">
                            <span
                              className={
                                row.conceptType === 'INCOME'
                                  ? 'admin-type admin-type--income'
                                  : 'admin-type admin-type--expense'
                              }
                            >
                              {conceptTypeLabel(row.conceptType)}
                            </span>
                          </td>
                          <td data-label="Estado">
                            <StatusBadge active={row.isActive} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
            </section>
          </div>

          {companyId !== null && canReadAccounts ? (
            <AccountConceptsPanel
              companyId={companyId}
              concepts={rows}
              canWrite={canWrite}
            />
          ) : null}
        </div>
      ) : null}
    </AdminSection>
  )
}
