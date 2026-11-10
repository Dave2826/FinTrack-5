import { BrandMark } from './BrandMark'

export function BrandPanel() {
  return (
    <aside className="brand-panel" aria-label="Presentación de FinTrack-5">
      <BrandMark />
      <div className="brand-copy">
        <p className="eyebrow eyebrow--light">
          Finanzas claras, decisiones mejores
        </p>
        <h1>FinTrack-5</h1>
        <p className="brand-subtitle">Panel financiero</p>
        <p className="brand-description">
          Consulta el balance general de tu empresa, revisa el detalle de tus
          cuentas y detecta riesgos en un solo lugar.
        </p>
      </div>
      <ul className="brand-points">
        <li>Balances por periodo</li>
        <li>Estado de riesgo</li>
        <li>Detalle por cuenta</li>
      </ul>
      <p className="brand-footer">Unidad III · Actividad 1</p>
    </aside>
  )
}
