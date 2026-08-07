import { useState } from 'react'
import { useNavigate } from 'react-router'

export function NotFound() {
  const navigate = useNavigate()
  const [imgBroken, setImgBroken] = useState(false)

  return (
    <div className="app-shell">
      <div className="notfound-wrap">
        <div className="mascot-stage" aria-hidden="true">
          {imgBroken ? (
            <span className="mascot-brand-fallback"><i /><i /></span>
          ) : (
            <img
              className="mascot-img"
              src="/mascota/Smarty_404.webp"
              alt=""
              onError={() => setImgBroken(true)}
            />
          )}
        </div>
        <span className="eyebrow">ERROR 404</span>
        <h1 className="notfound-title">Uy… esto no está en el pasillo</h1>
        <p className="notfound-copy">
          La página que buscás no existe o se cambió de estante.
          Volvé al inicio para seguir ahorrando.
        </p>
        <button type="button" className="add-button" onClick={() => navigate('/')}>
          Volver al inicio
        </button>
      </div>
    </div>
  )
}
