import { AuthProvider } from './auth/AuthContext'
import { RequireAuth } from './auth/RequireAuth'
import { useAuth } from './auth/useAuth'
import { BrandPanel } from './components/BrandPanel'
import { AppShell } from './app/AppShell'

function AppContent() {
  const { status } = useAuth()
  const isAuthenticated = status === 'authenticated'

  return (
    <div
      className={
        isAuthenticated ? 'app-shell app-shell--dashboard' : 'app-shell'
      }
    >
      {isAuthenticated ? null : <BrandPanel />}
      <main className={isAuthenticated ? 'dashboard-shell' : 'content-panel'}>
        <RequireAuth>
          <AppShell />
        </RequireAuth>
      </main>
    </div>
  )
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}

export default App
