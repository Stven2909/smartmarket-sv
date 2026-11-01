import { useEffect, useRef } from 'react'

type Props = {
  description: string
  onCancel: () => void
  onConfirm: () => void
}

export function LocationConsentDialog({ description, onCancel, onConfirm }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const onCancelRef = useRef(onCancel)

  useEffect(() => {
    onCancelRef.current = onCancel
  }, [onCancel])

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return

    dialog.showModal()
    const handleCancel = (event: Event) => {
      event.preventDefault()
      onCancelRef.current()
    }
    dialog.addEventListener('cancel', handleCancel)

    return () => {
      dialog.removeEventListener('cancel', handleCancel)
      if (dialog.open) dialog.close()
    }
  }, [])

  return (
    <dialog
      ref={dialogRef}
      className="location-consent-dialog"
      aria-labelledby="location-consent-title"
      aria-describedby="location-consent-description"
    >
      <div className="location-consent-icon" aria-hidden="true">📍</div>
      <span className="eyebrow">TU PRIVACIDAD</span>
      <h2 id="location-consent-title">¿Deseas compartir tu ubicación?</h2>
      <p id="location-consent-description">{description}</p>
      <div className="location-consent-actions">
        <button type="button" className="load-more-button" autoFocus onClick={onCancel}>
          Ahora no
        </button>
        <button type="button" className="add-button" onClick={onConfirm}>
          Continuar
        </button>
      </div>
    </dialog>
  )
}
