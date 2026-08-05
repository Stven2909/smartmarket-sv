import { ChevronRight, LogOut, MapPin } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

type Props = {
  onOpenSucursales: () => void
}

export function PerfilView({ onOpenSucursales }: Props) {
  const { user, logout } = useAuth()
  const initial = (user?.name?.trim().charAt(0) ?? 'U').toUpperCase()

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
    </div>
  )
}
