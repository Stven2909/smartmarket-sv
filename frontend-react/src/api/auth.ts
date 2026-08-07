import { api, setToken } from './client'
import type { ApiAuthResponse, ApiUser } from '../types/api'

export async function login(email: string, password: string): Promise<ApiAuthResponse> {
  const data = await api.post<ApiAuthResponse>('/login', { email, password })
  setToken(data.token)
  return data
}

export async function register(name: string, email: string, password: string, passwordConfirmation: string): Promise<ApiAuthResponse> {
  const data = await api.post<ApiAuthResponse>('/register', {
    name,
    email,
    password,
    password_confirmation: passwordConfirmation,
  })
  setToken(data.token)
  return data
}

export async function logout(): Promise<void> {
  try {
    await api.post('/logout')
  } finally {
    setToken(null)
  }
}

export async function me(): Promise<ApiUser> {
  return api.get<ApiUser>('/me')
}
