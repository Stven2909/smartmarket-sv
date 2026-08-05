// Presentación pura (iconos/colores por categoría y supermercado).
// No es lógica de negocio: solo mapea nombres existentes del backend a íconos.

const CATEGORY_ICONS: Record<string, string> = {
  'Lácteos': '🥛',
  'Bebidas': '🥤',
  'Limpieza': '🧼',
  'Granos básicos': '🫘',
  'Higiene personal': '🧴',
}

const CATEGORY_FALLBACK = '🛒'

export function categoryIcon(nombre: string): string {
  return CATEGORY_ICONS[nombre] ?? CATEGORY_FALLBACK
}

const SUPERMARKET_COLORS: Record<string, string> = {
  'Super Selectos': '#0f66e8',
  'Walmart': '#0071dc',
  'PriceSmart': '#b3120b',
  'Maxi Despensa': '#14a86b',
}

const SUPERMARKET_FALLBACK = '#52657a'

export function supermarketColor(nombre: string): string {
  return SUPERMARKET_COLORS[nombre] ?? SUPERMARKET_FALLBACK
}
