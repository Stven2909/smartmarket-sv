import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useAuth } from '../context/AuthContext'
import { ApiError } from '../api/client'

export function LoginScreen() {
  const { login, register } = useAuth()
  const shellRef = useRef<HTMLDivElement>(null)
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirmation, setPasswordConfirmation] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [imgBroken, setImgBroken] = useState(false)

  useEffect(() => {
    const shell = shellRef.current
    if (!shell) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const el: HTMLDivElement = shell
    let raf = 0
    function onMove(event: MouseEvent) {
      const nx = (event.clientX / window.innerWidth - 0.5) * 2
      const ny = (event.clientY / window.innerHeight - 0.5) * 2
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        el.style.setProperty('--px', nx.toFixed(3))
        el.style.setProperty('--py', ny.toFixed(3))
      })
    }
    window.addEventListener('mousemove', onMove)
    return () => {
      window.removeEventListener('mousemove', onMove)
      cancelAnimationFrame(raf)
    }
  }, [])

  function handleMascotError() {
    setImgBroken(true)
  }

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
    <div className="auth-shell" ref={shellRef}>
      <div className="auth-bg" aria-hidden="true">
        <div className="auth-bg-mod bg-compare"><i className="g" /><i /><i className="g" /></div>
        <div className="auth-bg-mod bg-list"><i className="row" /><i className="row" /><i className="row" /></div>
        <div className="auth-bg-mod bg-savings" />
        <div className="auth-bg-mod bg-store" />
        <div className="auth-bg-mod bg-promo"><i className="g" /><i /><i /><i className="g" /></div>
        <div className="auth-bg-mod bg-cat" />
      </div>

      <div className="auth-ambient" aria-hidden="true">
        <div className="amb-card amb-save"><b>−12%</b> hoy</div>
        <div className="amb-card amb-compare">Tu lista · 24 ítems</div>
        <div className="amb-card amb-store">Despensa Familiar</div>
        <div className="amb-card amb-tip">2×1 en frutas</div>
      </div>

      <main className="auth-scene">
        <button type="button" className="app-brand auth-brand" aria-label="SmartMarket SV">
          <span className="app-brand-mark" aria-hidden="true"><i /><i /></span>
          <span>Smart<b>Market</b> SV</span>
        </button>

        <h1 className="auth-hello">
          {mode === 'login' ? 'Bienvenido de nuevo.' : 'Bienvenido a SmartMarket.'}
        </h1>
        <p className="auth-slogan">Decisiones inteligentes para cada compra.</p>

        <div className="auth-mascot">
          <div className="auth-mascot-halo" aria-hidden="true" />
          {imgBroken ? (
            <span className="mascot-brand-fallback" aria-hidden="true"><i /><i /></span>
          ) : (
            <img
              className="auth-mascot-img"
              src="/mascota/Smarty_sinfondo.webp"
              alt="Smarty te saluda"
              onError={handleMascotError}
            />
          )}
        </div>

        <section className="auth-glass">
          <p className="auth-glass-eyebrow">Tu espacio te está esperando</p>

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

            <button type="submit" className="auth-submit" disabled={busy}>
              {busy ? 'Un momento…' : mode === 'login' ? 'Continuar' : 'Crear cuenta'}
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
              ? '¿No tenés cuenta? Creala acá'
              : '¿Ya tenés cuenta? Iniciá sesión'}
          </button>

          <p className="auth-note">Demo: usuario@smartmarket.sv / password123</p>
        </section>
      </main>
    </div>
  )
}
