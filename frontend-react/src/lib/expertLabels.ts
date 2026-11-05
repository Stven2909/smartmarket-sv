export const EXPERT_RULE_LABELS: Record<string, string> = {
  R01: 'Presupuesto muy excedido',
  R02: 'Faltan productos esenciales',
  R03: 'Distancia lejana con poco ahorro',
  R04: 'Tiempo alto con poco ahorro',
  R05: 'Compra fragmentada',
  R06: 'Alternativa conveniente',
  R07: 'Promociones relevantes',
  R08: 'Ahorro alto con dos paradas',
  R09: 'Sin productos disponibles',
  R10: 'Cobertura muy baja',
  R11: 'Conveniencia con cobertura completa',
  R12: 'Sin esenciales definidos y cobertura parcial',
  R13: 'Esenciales cubiertos y faltan productos',
  R14: 'Alta conveniencia con ahorro',
  R15: 'Conveniencia ponderada con ahorro bajo',
  R16: 'Cobertura alta con faltantes opcionales',
}

export const EXPERT_PRIORITY_LABELS: Record<string, string> = {
  PRESUPUESTO: 'Presupuesto',
  DISPONIBILIDAD: 'Disponibilidad de productos',
  DISTANCIA_AHORRO: 'Distancia y ahorro',
  TIEMPO_AHORRO: 'Tiempo y ahorro',
  FRAGMENTACION: 'Fragmentación de la compra',
  CONVENIENCIA: 'Conveniencia',
  CONVENIENCIA_PONDERADA: 'Conveniencia ponderada',
  PROMOCIONES: 'Promociones',
  AHORRO_FRAGMENTACION: 'Ahorro y fragmentación',
  SIN_REGLA: 'Sin regla activada',
}

export const EXPERT_FACT_LABELS: Record<string, string> = {
  dentro_presupuesto: 'Dentro del presupuesto',
  presupuesto_ligeramente_excedido: 'Presupuesto excedido ligeramente',
  presupuesto_muy_excedido: 'Presupuesto muy excedido',
  todos_productos_disponibles: 'Todos los productos disponibles',
  faltan_productos: 'Faltan productos',
  ningun_producto_disponible: 'Ningún producto disponible',
  algun_producto_disponible: 'Algún producto disponible',
  cobertura_muy_baja: 'Cobertura menor al 50%',
  sin_esenciales_definidos: 'Sin esenciales definidos',
  cobertura_parcial_relevante: 'Cobertura parcial (menos del 80%)',
  todos_esenciales_disponibles: 'Todos los esenciales disponibles',
  faltan_esenciales: 'Faltan productos esenciales',
  ahorro_bajo: 'Ahorro bajo',
  ahorro_alto: 'Ahorro alto',
  distancia_media: 'Distancia media',
  distancia_lejana: 'Distancia lejana',
  distancia_cercana: 'Distancia cercana',
  distancia_razonable: 'Distancia razonable',
  tiempo_razonable: 'Tiempo de traslado razonable',
  tiempo_medio: 'Tiempo de traslado medio',
  tiempo_alto: 'Tiempo de traslado alto',
  tiempo_bajo: 'Tiempo de traslado bajo',
  una_parada: 'Una sola parada',
  dos_paradas: 'Dos paradas',
  compra_fragmentada: 'Compra fragmentada',
  promociones_relevantes: 'Promociones relevantes',
  conveniencia_alta: 'Conveniencia alta',
  conveniencia_no_baja: 'Conveniencia no baja',
  conveniencia_solida: 'Conveniencia sólida',
  diferencia_presupuesto: 'Diferencia respecto al presupuesto',
  porcentaje_exceso_presupuesto: 'Exceso del presupuesto',
  porcentaje_productos_disponibles: 'Productos disponibles',
  porcentaje_esenciales_disponibles: 'Esenciales disponibles',
  ahorro_medio: 'Ahorro medio',
  promociones_aplicables: 'Promociones aplicables',
  distancia_km: 'Distancia',
  tiempo_estimado_min: 'Tiempo estimado',
  numero_supermercados: 'Supermercados necesarios',
}

export const EXPERT_OMISSION_LABELS: Record<string, string> = {
  presupuesto_null: 'La lista no tiene un presupuesto definido.',
  distancia_null: 'Esta sucursal no tiene coordenadas para calcular la distancia.',
  tiempo_null: 'No se pudo calcular el tiempo de traslado.',
  costo_total_null: 'No hay un costo total válido para esta alternativa.',
  productos_totales_cero: 'La lista no contiene productos evaluables.',
  productos_disponibles_negativo: 'La disponibilidad recibida no es válida.',
  productos_disponibles_mayor_que_totales: 'La disponibilidad supera el total de productos de la lista.',
  esenciales_disponibles_negativo: 'La disponibilidad de esenciales no es válida.',
  esenciales_disponibles_mayor_que_totales: 'La disponibilidad de esenciales supera el total de la lista.',
  esenciales_totales_negativo: 'El total de productos esenciales no es válido.',
  costo_referencia_indeterminado: 'No se pudo determinar un costo de referencia.',
  distancia_minima_indeterminada: 'No se pudo determinar la distancia mínima de referencia.',
  respuesta_invalida: 'El experto respondió con un formato inesperado; se descartó esa evaluación.',
  presupuesto_agotado: 'Se agotó el tiempo disponible para consultar al experto.',
  sin_respuesta: 'El experto no respondió a tiempo; el ranking local sigue siendo válido.',
}

export const EXPERT_LEVEL_LABELS: Record<string, string> = {
  EXCELENTE: 'Excelente',
  BUENA: 'Buena',
  NO_RECOMENDABLE: 'No recomendable',
}

export function ruleLabel(code: string): string {
  return EXPERT_RULE_LABELS[code] ?? code
}

export function priorityLabel(code: string): string {
  return EXPERT_PRIORITY_LABELS[code] ?? code
}

export function factLabel(key: string): string {
  return EXPERT_FACT_LABELS[key] ?? key
}

export function omissionReasonLabel(code: string | null): string | null {
  return code ? (EXPERT_OMISSION_LABELS[code] ?? code) : null
}
