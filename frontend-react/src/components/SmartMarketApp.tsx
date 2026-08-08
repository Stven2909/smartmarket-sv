import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { fetchCategorias, fetchProductos, fetchProducto, fetchSucursales, fetchHistorialPrecios } from '../api/catalog'
import * as listsApi from '../api/lists'
import { productFromApi, productLiteFromApi, historialPrecioFromApi } from '../types/domain'
import type { Branch, Category, HistorialPrecio, Product } from '../types/domain'
import { formatMoney } from '../lib/format'
import { useInstallPrompt } from '../lib/useInstallPrompt'
import { CategoryIcon } from './CategoryIcon'
import { BarChart2, Bell, ChevronLeft, Home, ListChecks, Plus, Search, User } from 'lucide-react'
import { ProductCard } from './ProductCard'
import { Promotions } from './Promotions'
import { SavingsByCategory } from './SavingsByCategory'
import { ListasView } from './ListasView'
import { PerfilView } from './PerfilView'
import { BuscarView } from './BuscarView'
import { CompararView } from './CompararView'
import { HomeFeed } from './HomeFeed'
import { InstallPrompt } from './InstallPrompt'

function formatDate(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString('es-SV', { day: 'numeric', month: 'short', year: 'numeric' })
}

type View = 'inicio' | 'buscar' | 'comparar' | 'mis-listas' | 'perfil' | 'categorias' | 'promociones' | 'sucursales'

const NAV: Array<{ id: View; label: string; icon: typeof Home }> = [
  { id: 'inicio', label: 'Inicio', icon: Home },
  { id: 'buscar', label: 'Buscar', icon: Search },
  { id: 'comparar', label: 'Comparar', icon: BarChart2 },
  { id: 'mis-listas', label: 'Mis listas', icon: ListChecks },
  { id: 'perfil', label: 'Perfil', icon: User },
]

const NAV_ACTIVE_PARENT: Partial<Record<View, View>> = {
  categorias: 'inicio',
  promociones: 'inicio',
  sucursales: 'perfil',
}

