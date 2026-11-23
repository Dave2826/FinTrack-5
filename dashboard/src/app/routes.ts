/**
 * Navegación por hash: una sola aplicación, sin dependencias nuevas.
 * El hash permite recargar o compartir la vista actual.
 */

export type AppRoute =
  | 'financiero'
  | 'admin/usuarios'
  | 'admin/cuentas'
  | 'admin/conceptos'
  | 'admin/roles'

export const DEFAULT_ROUTE: AppRoute = 'financiero'

const ROUTES: readonly AppRoute[] = [
  'financiero',
  'admin/usuarios',
  'admin/cuentas',
  'admin/conceptos',
  'admin/roles',
]

export function parseRoute(hash: string): AppRoute {
  const value = hash.replace(/^#\/?/, '')

  if (value === 'admin') {
    return 'admin/usuarios'
  }

  return (ROUTES as readonly string[]).includes(value)
    ? (value as AppRoute)
    : DEFAULT_ROUTE
}

export function routeHref(route: AppRoute): string {
  return `#/${route}`
}

export function isAdminRoute(route: AppRoute): boolean {
  return route.startsWith('admin/')
}
