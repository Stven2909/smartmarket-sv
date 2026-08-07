// Formato de moneda central (USD, es-SV). Todos los precios de la UI pasan por
// acá para garantizar el símbolo $ en cada pantalla.
//
// El backend serializa las columnas NUMERIC/DECIMAL como string ("1.85") y
// toLocaleString sobre un string NO aplica formato de moneda — por eso los
// precios aparecían sin $. Este helper coacciona a Number y formatea siempre.
// Si el valor no es un número real (null/undefined/vacío) devuelve "—":
// un "no hay dato" honesto, nunca un $0.00 inventado ni un NaN que explote.
export function formatMoney(value: number | string | null | undefined): string {
  const n = typeof value === 'number' ? value : value == null || value === '' ? NaN : Number(value)
  return Number.isFinite(n)
    ? n.toLocaleString('es-SV', { style: 'currency', currency: 'USD' })
    : '—'
}
