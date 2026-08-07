import { useEffect, useMemo, useState } from 'react'
import { ApiError } from '../api/client'
import { buscarProductos } from '../api/catalog'
import * as listsApi from '../api/lists'
import { formatMoney } from '../lib/format'
import { productFromApi } from '../types/domain'
import type { Product } from '../types/domain'
import { ProductCard } from './ProductCard'
import { SearchBox } from './SearchBox'

export function BuscarView() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Product[]>([])
  const [searchedQuery, setSearchedQuery] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const [listas, setListas] = useState<Awaited<ReturnType<typeof listsApi.fetchListas>>>([])
  const [selectedListaId, setSelectedListaId] = useState<number | null>(null)
  const [addMessage, setAddMessage] = useState<string | null>(null)

  useEffect(() => {
    loadListas()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function runSearch() {
    const q = query.trim()
    if (q.length < 2) return
    setLoading(true)
    setError(null)
    setResults([])
    try {
      const data = await buscarProductos(q)
      setResults(data.data.map(productFromApi))
      setSearchedQuery(q)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'No se pudo completar la búsqueda.')
      setSearchedQuery(q)
    } finally {
      setLoading(false)
    }
  }

  async function loadListas() {
    try {
      const data = await listsApi.fetchListas('activa')
      setListas(data)
      if (selectedListaId == null && data.length > 0) setSelectedListaId(data[0].id)
    } catch {
      setListas([])
    }
  }

  async function addToSelectedList(productId: number) {
    setAddMessage(null)
    if (!selectedListaId) {
      setAddMessage('Primero crea o selecciona una lista.')
      return
    }
    try {
      await listsApi.addProductoToLista(selectedListaId, productId)
      setAddMessage('Producto agregado a tu lista.')
      await loadListas()
    } catch {
      setAddMessage('No se pudo agregar el producto.')
    }
  }

  const totalCost = useMemo(
    () =>
      results.reduce((sum, product) => {
        const best = [...product.offers].sort((a, b) => a.price - b.price)[0]
        return sum + (Number(best?.price) || 0)
      }, 0),
    [results],
  )

  return (
    <div className="view" style={{ maxWidth: 860 }}>
      <div className="page-heading">
        <div className="eyebrow"><span />BUSCADOR UNIVERSAL</div>
        <h1>Busca y compara en todos los supermercados</h1>
        <SearchBox query={query} setQuery={setQuery} onSubmit={runSearch} large />
      </div>

      {addMessage && <div className="toast">{addMessage}</div>}
      {error && <div className="live-error"><b>Búsqueda incompleta</b><span>{error}</span></div>}
      {loading && <div className="live-loading"><i />Buscando…</div>}

      {!loading && searchedQuery && results.length === 0 && !error && (
        <div className="empty-state">
          <h3>Sin coincidencias para "{searchedQuery}"</h3>
          <p>Prueba con arroz, leche, café o el nombre de una marca.</p>
        </div>
      )}

      {results.length > 0 && (
        <>
          <div className="store-search-filter">
            <select
              value={selectedListaId ?? ''}
              onChange={(e) => setSelectedListaId(e.target.value ? Number(e.target.value) : null)}
              aria-label="Lista destino"
            >
              <option value="">Agregar a lista…</option>
              {listas.map((lista) => (
                <option key={lista.id} value={lista.id}>{lista.nombre}</option>
              ))}
            </select>
            <span className="search-summary">
              {results.length} {results.length === 1 ? 'resultado' : 'resultados'} · total estimado <b>{formatMoney(totalCost)}</b>
            </span>
          </div>

          <div className="live-products">
            {results.map((product) => (
              <ProductCard key={product.id} product={product} onAddToList={() => void addToSelectedList(product.id)} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
