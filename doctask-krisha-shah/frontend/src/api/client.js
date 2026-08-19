const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

// The single-user identity used for review decisions until auth is added.
// Matches the seeded admin user in schema.sql.
export const CURRENT_USER_ID = '11111111-1111-1111-1111-111111111111'

class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === 'string' ? detail : JSON.stringify(detail))
    this.status = status
    this.detail = detail
  }
}

async function handleResponse(response) {
  if (response.status === 204) return null
  const isJson = response.headers.get('content-type')?.includes('application/json')
  const body = isJson ? await response.json() : await response.text()
  if (!response.ok) {
    const detail = isJson ? body?.detail ?? body : body
    throw new ApiError(response.status, detail)
  }
  return body
}

export async function get(path) {
  const response = await fetch(`${BASE_URL}${path}`)
  return handleResponse(response)
}

export async function post(path, body) {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  return handleResponse(response)
}

export async function postForm(path, formData) {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    body: formData,
  })
  return handleResponse(response)
}

export { ApiError }
