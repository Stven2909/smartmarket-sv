import { AuthProvider, useAuth } from './context/AuthContext'
import { SmartMarketApp } from './components/SmartMarketApp'
import { LoginScreen } from './components/LoginScreen'

function Gate() {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return (
      <div className="app-shell">
        <div className="live-loading" style={{ marginTop: 120 }}>Cargando sesión…</div>
      </div>
    )
  }

  return isAuthenticated ? <SmartMarketApp /> : <LoginScreen />
}

export function App() {
  return (
    <AuthProvider>
      <Gate />
    </AuthProvider>
  )
}
