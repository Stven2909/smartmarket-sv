import { useState } from 'react'
import type { FormEvent } from 'react'
import { useAuth } from '../context/AuthContext'
import { ApiError } from '../api/client'

export function LoginScreen() {
  const { login, register } = useAuth()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirmation, setPasswordConfirmation] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setBusy(true)
    try {
      if (mode === 'login') {
        await login(email, password)
      } else {
        await register(name, email, password, passwordConfirmation)
      }
    } catch (e) {
      if (e instanceof ApiError) {
        if (e.validation) {
          setError(Object.values(e.validation).flat().join(' '))
        } else {
          setError(e.message)
        }
      } else {
        setError('No se pudo conectar con el servidor.')
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="app-shell">
      <div className="auth-panel">
        <button type="button" className="app-brand" aria-label="SmartMarket SV">
          <span className="app-brand-mark" aria-hidden="true"><i /><i /></span>
          <span>Smart<b>Market</b> SV</span>
        </button>

        <div className="slogan">Decisiones inteligentes para cada compra</div>
        <h1 className="auth-title">
          {mode === 'login' ? 'Inicia sesión' : 'Crea tu cuenta'}
        </h1>
        <p className="auth-subtitle">
          Guarda tus listas de compra, compara precios por supermercado y optimiza tu presupuesto.
        </p>

        <form className="auth-form" onSubmit={handleSubmit}>
          {mode === 'register' && (
            <label className="auth-field">
              <span>Nombre</span>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                minLength={2}
                maxLength={150}
                placeholder="Tu nombre"
                autoComplete="name"
              />
            </label>
          )}

          <label className="auth-field">
            <span>Correo electrónico</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="tucorreo@ejemplo.com"
              autoComplete="email"
            />
          </label>

          <label className="auth-field">
            <span>Contraseña</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              placeholder="Mínimo 8 caracteres"
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            />
          </label>

          {mode === 'register' && (
            <label className="auth-field">
              <span>Confirmar contraseña</span>
              <input
                type="password"
                value={passwordConfirmation}
                onChange={(e) => setPasswordConfirmation(e.target.value)}
                required
                minLength={8}
                placeholder="Repite tu contraseña"
                autoComplete="new-password"
              />
            </label>
          )}

          {error && <div className="live-error"><b>No se pudo continuar</b><span>{error}</span></div>}

          <button type="submit" className="add-button auth-submit" disabled={busy}>
            {busy ? 'Un momento…' : mode === 'login' ? 'Entrar' : 'Crear cuenta'}
          </button>
        </form>

        <button
          type="button"
          className="link-button auth-switch"
          onClick={() => {
            setMode(mode === 'login' ? 'register' : 'login')
            setError(null)
          }}
        >
          {mode === 'login'
            ? '¿No tienes cuenta? Regístrate'
            : '¿Ya tienes cuenta? Inicia sesión'}
        </button>

        <p className="auth-note">
          Demo: usuario@smartmarket.sv / password123
        </p>
      </div>
    </div>
  )
}
