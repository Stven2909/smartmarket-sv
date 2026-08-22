// Tipos de dominio que consume la UI, con adaptadores desde el contrato Laravel.
// No se copian los tipos del mock de Isaac: estos reflejan el contrato real de la API.

import { categoryIcon, supermarketColor } from '../lib/presentation'
import type {
  ApiCategoria,
  ApiCompararResultado,
  ApiDetalle,
  ApiHistorialPrecio,
  ApiLista,
  ApiListaShow,
  ApiOptimizarResultado,
  ApiPrecioActual,
  ApiPromocion,
  ApiProductoFull,
  ApiProductoLite,
  ApiSucursal,
} from './api'

export type Category = {
  id: number
  name: string
  icon: string
}

export type Supermarket = {
  id: number
  name: string
  logo: string | null
  webUrl: string | null
  color: string
}

export type Branch = {
  id: number
  name: string
  address: string | null
  lat: number | null
  lng: number | null
  phone: string | null
  schedule: string | null
  supermarket: Supermarket
}

export type Offer = {
  branchId: number
  branchName: string
  supermarketId: number
  supermarketName: string
  price: number
  previousPrice?: number
  hasPromo: boolean
  promoType?: string
  savings?: number
  discountPercent?: number
}

export type Product = {
  id: number
  name: string
  brand: string | null
  unitLabel: string
  categoryName: string
  categoryIcon: string
  offers: Offer[]
}

export type Promotion = {
  id: string
  productId: number
  productName: string
  categoryName: string
  categoryIcon: string
  unitLabel: string
  supermarketId: number
  supermarketName: string
  branchName: string
  price: number
  previousPrice?: number
  savings?: number
  discountPercent?: number
  promotionText: string
  kind: 'discount' | 'published'
}

export type ListaSummary = {
  id: number
  nombre: string
  presupuesto: number | null
  estado: string
  fecha: string
  detallesCount: number
}

export type HistorialPrecio = {
  id: number
  fecha: string
  precioNormal: number
  precioFinal: number
  tienePromo: boolean
  tipoPromocion: string | null
  origen: string | null
  sucursal: Branch
}

export type ListaDetalle = {
  id: number
  productoId: number
  nombre: string
  categoria: string
  cantidad: number
  esencial: boolean
}

export type CompararResultado = {
  sucursalId: number
  sucursal: string
  supermercado: string
  latitud: number
  longitud: number
  costoTotal: number
  beneficioPromociones: number
  productosConPromocion: number
  esencialesDisponibles: number
  esencialesTotales: number
  opcionalesDisponibles: number
  opcionalesTotales: number
  todosLosEsenciales: boolean
  dentroDelPresupuesto: boolean | null
}

export type OptimizarResultado = CompararResultado & {
  distanciaKm: number
  penalizacionDistancia: number
  tiempoMinutos: number
  costoTiempo: number
  score: number
  nivelOptimizacion: number
}

// ---------------------------------------------------------------------------
// Adaptadores
// ---------------------------------------------------------------------------

export function categoryFromApi(cat: ApiCategoria): Category {
  return { id: cat.id, name: cat.nombre, icon: categoryIcon(cat.nombre) }
}

export function supermarketFromApi(s: ApiSucursal['supermercado']): Supermarket {
  return {
    id: s.id,
    name: s.nombre,
    logo: s.logo,
    webUrl: s.sitio_web,
    color: supermarketColor(s.nombre),
  }
}

export function branchFromApi(suc: ApiSucursal): Branch {
  return {
    id: suc.id,
    name: suc.nombre,
    address: suc.direccion,
    lat: suc.latitud,
    lng: suc.longitud,
    phone: suc.telefono,
    schedule: suc.horario,
    supermarket: supermarketFromApi(suc.supermercado),
  }
}

// Convierte a número real los valores que Laravel serializa como string
// (columnas NUMERIC/DECIMAL de PostgreSQL: "1.85"). Nunca devuelve 0 silencioso:
// si el campo no viene (null/undefined/vacío) devuelve NaN, y formatMoney lo
// muestra como "—" en vez de inventar un precio.
function num(value: unknown): number {
  if (typeof value === 'number') return value
  if (typeof value === 'string' && value !== '') return Number(value)
  return NaN
}

export function unitLabel(p: ApiProductoLite): string {
  if (p.presentacion) return p.presentacion
  if (p.contenido != null && p.unidad_medida) return `${p.contenido} ${p.unidad_medida}`
  return ''
}

export function offerFromApi(precio: ApiPrecioActual): Offer {
  const precioFinal = num(precio.precio_final)
  const precioNormal = num(precio.precio_normal)
  const hasPromo = Boolean(precio.tiene_promocion && precioFinal < precioNormal)
  const savings = hasPromo ? precioNormal - precioFinal : undefined
  const discountPercent = hasPromo && savings
    ? Math.round((savings / precioNormal) * 100)
    : undefined
  return {
    branchId: precio.sucursal.id,
    branchName: precio.sucursal.nombre,
    supermarketId: precio.sucursal.supermercado.id,
    supermarketName: precio.sucursal.supermercado.nombre,
    price: precioFinal,
    previousPrice: hasPromo ? precioNormal : undefined,
    hasPromo,
    promoType: precio.tipo_promocion ?? undefined,
    savings,
    discountPercent,
  }
}

