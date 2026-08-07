// Cliente HTTP base: resuelve la URL desde VITE_API_URL y adjunta el token Bearer
// de Sanctum cuando existe.

const BASE_URL = (import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000/api').replace(/\/$/, '')

export class ApiError extends Error {
  status: number
  validation?: Record<string, string[]>

  constructor(status: number, message: string, validation?: Record<string, string[]>) {
    super(message)
    this.status = status
    this.validation = validation
  }
}

export function getToken(): string | null {
  return localStorage.getItem('smartmarket_token')
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem('smartmarket_token', token)
  else localStorage.removeItem('smartmarket_token')
}

// Un fetch abortado (componente que se desmonta, o el doble montaje de
// React StrictMode en dev) NO es un error real: se ignora y no se muestra.
export function isAbortError(e: unknown): boolean {
  return (e instanceof DOMException && e.name === 'AbortError')
    || (e instanceof Error && e.name === 'AbortError')
}

// Traduce un error desconocido a un mensaje amigable en español.
// Devuelve null cuando el error no debe mostrarse (fetch abortado).
export function friendlyError(e: unknown, fallback: string): string | null {
  if (isAbortError(e)) return null
  if (e instanceof ApiError) return e.message
  if (e instanceof TypeError) return 'No pudimos conectar con el servidor. Verifica tu conexión e inténtalo de nuevo.'
  return fallback
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    Accept: 'application/json',
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  }
  if (token) headers.Authorization = `Bearer ${token}`

  const response = await fetch(`${BASE_URL}${path}`, { ...options, headers })

  if (!response.ok) {
    let message = `Error ${response.status}`
    let validation: Record<string, string[]> | undefined
    try {
      const body = await response.json()
      if (body?.message) message = body.message
      if (body?.errors) validation = body.errors
    } catch {
      // sin cuerpo JSON
    }
    throw new ApiError(response.status, message, validation)
  }

  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  get<T>(path: string, signal?: AbortSignal): Promise<T> {
    return request<T>(path, { signal })
  },
  post<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, { method: 'POST', body: JSON.stringify(body ?? {}) })
  },
  patch<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, { method: 'PATCH', body: JSON.stringify(body ?? {}) })
  },
  del<T>(path: string): Promise<T> {
    return request<T>(path, { method: 'DELETE' })
  },
}
