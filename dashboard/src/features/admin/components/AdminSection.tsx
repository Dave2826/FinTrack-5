import type { ReactNode } from 'react'

interface AdminSectionProps {
  id: string
  eyebrow: string
  title: string
  lead: string
  children: ReactNode
}

/** Marco común de cada pantalla: una pregunta por pantalla. */
export function AdminSection({
  id,
  eyebrow,
  title,
  lead,
  children,
}: AdminSectionProps) {
  return (
    <div className="dashboard-main">
      <section className="dashboard-content" aria-labelledby={id}>
        <div className="dashboard-content__header">
          <p className="eyebrow">{eyebrow}</p>
          <h2 id={id}>{title}</h2>
          <p className="dashboard-content__lead">{lead}</p>
        </div>
        {children}
      </section>
    </div>
  )
}
