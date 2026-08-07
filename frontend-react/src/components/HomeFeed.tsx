import { useEffect, useState } from 'react'
import { fetchPromociones } from '../api/promos'
import { friendlyError } from '../api/client'
import { CheckCircle2, ChevronRight, Search, ShoppingBag, Tag, TrendingUp } from 'lucide-react'
import { formatMoney } from '../lib/format'
import type { Category, ListaSummary, Promotion } from '../types/domain'
import { Promotions } from './Promotions'
import { SavingsByCategory } from './SavingsByCategory'

function formatDate(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString('es-SV', { day: 'numeric', month: 'short' })
}

type Props = {
  userName: string
  categories: Category[]
  listas: ListaSummary[]
  onSearch: () => void
  onOpenCategory: (id: number) => void
  onOpenPromociones: () => void
  onOpenMisListas: () => void
}

export function HomeFeed({ userName, categories, listas, onSearch, onOpenCategory, onOpenPromociones, onOpenMisListas }: Props) {
  const [promotions, setPromotions] = useState<Promotion[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    fetchPromociones(undefined, controller.signal)
      .then(setPromotions)
      .catch((e) => setError(friendlyError(e, 'No pudimos cargar las ofertas de hoy.')))
    return () => controller.abort()
  }, [])

  const discounted = promotions.filter((p) => p.discountPercent != null)
  const bestPromo = [...discounted].sort((a, b) => (b.discountPercent ?? 0) - (a.discountPercent ?? 0))[0]
  const maxDiscount = bestPromo?.discountPercent ?? null
  const firstName = userName.trim().split(/\s+/)[0] || userName

  const recent = listas.slice(0, 3)

  return (
    <div className="view">
      <div className="greeting">
        <span className="slogan">Decisiones inteligentes para cada compra</span>
        <h1>Hola, {firstName}</h1>
        <p>Aquí está todo lo que necesitas para tu próxima compra.</p>
      </div>

      <div className="savings-strip">
        {promotions.length > 0 && (
          <span className="stat-chip">
            <Tag size={16} />
            <b>{promotions.length}</b> {promotions.length === 1 ? 'oferta activa' : 'ofertas activas'} hoy
          </span>
        )}
        {maxDiscount != null && (
          <span className="stat-chip positive">
            <TrendingUp size={16} />
            Hasta <b>-{maxDiscount}%</b> de descuento
          </span>
        )}
        <span className="stat-chip">
          <ShoppingBag size={16} />
          <b>{listas.length}</b> {listas.length === 1 ? 'lista guardada' : 'listas guardadas'}
        </span>
      </div>

      <div className="feed-section">
        <button type="button" className="search-prompt" onClick={onSearch}>
          <Search size={20} />
          Busca un producto y compara precios en todos los supermercados
          <ChevronRight size={18} style={{ marginLeft: 'auto' }} />
        </button>
      </div>

      {categories.length > 0 && (
        <section className="feed-section">
          <div className="feed-section-head">
            <h2>Categorías para cada compra</h2>
            <span>{categories.length} categorías</span>
          </div>
          <div className="category-scroll">
            {categories.map((category) => (
              <button
                key={category.id}
                type="button"
                className="category-dot"
                onClick={() => onOpenCategory(category.id)}
              >
                <span className="category-dot-icon">{category.icon}</span>
                <b>{category.name}</b>
              </button>
            ))}
          </div>
        </section>
      )}

      <section className="feed-section">
        <div className="feed-section-head">
          <h2>Sugerencia para esta compra</h2>
        </div>
        {bestPromo ? (
          <article className="rec-card">
            <span className="rec-icon"><TrendingUp size={24} /></span>
            <div>
              <h3>Hoy, {bestPromo.productName} bajó de precio</h3>
              <p className="rec-copy">
                En <b>{bestPromo.supermarketName}</b> lo encontrás en <b>{formatMoney(bestPromo.price)}</b>,
                un <b className="rec-save">{bestPromo.discountPercent}% de descuento</b> sobre su precio anterior.
              </p>
              <div className="rec-actions">
                <button type="button" className="add-button" onClick={onSearch}>Comparar precios</button>
                <button type="button" className="link-button" onClick={onOpenPromociones}>Ver todas las promos</button>
              </div>
            </div>
          </article>
        ) : (
          <article className="rec-card">
            <span className="rec-icon"><CheckCircle2 size={24} /></span>
            <div>
              <h3>Guarda tu canasta y compará</h3>
              <p className="rec-copy">
                {listas.length > 0
                  ? 'Tu última lista está lista para comparar. Elegí el supermercado con mejor precio hoy.'
                  : 'Creá tu primera lista y el sistema te dirá dónde conviene comprar según costo y distancia.'}
              </p>
              <div className="rec-actions">
                <button type="button" className="add-button" onClick={onOpenMisListas}>
                  {listas.length > 0 ? 'Comparar mi lista' : 'Crear mi primera lista'}
                </button>
              </div>
            </div>
          </article>
        )}
      </section>

      <section className="feed-section">
        <div className="feed-section-head">
          <h2>Tus listas recientes</h2>
          {listas.length > 0 && <span>{listas.length} total</span>}
        </div>
        {recent.length === 0 ? (
          <div className="empty-state compact">
            <h3>Creá una lista para empezar</h3>
            <p>Las listas que guardes aparecerán aquí para comparar sus precios al instante.</p>
          </div>
        ) : (
          <div style={{ display: 'grid', gap: 10 }}>
            {recent.map((lista) => (
              <button key={lista.id} type="button" className="recent-list-card" onClick={onOpenMisListas}>
                <span className="recent-list-icon"><ShoppingBag size={20} /></span>
                <div>
                  <b>{lista.nombre}</b>
                  <small>{lista.detallesCount} productos · {lista.presupuesto != null ? formatMoney(lista.presupuesto) : 'sin presupuesto'} · {formatDate(lista.fecha) || 'reciente'}</small>
                </div>
                <span className="recent-list-save"><ChevronRight size={18} /></span>
              </button>
            ))}
          </div>
        )}
      </section>

      {discounted.length > 0 && (
        <section className="feed-section">
          <div className="feed-section-head">
            <h2>Bajaron de precio hoy</h2>
            <span>{discounted.length} productos</span>
          </div>
          <div className="h-scroll">
            {discounted.slice(0, 8).map((promo) => (
              <button key={promo.id} type="button" className="drop-card" onClick={onOpenPromociones}>
                <span className="product-emoji">{promo.categoryIcon}</span>
                <b>{promo.productName}</b>
                <small>{promo.supermarketName} · {formatMoney(promo.price)}</small>
                <span className="drop-save">-{promo.discountPercent}% <Tag size={13} /></span>
              </button>
            ))}
          </div>
        </section>
      )}

      {bestPromo && (
        <section className="feed-section">
          <button type="button" className="promo-of-day" onClick={onOpenPromociones} style={{ width: '100%', textAlign: 'left', border: 0 }}>
            <span className="promotion-emoji">{bestPromo.categoryIcon}</span>
            <span className="promotion-badge">-{bestPromo.discountPercent}%</span>
            <span className="eyebrow">PROMO DEL DÍA</span>
            <h3>{bestPromo.productName}</h3>
            <p>{bestPromo.supermarketName} · {formatMoney(bestPromo.price)}
              {bestPromo.previousPrice != null ? ` · antes ${formatMoney(bestPromo.previousPrice)}` : ''}</p>
          </button>
        </section>
      )}

      <Promotions />
      <SavingsByCategory />

      {error && (
        <div className="live-error"><b>Ofertas de hoy no disponibles</b><span>{error}</span></div>
      )}
    </div>
  )
}
