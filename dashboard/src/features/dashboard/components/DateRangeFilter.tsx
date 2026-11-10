import { useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { validateDateRange } from '../../../lib/dateRange'
import type { DateRange, DateRangeValidation } from '../../../lib/dateRange'

type InvalidDateRange = Extract<DateRangeValidation, { ok: false }>

interface DateRangeFilterProps {
  /** Rango aplicado actualmente; se usa como valor inicial del formulario. */
  range: DateRange
  /** Se invoca solo con un rango que pasó la validación. */
  onApply: (range: DateRange) => void
  /** Deshabilita el envío mientras hay una consulta en curso. */
  isUpdating?: boolean
}

const ERROR_ID = 'dashboard-date-range-error'

export function DateRangeFilter({
  range,
  onApply,
  isUpdating = false,
}: DateRangeFilterProps) {
  const [fromDate, setFromDate] = useState(range.fromDate)
  const [toDate, setToDate] = useState(range.toDate)
  const [validationError, setValidationError] =
    useState<InvalidDateRange | null>(null)
  const fromInputRef = useRef<HTMLInputElement>(null)
  const toInputRef = useRef<HTMLInputElement>(null)

  const fromInvalid =
    validationError?.reason === 'missing-from' ||
    validationError?.reason === 'invalid-from' ||
    validationError?.reason === 'from-after-to'

  const toInvalid =
    validationError?.reason === 'missing-to' ||
    validationError?.reason === 'invalid-to' ||
    validationError?.reason === 'from-after-to'

  function handleFromChange(value: string) {
    setFromDate(value)
    setValidationError(null)
  }

  function handleToChange(value: string) {
    setToDate(value)
    setValidationError(null)
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const validation = validateDateRange(fromDate, toDate)

    if (!validation.ok) {
      setValidationError(validation)

      // Llevar el foco al campo que el usuario debe corregir.
      const target =
        validation.reason === 'missing-to' ||
        validation.reason === 'invalid-to'
          ? toInputRef
          : fromInputRef
      target.current?.focus()
      return
    }

    setValidationError(null)
    onApply(validation.range)
  }

  return (
    <form
      className="dashboard-filter"
      aria-labelledby="dashboard-period-title"
      onSubmit={handleSubmit}
      noValidate
    >
      <div className="dashboard-filter__heading">
        <p className="eyebrow">Periodo</p>
        <h3 id="dashboard-period-title">Rango de fechas</h3>
        <p className="dashboard-filter__hint">
          Las fechas se interpretan como días completos UTC.
        </p>
      </div>

      <div className="dashboard-filter__fields">
        <div className="field">
          <label className="field__label" htmlFor="dashboard-from-date">
            Fecha inicial
          </label>
          <input
            id="dashboard-from-date"
            ref={fromInputRef}
            className="field__input"
            type="date"
            value={fromDate}
            onChange={(event) => handleFromChange(event.target.value)}
            aria-invalid={fromInvalid ? true : undefined}
            aria-describedby={fromInvalid ? ERROR_ID : undefined}
            required
          />
        </div>

        <div className="field">
          <label className="field__label" htmlFor="dashboard-to-date">
            Fecha final
          </label>
          <input
            id="dashboard-to-date"
            ref={toInputRef}
            className="field__input"
            type="date"
            value={toDate}
            onChange={(event) => handleToChange(event.target.value)}
            aria-invalid={toInvalid ? true : undefined}
            aria-describedby={toInvalid ? ERROR_ID : undefined}
            required
          />
        </div>

        <button
          className="button button--primary dashboard-filter__submit"
          type="submit"
          disabled={isUpdating}
        >
          {isUpdating ? 'Consultando…' : 'Consultar'}
        </button>
      </div>

      {validationError ? (
        <p
          className="field__error dashboard-filter__error"
          id={ERROR_ID}
          role="alert"
        >
          {validationError.message}
        </p>
      ) : null}
    </form>
  )
}
