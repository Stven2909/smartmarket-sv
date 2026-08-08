import { useState } from 'react'
import type { InstallPromptApi } from '../lib/useInstallPrompt'

type Props = {
  variant: 'banner' | 'modal'
  install: InstallPromptApi
  onClose: () => void
}

function SmartyImage({ size, broken, setBroken }: { size: number; broken: boolean; setBroken: (v: boolean) => void }) {
  if (broken) {
    return (
      <span className="install-smarty-fallback" aria-hidden="true">
        <i /><i />
      </span>
    )
  }
  return (
    <img
      className="install-smarty-img"
      src="/mascota/Smarty_waving.webp"
      alt=""
      width={size}
      height={size}
      style={{ width: size, height: size }}
      onError={() => setBroken(true)}
    />
  )
}

export function InstallPrompt({ variant, install, onClose }: Props) {
  const [busy, setBusy] = useState(false)
  const [imgBroken, setImgBroken] = useState(false)
  const [imgBrokenModal, setImgBrokenModal] = useState(false)

  const handleInstall = async () => {
    if (busy) return
    setBusy(true)
    const outcome = await install.promptInstall()
    if (outcome === 'dismissed') install.dismiss()
    onClose()
  }

  const handleDismiss = () => {
    install.dismiss()
    onClose()
  }

  if (variant === 'modal') {
    return (
      <div className="install-modal-scrim" onClick={onClose}>
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="install-modal-title"
          className="install-prompt-modal"
          onClick={(e) => e.stopPropagation()}
        >
          <button type="button" className="install-modal-close" aria-label="Cerrar" onClick={onClose}>
            ✕
          </button>
          <SmartyImage size={84} broken={imgBrokenModal} setBroken={setImgBrokenModal} />
          <span className="eyebrow"><span />INSTALAR SMARTMARKET</span>
          <h2 id="install-modal-title">¡Llévame contigo! 👋</h2>
          <p className="install-modal-intro">
            Puedes instalar SmartMarket en tu iPhone:
          </p>
          <ol className="install-steps">
            <li>Toca <strong>Compartir</strong> en Safari.</li>
            <li>Selecciona <strong>“Agregar a pantalla de inicio”</strong>.</li>
            <li>Toca <strong>Agregar</strong>.</li>
          </ol>
          <button type="button" className="add-button" onClick={onClose} autoFocus>
            Entendido
          </button>
        </div>
      </div>
    )
  }

  return (
    <aside
      role="dialog"
      aria-modal="false"
      aria-labelledby="install-banner-title"
      className="install-prompt-banner"
    >
      <SmartyImage size={72} broken={imgBroken} setBroken={setImgBroken} />
      <div className="install-prompt-body">
        <span className="install-prompt-hi">👋 ¡Hola! Soy Smarty</span>
        <h2 id="install-banner-title">Llévame contigo.</h2>
        <p>
          Instala SmartMarket en tu dispositivo y tendrás tus listas, comparaciones
          y mejores opciones de compra siempre a mano.
        </p>
        <div className="install-prompt-actions">
          <button type="button" className="install-primary" onClick={() => void handleInstall()} disabled={busy}>
            Instalar SmartMarket
          </button>
          <button type="button" className="install-secondary" onClick={handleDismiss}>
            Ahora no
          </button>
        </div>
      </div>
    </aside>
  )
}
