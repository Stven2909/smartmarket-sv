import { CupSoda, Droplets, Milk, ShoppingBasket, SprayCan, Wheat } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

// Íconos SVG de línea por categoría (consistente con el resto de la UI, que es
// tipográfica y con íconos de lucide). Si una categoría no tiene mapeo explícito
// se usa un fallback genérico: nunca un hueco visual.
const CATEGORY_ICONS: Record<string, LucideIcon> = {
  'Lácteos': Milk,
  'Bebidas': CupSoda,
  'Limpieza': SprayCan,
  'Granos básicos': Wheat,
  'Higiene personal': Droplets,
}

const FALLBACK: LucideIcon = ShoppingBasket

type Props = {
  name: string
  size?: number
  className?: string
}

export function CategoryIcon({ name, size = 20, className }: Props) {
  const Icon = CATEGORY_ICONS[name] ?? FALLBACK
  return <Icon size={size} className={className} aria-hidden="true" />
}
