import type { CompararResultado } from '../types/domain'

// Reglas de presentación para listas incompletas (Q/A). El Score y el orden del
// backend NO cambian: aquí solo se decide qué alternativa puede llamarse
// "precio más bajo" o "mejor Score" y cómo se etiqueta un subtotal parcial.
//
// Política: si existe al menos una alternativa con la lista completa, las
// etiquetas de ganador se calculan entre esas. Si ninguna está completa, se
// muestra la mejor parcial con una advertencia explícita.

export function alternativasComparables<T extends CompararResultado>(resultados: T[]): T[] {
  const completas = resultados.filter((resultado) => resultado.listaCompleta)
  return completas.length > 0 ? completas : resultados
}

export function mejorPorCosto<T extends CompararResultado>(resultados: T[]): T | undefined {
  return [...alternativasComparables(resultados)].sort((a, b) => a.costoTotal - b.costoTotal)[0]
}

export function mejorPorScore<T extends CompararResultado & { score: number }>(resultados: T[]): T | undefined {
  return [...alternativasComparables(resultados)].sort((a, b) => a.score - b.score)[0]
}

export function faltantesTexto(resultado: CompararResultado): string {
  if (resultado.listaCompleta) return 'Lista completa'

  const total = resultado.productosFaltantes
  const esenciales = resultado.esencialesFaltantes
  const productos = `${total} producto${total === 1 ? '' : 's'}`

  return esenciales > 0
    ? `Faltan ${productos} (${esenciales} esencial${esenciales === 1 ? '' : 'es'})`
    : `Faltan ${productos}`
}

export function etiquetaSubtotal(resultado: CompararResultado): string {
  return resultado.listaCompleta
    ? 'Precio más bajo'
    : `Subtotal parcial · faltan ${resultado.productosFaltantes}`
}
