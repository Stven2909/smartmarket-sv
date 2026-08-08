import { useCallback, useEffect, useMemo, useState } from 'react'

// beforeinstallprompt no forma parte de las lib.dom estándar todavía.
type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string }>
}

type InstallState = 'dismissed' | 'completed'
type PromptOutcome = 'accepted' | 'dismissed' | 'ios' | 'unavailable'

const STATE_KEY = 'install_prompt_state'

function readState(): InstallState | null {
  const value = window.localStorage.getItem(STATE_KEY)
  return value === 'dismissed' || value === 'completed' ? value : null
}

function isStandalone(): boolean {
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    // iOS Safari expone navigator.standalone (no tipado en lib.dom)
    (navigator as unknown as { standalone?: boolean }).standalone === true
  )
}

function isIos(): boolean {
  return /iPad|iPhone|iPod/.test(navigator.userAgent) && !('MSStream' in window)
}

// Invitación de instalación de la PWA.
//
//  - Chromium/Edge/Android: captura beforeinstallprompt (deferred prompt) y
//    permite disparar el diálogo nativo desde un gesto del usuario.
//  - iOS/Safari: beforeinstallprompt nunca existe; el CTA de Perfil abre el
//    modal de instrucciones manuales (promptInstall() devuelve 'ios').
//  - Reglas: nunca mostrar si ya corre como PWA (standalone); una vez que el
//    usuario instala o descarta, no volver a ofrecer automáticamente
//    (localStorage install_prompt_state).
export function useInstallPrompt() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null)
  const [state, setState] = useState<InstallState | null>(readState)
  const [standalone, setStandalone] = useState(isStandalone)

  useEffect(() => {
    const onBeforeInstall = (e: Event) => {
      e.preventDefault()
      setDeferred(e as BeforeInstallPromptEvent)
    }
    const onInstalled = () => setState('completed')

    const mq = window.matchMedia('(display-mode: standalone)')
    const onStandaloneChange = () => setStandalone(mq.matches)

    window.addEventListener('beforeinstallprompt', onBeforeInstall)
    window.addEventListener('appinstalled', onInstalled)
    mq.addEventListener('change', onStandaloneChange)
    return () => {
      window.removeEventListener('beforeinstallprompt', onBeforeInstall)
      window.removeEventListener('appinstalled', onInstalled)
      mq.removeEventListener('change', onStandaloneChange)
    }
  }, [])

  // ¿El navegador puede instalar y aún no lo ofrecimos/descartamos?
  const installable = Boolean(deferred) && !standalone && state === null

  const promptInstall = useCallback(async (): Promise<PromptOutcome> => {
    if (standalone) return 'unavailable'
    if (isIos()) return 'ios'
    if (!deferred) return 'unavailable'

    await deferred.prompt()
    const choice = await deferred.userChoice
    setDeferred(null)
    if (choice.outcome === 'accepted') {
      setState('completed')
      return 'accepted'
    }
    return 'dismissed'
  }, [deferred, standalone])

  const dismiss = useCallback(() => {
    // No anulamos el deferred prompt: así, aunque el banner se haya descartado,
    // el CTA manual de Perfil sigue pudiendo disparar la instalación nativa.
    setState('dismissed')
  }, [])

  return useMemo(
    () => ({
      installable,
      isIos: isIos(),
      isStandalone: standalone,
      promptInstall,
      dismiss,
    }),
    [installable, standalone, promptInstall, dismiss],
  )
}

export type InstallPromptApi = ReturnType<typeof useInstallPrompt>
