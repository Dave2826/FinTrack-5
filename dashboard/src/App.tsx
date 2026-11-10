import { AuthProvider } from './auth/AuthContext'
import { RequireAuth } from './auth/RequireAuth'
import { BrandPanel } from './components/BrandPanel'
import { DashboardPlaceholder } from './features/dashboard/DashboardPlaceholder'

function App() {
  return (
    <AuthProvider>
      <div className="app-shell">
        <BrandPanel />
        <main className="content-panel">
          <RequireAuth>
            <DashboardPlaceholder />
          </RequireAuth>
        </main>
      </div>
    </AuthProvider>
  )
}

export default App
