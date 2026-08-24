// Contratos crudos (raw) de la API Laravel, tal cual los devuelve el backend.
// Los tipos de dominio usados por la UI viven en types/domain.ts con sus adaptadores.

export type ApiCategoria = {
  id: number
  nombre: string
}

export type ApiSupermercado = {
  id: number
  nombre: string
  logo: string | null
  sitio_web: string | null
  activo: boolean
}

export type ApiSucursal = {
  id: number
  supermercado_id: number
  nombre: string
  direccion: string | null
  latitud: number | null
  longitud: number | null
  telefono: string | null
  horario: string | null
  supermercado: ApiSupermercado
}

export type ApiPrecioActual = {
  id: number
  producto_id: number
  sucursal_id: number
  precio_normal: number
  precio_final: number
  tiene_promocion: boolean
  tipo_promocion: string | null
  fecha_actualizacion: string | null
  origen_dato: string | null
  sucursal: ApiSucursal
}

export type ApiProductoLite = {
  id: number
  categoria_id: number
  marca: string | null
  nombre: string
  presentacion: string | null
  unidad_medida: string | null
  contenido: number | null
  activo: boolean
  categoria: ApiCategoria
}

export type ApiProductoFull = ApiProductoLite & {
  precios_actuales: ApiPrecioActual[]
}

export type ApiPromocion = ApiPrecioActual & {
  producto: ApiProductoLite
}

export type ApiPaginated<T> = {
  current_page: number
  data: T[]
  per_page: number
  total: number
  last_page: number
}

export type ApiUser = {
  id: number
  name: string
  email: string
  rol: string
  estado: string
}

export type ApiAuthResponse = {
  user: ApiUser
  token: string
}

export type ApiLista = {
  id: number
  usuario_id: number
  nombre: string
  presupuesto: number | null
  estado: string
  fecha: string
  created_at: string
  updated_at: string
  detalles_count?: number
}

export type ApiHistorialPrecio = {
  id: number
  producto_id: number
  sucursal_id: number
  precio_normal: number
  precio_final: number
  tipo_promocion: string | null
  fecha: string
  origen: string | null
  sucursal: ApiSucursal
}

export type ApiDetalle = {
  id: number
  lista_id: number
  producto_id: number
  cantidad: number
  esencial: boolean
  permite_sustituto: boolean | null
  producto: ApiProductoLite
}

export type ApiListaShow = ApiLista & {
  detalles: ApiDetalle[]
}

export type ApiCompararResultado = {
  sucursal_id: number
  sucursal: string
  supermercado: string
  latitud: number
  longitud: number
  costo_total: number
  beneficio_promociones: number
  productos_con_promocion: number
  productos_esenciales_disponibles: number
  productos_esenciales_totales: number
  productos_opcionales_disponibles: number
  productos_opcionales_totales: number
  todos_los_esenciales_disponibles: boolean
  dentro_del_presupuesto: boolean | null
}

export type ApiComparar = {
  lista: string
  presupuesto: number | null
  resultados: ApiCompararResultado[]
}

export type ApiOptimizarResultado = ApiCompararResultado & {
  distancia_km: number | null
  penalizacion_distancia: number
  tiempo_minutos: number | null
  costo_tiempo: number | null
  score: number
  nivel_optimizacion: number
  recommendation: ApiExpertRecommendation | null
  expert_system_available: boolean
}

export type ApiExpertRecommendation = {
  request_id: string
  nivel_recomendacion: 'EXCELENTE' | 'BUENA' | 'NO_RECOMENDABLE'
  accion_sugerida: string
  explicacion: string
  indice_conveniencia: number | null
  clasificacion_conveniencia: string | null
  componentes_conveniencia: Record<string, number> | null
  pesos_conveniencia: Record<string, number> | null
  chatbot_available: boolean | null
  reglas_activadas: string[]
  prioridad_aplicada: string
  hechos_derivados: Record<string, boolean | number>
  version_reglas: string
  version_contrato: string | null
  winning_rule: string | null
  losing_rules: string[]
  trace: Array<Record<string, unknown>>
}

export type ApiOptimizar = {
  lista: string
  presupuesto: number | null
  mejor_opcion: ApiOptimizarResultado | null
  resultados: ApiOptimizarResultado[]
  resultado_optimizacion_id: number | null
}
