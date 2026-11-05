// Cliente HTTP base: resuelve la URL desde VITE_API_URL y adjunta el token Bearer
// de Sanctum cuando existe.

const BASE_URL = (import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000/api').replace(/\/$/, '')

// Tope por defecto para peticiones normales. Las operaciones que dependen del
// Sistema Experto usan un tope mayor porque Render puede tardar en despertar.
const DEFAULT_TIMEOUT_MS = 15000
export const EXPERT_REQUEST_TIMEOUT_MS = 45000

export class ApiError extends Error {
  status: number
  validation?: Record<string, string[]>

  constructor(status: number, message: string, validation?: Record<string, string[]>) {
    super(message)
    this.status = status
    this.validation = validation
  }
}

export type RequestOptions = {
  signal?: AbortSignal
  timeoutMs?: number
}

function isAbortSignal(value: unknown): value is AbortSignal {
  return typeof value === 'object'
    && value !== null
    && 'aborted' in value
    && typeof (value as AbortSignal).addEventListener === 'function'
}

function toRequestOptions(input?: AbortSignal | RequestOptions): RequestOptions {
  if (!input) return {}
  return isAbortSignal(input) ? { signal: input } : input
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

async function request<T>(path: string, options: RequestInit & { timeoutMs?: number } = {}): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, signal, ...init } = options
  const token = getToken()
  const headers: Record<string, string> = {
    Accept: 'application/json',
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string> | undefined),
  }
  if (token) headers.Authorization = `Bearer ${token}`

  // El timeout se implementa con un AbortController propio para no pisar la
  // señal que envíe el componente que inició la petición.
  const controller = new AbortController()
  let timedOut = false
  const timer = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, timeoutMs)
  const abortFromCaller = () => controller.abort()

  if (signal) {
    if (signal.aborted) controller.abort()
    else signal.addEventListener('abort', abortFromCaller)
  }

  try {
    const response = await fetch(`${BASE_URL}${path}`, { ...init, headers, signal: controller.signal })

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
  } catch (e) {
    if (timedOut) {
      throw new ApiError(
        408,
        'La operación tardó demasiado. Verifica tu conexión e inténtalo de nuevo.',
      )
    }
    throw e
  } finally {
    clearTimeout(timer)
    if (signal) signal.removeEventListener('abort', abortFromCaller)
  }
}

export const api = {
  get<T>(path: string, signalOrOptions?: AbortSignal | RequestOptions): Promise<T> {
    return request<T>(path, toRequestOptions(signalOrOptions))
  },
  post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return request<T>(path, { ...options, method: 'POST', body: JSON.stringify(body ?? {}) })
  },
  patch<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return request<T>(path, { ...options, method: 'PATCH', body: JSON.stringify(body ?? {}) })
  },
  del<T>(path: string, options?: RequestOptions): Promise<T> {
    return request<T>(path, { ...options, method: 'DELETE' })
  },
}