export function SmartMarketApp() {
  const { user } = useAuth()
  const [view, setView] = useState<View>('inicio')

  // La invitación de instalación no aparece en el primer render: solo cuando el
  // usuario ya interactuó con la app (salió de Inicio) o pasaron 30 segundos.
  const [engagement, setEngagement] = useState(false)
  useEffect(() => {
    if (view !== 'inicio') setEngagement(true)
  }, [view])
  useEffect(() => {
    const t = window.setTimeout(() => setEngagement(true), 30_000)
    return () => window.clearTimeout(t)
  }, [])
  const install = useInstallPrompt()

  const [categories, setCategories] = useState<Category[]>([])
  const [branches, setBranches] = useState<Branch[]>([])
  const [listas, setListas] = useState<Awaited<ReturnType<typeof listsApi.fetchListas>>>([])

  // catálogo
  const [catalog, setCatalog] = useState<Product[]>([])
  const [catalogCategory, setCatalogCategory] = useState<number | null>(null)
  const [catalogPage, setCatalogPage] = useState(1)
  const [catalogHasMore, setCatalogHasMore] = useState(false)
  const [catalogTotal, setCatalogTotal] = useState(0)
  const [detail, setDetail] = useState<Product | null>(null)

  // historial de precios del producto en detalle (Fase 5)
  const [historial, setHistorial] = useState<HistorialPrecio[]>([])
  const [historialError, setHistorialError] = useState<string | null>(null)
  const [historialLoading, setHistorialLoading] = useState(false)

  const loadCategories = useCallback(async () => {
    try {
      setCategories(await fetchCategorias())
    } catch {
      setCategories([])
    }
  }, [])

  const loadBranches = useCallback(async () => {
    try {
      setBranches(await fetchSucursales())
    } catch {
      setBranches([])
    }
  }, [])

  const loadListas = useCallback(async () => {
    try {
      setListas(await listsApi.fetchListas('activa'))
    } catch {
      setListas([])
    }
  }, [])

  useEffect(() => {
    loadCategories()
    loadBranches()
    loadListas()
  }, [loadCategories, loadBranches, loadListas])

  async function loadCatalog(page = 1) {
    try {
      const data = await fetchProductos(page, catalogCategory ?? undefined)
      setCatalog(data.data.map(productLiteFromApi))
      setCatalogPage(data.current_page)
      setCatalogHasMore(data.current_page < data.last_page)
      setCatalogTotal(data.total)
    } catch {
      setCatalog([])
    }
  }

  useEffect(() => {
    if (view !== 'categorias') return
    setCatalogPage(1)
    loadCatalog(1)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, catalogCategory])

  async function openDetail(id: number) {
    try {
      const full = await fetchProducto(id)
      setDetail(productFromApi(full))
    } catch {
      setDetail(null)
    }
    setHistorial([])
    setHistorialError(null)
    setHistorialLoading(true)
    try {
      const data = await fetchHistorialPrecios(id)
      setHistorial(data.data.map(historialPrecioFromApi))
    } catch {
      setHistorialError('No se pudo cargar el historial de precios.')
    } finally {
      setHistorialLoading(false)
    }
  }

  function openCategory(id: number) {
    setCatalogCategory(id)
    setView('categorias')
  }

  const activeNavId = NAV_ACTIVE_PARENT[view] ?? view
  const showFab = view !== 'mis-listas' && view !== 'perfil'
  const initial = (user?.name?.trim().charAt(0) ?? 'U').toUpperCase()

  return (
    <div className="app-shell">
      <header className="app-header">
        <button type="button" className="app-brand" onClick={() => setView('inicio')} aria-label="Ir al inicio">
          <span className="app-brand-mark" aria-hidden="true"><i /><i /></span>
          <span>Smart<b>Market</b> SV</span>
        </button>

        <nav className="desktop-nav" aria-label="Secciones principales">
          {NAV.map((item) => {
            const Icon = item.icon
            return (
              <button
                key={item.id}
                type="button"
                className={activeNavId === item.id ? 'active' : ''}
                onClick={() => setView(item.id)}
                aria-current={activeNavId === item.id ? 'page' : undefined}
              >
                <Icon size={16} />
                {item.label}
              </button>
            )
          })}
        </nav>

        <div className="header-actions">
          <button type="button" className="icon-button" onClick={() => setView('promociones')} aria-label="Promociones">
            <Bell size={18} />
          </button>
          <button type="button" className="avatar-button" onClick={() => setView('perfil')} aria-label="Tu perfil">
            {initial}
          </button>
        </div>
      </header>

      <main>
        {view === 'inicio' && (
          <HomeFeed
            userName={user?.name ?? ''}
            categories={categories}
            listas={listas}
            onSearch={() => setView('buscar')}
            onOpenCategory={openCategory}
            onOpenPromociones={() => setView('promociones')}
            onOpenMisListas={() => setView('mis-listas')}
          />
        )}

        {view === 'buscar' && <BuscarView />}

        {view === 'comparar' && (
          <CompararView onListasChange={setListas} onOpenMisListas={() => setView('mis-listas')} />
        )}

        {view === 'mis-listas' && (
          <div className="view">
            <ListasView onListasChange={setListas} />
          </div>
        )}

        {view === 'perfil' && <PerfilView onOpenSucursales={() => setView('sucursales')} install={install} />}

        {view === 'categorias' && (
          <div className="view">
            <button type="button" className="link-button" onClick={() => setView('inicio')} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, marginBottom: 12 }}>
              <ChevronLeft size={16} /> Volver al inicio
            </button>
            <div className="page-heading">
              <div className="eyebrow"><span />CATÁLOGO</div>
              <h1>Explora el catálogo ({catalogTotal})</h1>
              <div className="category-filters" style={{ marginTop: 14 }}>
                <button
                  type="button"
                  className={catalogCategory === null ? 'active' : ''}
                  onClick={() => setCatalogCategory(null)}
                >
                  Todas
                </button>
                {categories.map((category) => (
                  <button
                    key={category.id}
                    type="button"
                    className={catalogCategory === category.id ? 'active' : ''}
                    onClick={() => setCatalogCategory(category.id)}
                  >
                    {category.name}
                  </button>
                ))}
              </div>
            </div>

            {detail && (
              <section className="category-results">
                <div className="category-results-head">
                  <div>
                    <span className="eyebrow"><CategoryIcon name={detail.categoryName} size={13} /> DETALLE</span>
                    <h2>{detail.name}</h2>
                    <p>{[detail.unitLabel, detail.categoryName].filter(Boolean).join(' · ')}</p>
                  </div>
                  <button type="button" className="link-button" onClick={() => setDetail(null)}>Cerrar detalle</button>
                </div>
                <ProductCard product={detail} />

                <div className="optimizer-panel" style={{ marginTop: 18 }}>
                  <div className="optimizer-head">
                    <span className="spark-icon">📈</span>
                    <div>
                      <span>HISTORIAL DE PRECIOS</span>
                      <h2>Evolución por supermercado</h2>
                    </div>
                  </div>
                  {historialLoading && <div className="live-loading"><i />Cargando historial…</div>}
                  {!historialLoading && historialError && (
                    <div className="live-error"><b>Historial no disponible</b><span>{historialError}</span></div>
                  )}
                  {!historialLoading && !historialError && historial.length === 0 && (
                    <div className="empty-optimizer">
                      <span>📈</span>
                      <h3>Sin historial registrado</h3>
                      <p>Los cambios de precio de este producto aún no se han registrado.</p>
                    </div>
                  )}
                  {!historialLoading && historial.length > 0 && (
                    <div className="store-table">
                      <div className="store-table-head">
                        <span>Fecha</span>
                        <span>Supermercado</span>
                        <span>Precio</span>
                      </div>
                      {historial.map((h) => (
                        <div key={h.id} className="store-table-row">
                          <div>
                            <b>{formatDate(h.fecha) || '—'}</b>
                            {h.origen && <small> · {h.origen}</small>}
                          </div>
                          <div>
                            <b>{h.sucursal.supermarket.name}</b>
                            <small> · {h.sucursal.name}</small>
                          </div>
                          <span className="saving-price" style={{ justifyContent: 'flex-end' }}>
                            {h.tienePromo && h.precioNormal > h.precioFinal && (
                              <s>{formatMoney(h.precioNormal)}</s>
                            )}
                            <b>{formatMoney(h.precioFinal)}</b>
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </section>
            )}

            <div className="category-products-grid">
              {catalog.map((product) => (
                <button
                  key={product.id}
                  type="button"
                  className="category-product-card"
                  onClick={() => void openDetail(product.id)}
                >
                  <span className="product-emoji"><CategoryIcon name={product.categoryName} size={22} /></span>
                  <div className="category-product-body">
                    <h3>{product.name}</h3>
                    <p>{[product.unitLabel, product.categoryName].filter(Boolean).join(' · ')}</p>
                  </div>
                </button>
              ))}
            </div>

            {catalog.length === 0 && (
              <div className="empty-state compact">
                <h3>Sin resultados</h3>
                <p>Prueba con otra categoría o vuelve más tarde.</p>
              </div>
            )}

            {catalogHasMore && (
              <div className="category-filters" style={{ marginTop: 20, justifyContent: 'center' }}>
                <button type="button" className="load-more-button" onClick={() => void loadCatalog(catalogPage + 1)}>
                  Cargar más productos
                </button>
              </div>
            )}
          </div>
        )}

        {view === 'promociones' && (
          <div className="view">
            <button type="button" className="link-button" onClick={() => setView('inicio')} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, marginBottom: 12 }}>
              <ChevronLeft size={16} /> Volver al inicio
            </button>
            <div className="page-heading">
              <div className="eyebrow"><span />OFERTAS</div>
              <h1>Promociones activas</h1>
            </div>
            <Promotions />
            <SavingsByCategory />
          </div>
        )}

        {view === 'sucursales' && (
          <div className="view">
            <button type="button" className="link-button" onClick={() => setView('perfil')} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, marginBottom: 12 }}>
              <ChevronLeft size={16} /> Volver a perfil
            </button>
            <div className="page-heading">
              <div className="eyebrow"><span />SUCURSALES</div>
              <h1>Encuentra supermercados cercanos</h1>
              <p className="data-disclaimer" style={{ marginTop: 14 }}>
                La lista muestra las sucursales del catálogo con su supermercado. La distancia
                es aproximada y no sustituye la ruta ni el inventario oficial.
              </p>
            </div>

            {branches.length === 0 && (
              <div className="empty-state compact">
                <h3>No hay datos</h3>
                <p>No pudimos cargar las sucursales.</p>
              </div>
            )}

            <div className="nearby-branches">
              {branches.map((branch) => (
                <article key={branch.id} className="location-result">
                  <div className="store-badge" style={{ background: branch.supermarket.color }}>
                    {branch.supermarket.name.slice(0, 2).toUpperCase()}
                  </div>
                  <div>
                    <strong>{branch.name}</strong>
                    <span>{branch.supermarket.name}</span>
                    {branch.address && <small>{branch.address}</small>}
                    {branch.schedule && <small>Horario: {branch.schedule}</small>}
                    {branch.phone && <small>Tel: {branch.phone}</small>}
                  </div>
                </article>
              ))}
            </div>
          </div>
        )}
      </main>

      <nav className="bottom-nav" aria-label="Navegación principal">
        {NAV.map((item) => {
          const Icon = item.icon
          return (
            <button
              key={item.id}
              type="button"
              className={activeNavId === item.id ? 'active' : ''}
              onClick={() => setView(item.id)}
              aria-current={activeNavId === item.id ? 'page' : undefined}
            >
              <Icon size={20} />
              {item.label}
            </button>
          )
        })}
      </nav>

      {showFab && (
        <button type="button" className="fab" onClick={() => setView('mis-listas')}>
          <Plus size={18} /> Nueva lista
        </button>
      )}

      <footer className="app-footer">
        <div className="neutrality-banner">
          <span className="neutral-icon">⚖️</span>
          <div>
            <strong>Neutralidad primero.</strong>
            <p>Las recomendaciones se calculan con precio, distancia, tiempo y disponibilidad.
            La publicidad nunca cambia el resultado.</p>
          </div>
        </div>
        <p className="data-disclaimer">SmartMarket SV · datos de ejemplo del catálogo maestro · precios manuales</p>
      </footer>

      {install.installable && engagement && (
        <InstallPrompt variant="banner" install={install} onClose={() => {}} />
      )}
    </div>
  )
}
