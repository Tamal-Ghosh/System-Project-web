const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

// Used when backend endpoints exist. Current pages deliberately use mock data.
// Add the agreed CSRF token for cookie-authenticated mutation requests.
export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('Accept', 'application/json')
  if (options.body && typeof options.body === 'string' && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const response = await fetch(`${baseUrl}/${path.replace(/^\//, '')}`, {
    ...options, headers, credentials: 'include',
  })
  if (!response.ok) throw new ApiError(response.status, `Request failed (${response.status}). Please retry.`)
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}