export function productFromApi(p: ApiProductoFull): Product {
  return {
    id: p.id,
    name: p.nombre,
    brand: p.marca,
    unitLabel: unitLabel(p),
    categoryName: p.categoria?.nombre ?? '',
    categoryIcon: categoryIcon(p.categoria?.nombre ?? ''),
    offers: (p.precios_actuales ?? []).map(offerFromApi),
  }
}

export function productLiteFromApi(p: ApiProductoLite): Product {
  return {
    id: p.id,
    name: p.nombre,
    brand: p.marca,
    unitLabel: unitLabel(p),
    categoryName: p.categoria?.nombre ?? '',
    categoryIcon: categoryIcon(p.categoria?.nombre ?? ''),
    offers: [],
  }
}

export function promotionFromApi(precio: ApiPromocion): Promotion {
  const producto = precio.producto
  const precioFinal = num(precio.precio_final)
  const precioNormal = num(precio.precio_normal)
  const hasDiscount = Boolean(precio.tiene_promocion && precioFinal < precioNormal)
  const savings = hasDiscount ? precioNormal - precioFinal : undefined
  const discountPercent = hasDiscount && savings
    ? Math.round((savings / precioNormal) * 100)
    : undefined
  const productName = producto?.nombre ?? `Producto ${precio.producto_id}`
  const categoryName = producto?.categoria?.nombre ?? ''
  return {
    id: `${precio.producto_id}:${precio.sucursal_id}`,
    productId: precio.producto_id,
    productName,
    categoryName,
    categoryIcon: categoryIcon(categoryName),
    unitLabel: producto ? unitLabel(producto) : '',
    supermarketId: precio.sucursal.supermercado.id,
    supermarketName: precio.sucursal.supermercado.nombre,
    branchName: precio.sucursal.nombre,
    price: precioFinal,
    previousPrice: hasDiscount ? precioNormal : undefined,
    savings,
    discountPercent,
    promotionText: hasDiscount ? `Ahorras ${discountPercent}%` : (precio.tipo_promocion ?? 'Promoción'),
    kind: hasDiscount ? 'discount' : 'published',
  }
}

export function listaFromApi(l: ApiLista): ListaSummary {
  return {
    id: l.id,
    nombre: l.nombre,
    presupuesto: l.presupuesto,
    estado: l.estado ?? 'activa',
    fecha: l.fecha,
    detallesCount: l.detalles_count ?? 0,
  }
}

export function listaShowFromApi(l: ApiListaShow): ListaSummary & { detalles: ListaDetalle[] } {
  return {
    id: l.id,
    nombre: l.nombre,
    presupuesto: l.presupuesto,
    estado: l.estado ?? 'activa',
    fecha: l.fecha,
    detallesCount: l.detalles?.length ?? 0,
    detalles: (l.detalles ?? []).map(detalleFromApi),
  }
}

export function historialPrecioFromApi(h: ApiHistorialPrecio): HistorialPrecio {
  const precioNormal = num(h.precio_normal)
  const precioFinal = num(h.precio_final)
  const hasPromo = Boolean(h.tipo_promocion && precioFinal < precioNormal)
  return {
    id: h.id,
    fecha: h.fecha,
    precioNormal,
    precioFinal,
    tienePromo: hasPromo,
    tipoPromocion: h.tipo_promocion,
    origen: h.origen,
    sucursal: branchFromApi(h.sucursal),
  }
}

export function detalleFromApi(d: ApiDetalle): ListaDetalle {
  return {
    id: d.id,
    productoId: d.producto_id,
    nombre: d.producto?.nombre ?? `Producto ${d.producto_id}`,
    categoria: d.producto?.categoria?.nombre ?? '',
    cantidad: d.cantidad,
    esencial: Boolean(d.esencial),
  }
}

export function compararResultadoFromApi(r: ApiCompararResultado): CompararResultado {
  return {
    sucursalId: r.sucursal_id,
    sucursal: r.sucursal,
    supermercado: r.supermercado,
    latitud: r.latitud,
    longitud: r.longitud,
    costoTotal: r.costo_total,
    beneficioPromociones: r.beneficio_promociones,
    productosConPromocion: r.productos_con_promocion,
    esencialesDisponibles: r.productos_esenciales_disponibles,
    esencialesTotales: r.productos_esenciales_totales,
    opcionalesDisponibles: r.productos_opcionales_disponibles,
    opcionalesTotales: r.productos_opcionales_totales,
    todosLosEsenciales: r.todos_los_esenciales_disponibles,
    dentroDelPresupuesto: r.dentro_del_presupuesto,
  }
}

export function optimizarResultadoFromApi(r: ApiOptimizarResultado): OptimizarResultado {
  return {
    ...compararResultadoFromApi(r),
    distanciaKm: r.distancia_km,
    penalizacionDistancia: r.penalizacion_distancia,
    tiempoMinutos: r.tiempo_minutos,
    costoTiempo: r.costo_tiempo,
    score: r.score,
    nivelOptimizacion: r.nivel_optimizacion,
  }
}
