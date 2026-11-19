interface StatusBadgeProps {
  active: boolean
  activeLabel?: string
  inactiveLabel?: string
}

/** Activo e inactivo se distinguen por texto y por color. */
export function StatusBadge({
  active,
  activeLabel = 'Activo',
  inactiveLabel = 'Inactivo',
}: StatusBadgeProps) {
  return (
    <span
      className={
        active
          ? 'admin-badge admin-badge--active'
          : 'admin-badge admin-badge--inactive'
      }
    >
      {active ? activeLabel : inactiveLabel}
    </span>
  )
}
