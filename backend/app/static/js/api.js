// Cliente HTTP único. Cookie de sesión HttpOnly + cabecera CSRF (double-submit). Sin localStorage.
export class ApiError extends Error {
  constructor(status, code, message, errors = []) {
    super(message); this.status = status; this.code = code; this.errors = errors;
  }
}

function cookie(name) {
  const m = document.cookie.split('; ').find((c) => c.startsWith(name + '='));
  return m ? decodeURIComponent(m.split('=')[1]) : '';
}

export function qs(params = {}) {
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== null && v !== undefined && v !== '') u.set(k, v);
  const s = u.toString();
  return s ? '?' + s : '';
}

export async function api(path, { method = 'GET', body, params } = {}) {
  const headers = { Accept: 'application/json' };
  if (method !== 'GET') headers['X-CSRF-Token'] = cookie('rh_csrf');
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  let res;
  try {
    res = await fetch('/api/v1' + path + qs(params), {
      method, headers, credentials: 'same-origin', body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, 'network', 'No se pudo conectar con el servidor. Revisa tu conexión.');
  }
  if (res.status === 204) return null;
  let data = null;
  try { data = await res.json(); } catch { /* cuerpo vacío o no JSON */ }
  if (res.ok) return data;
  const publicPage = location.pathname.startsWith('/login') || location.pathname.startsWith('/registro');
  if (res.status === 401 && !publicPage && path !== '/auth/login' && path !== '/auth/register') {
    location.href = '/login';
  }
  const msg = (data && typeof data.detail === 'string' && data.detail) || `Error ${res.status}`;
  throw new ApiError(res.status, data?.code ?? 'error', msg, data?.errors ?? []);
}

export const get = (p, params) => api(p, { params });
export const post = (p, body) => api(p, { method: 'POST', body: body ?? {} });
export const patch = (p, body) => api(p, { method: 'PATCH', body });
export const del = (p) => api(p, { method: 'DELETE' });
