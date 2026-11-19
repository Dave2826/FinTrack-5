import { DashboardHeader } from '../features/dashboard/components/DashboardHeader'
import { DashboardPage } from '../features/dashboard/DashboardPage'
import { AccountsAdminPage } from '../features/admin/AccountsAdminPage'
import { ConceptsAdminPage } from '../features/admin/ConceptsAdminPage'
import { UsersAdminPage } from '../features/admin/UsersAdminPage'
import '../features/admin/admin.css'
import { SessionInfoProvider } from '../session/SessionInfoProvider'
import { AppNav } from './AppNav'
import { isAdminRoute } from './routes'
import type { AppRoute } from './routes'
import { useHashRoute } from './useHashRoute'

function Section({ route }: { route: AppRoute }) {
  switch (route) {
    case 'admin/usuarios':
      return <UsersAdminPage />
    case 'admin/cuentas':
      return <AccountsAdminPage />
    case 'admin/conceptos':
      return <ConceptsAdminPage />
    case 'financiero':
    default:
      return <DashboardPage />
  }
}

/**
 * Aplicación autenticada: mismo login, mismo encabezado y un menú que lleva
 * al dashboard financiero (actividad 1) o al administrativo (actividad 13).
 */
export function AppShell() {
  const [route, navigate] = useHashRoute()
  const section = isAdminRoute(route) ? 'administrativo' : 'financiero'

  return (
    <SessionInfoProvider>
      <div className="dashboard-page">
        <DashboardHeader section={section} />

        <div className="app-layout">
          <AppNav route={route} onNavigate={navigate} />
          <div className="app-layout__content">
            <Section route={route} />
          </div>
        </div>
      </div>
    </SessionInfoProvider>
  )
}
