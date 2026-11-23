import type { MouseEvent } from 'react'
import { useSessionInfo } from '../session/useSessionInfo'
import { isAdminRoute, routeHref } from './routes'
import type { AppRoute } from './routes'

interface AppNavProps {
  route: AppRoute
  onNavigate: (route: AppRoute) => void
}

/**
 * Cada ítem se dibuja solo si el rol de la sesión tiene el permiso de
 * lectura de esa pantalla: el menú coincide con la columna del puesto en la
 * matriz. El API rechaza la consulta aunque alguien escriba la URL directo.
 */
const ADMIN_ITEMS: {
  route: AppRoute
  label: string
  hint: string
  permission: string
}[] = [
  {
    route: 'admin/usuarios',
    label: 'Usuarios',
    hint: '¿Quién pertenece?',
    permission: 'company.users.read',
  },
  {
    route: 'admin/cuentas',
    label: 'Cuentas',
    hint: '¿Dónde está el dinero?',
    permission: 'accounts.read',
  },
  {
    route: 'admin/conceptos',
    label: 'Conceptos',
    hint: '¿Por qué se mueve?',
    permission: 'concepts.read',
  },
  {
    route: 'admin/roles',
    label: 'Roles y permisos',
    hint: '¿Qué puede hacer cada puesto?',
    permission: 'roles.read',
  },
]

/** Menú lateral: distingue el dashboard financiero del administrativo. */
export function AppNav({ route, onNavigate }: AppNavProps) {
  const { can } = useSessionInfo()
  const items = ADMIN_ITEMS.filter((item) => can(item.permission))

  function follow(next: AppRoute) {
    return (event: MouseEvent<HTMLAnchorElement>) => {
      event.preventDefault()
      onNavigate(next)
    }
  }

  return (
    <nav className="app-nav" aria-label="Secciones">
      <a
        className="app-nav__link"
        href={routeHref('financiero')}
        aria-current={route === 'financiero' ? 'page' : undefined}
        onClick={follow('financiero')}
      >
        Dashboard financiero
      </a>

      <p
        className={
          isAdminRoute(route)
            ? 'app-nav__group app-nav__group--active'
            : 'app-nav__group'
        }
        id="app-nav-admin"
      >
        Dashboard administrativo
      </p>
      <ul className="app-nav__list" aria-labelledby="app-nav-admin">
        {items.map((item) => (
          <li key={item.route}>
            <a
              className="app-nav__link app-nav__link--child"
              href={routeHref(item.route)}
              aria-current={route === item.route ? 'page' : undefined}
              onClick={follow(item.route)}
            >
              <span>{item.label}</span>
              <span className="app-nav__hint">{item.hint}</span>
            </a>
          </li>
        ))}
      </ul>
    </nav>
  )
}
