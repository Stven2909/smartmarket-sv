import { useState } from 'react'
import { ChevronRight, LogOut, MapPin, Smartphone } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import type { InstallPromptApi } from '../lib/useInstallPrompt'
import { InstallPrompt } from './InstallPrompt'

type Props = {
  onOpenSucursales: () => void
  install: InstallPromptApi
}

export function PerfilView({ onOpenSucursales, install }: Props) {
  const { user, logout } = useAuth()
  const [iosModalOpen, setIosModalOpen] = useState(false)
  const initial = (user?.name?.trim().charAt(0) ?? 'U').toUpperCase()

  const handleInstall = async () => {
    // Chromium/Edge/Android: dispara la instalación nativa.
    // iOS/Safari: abre el modal con las instrucciones manuales.
    const outcome = await install.promptInstall()
    if (outcome === 'ios') setIosModalOpen(true)
  }

  return (
    <div className="view" style={{ maxWidth: 560 }}>
      <div className="page-heading">
        <div className="eyebrow"><span />TU CUENTA</div>
        <h1>Perfil</h1>
      </div>

      <section className="profile-card">
        <div className="profile-avatar">{initial}</div>
        <h1>{user?.name}</h1>
        <p>{user?.email}</p>
      </section>

      <div className="profile-rows">
        {!install.isStandalone && (
          <button type="button" className="profile-row install" onClick={() => void handleInstall()}>
            <Smartphone size={20} />
            <span className="profile-row-text">
              <strong>Instalar SmartMarket</strong>
              <small>Lleva tus listas y comparaciones siempre contigo.</small>
            </span>
            <span><ChevronRight size={18} /></span>
          </button>
        )}

        <button type="button" className="profile-row" onClick={onOpenSucursales}>
          <MapPin size={20} />
          Mis sucursales
          <span><ChevronRight size={18} /></span>
        </button>

        <button
          type="button"
          className="profile-row danger"
          onClick={() => void logout()}
        >
          <LogOut size={20} />
          Cerrar sesión
          <span><ChevronRight size={18} /></span>
        </button>
      </div>

      {iosModalOpen && (
        <InstallPrompt variant="modal" install={install} onClose={() => setIosModalOpen(false)} />
      )}
    </div>
  )
}
