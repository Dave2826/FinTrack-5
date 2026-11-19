import type { MouseEvent } from 'react'
import { isAdminRoute, routeHref } from './routes'
import type { AppRoute } from './routes'

interface AppNavProps {
  route: AppRoute
  onNavigate: (route: AppRoute) => void
}

const ADMIN_ITEMS: { route: AppRoute; label: string; hint: string }[] = [
  { route: 'admin/usuarios', label: 'Usuarios', hint: '¿Quién pertenece?' },
  { route: 'admin/cuentas', label: 'Cuentas', hint: '¿Dónde está el dinero?' },
  {
    route: 'admin/conceptos',
    label: 'Conceptos',
    hint: '¿Por qué se mueve?',
  },
]

/** Menú lateral: distingue el dashboard financiero del administrativo. */
export function AppNav({ route, onNavigate }: AppNavProps) {
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
        {ADMIN_ITEMS.map((item) => (
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
