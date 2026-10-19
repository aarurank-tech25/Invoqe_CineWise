// API client — all calls to the FastAPI backend
const BACKEND_URL = (import.meta.env.VITE_BACKEND_URL || '').replace(/\/+$/, '');
const BASE = BACKEND_URL ? `${BACKEND_URL}/api` : '/api';

function getApiKey() {
  return localStorage.getItem('cinewise_api_key') || '';
}

async function fetchJSON(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function apiHealth() {
  return fetchJSON(`${BASE}/health?api_key=${getApiKey()}`);
}

export async function apiGetTitles(language = 'all') {
  return fetchJSON(`${BASE}/titles?language=${language}&api_key=${getApiKey()}`);
}

export async function apiSearch({
  q = '',
  language = 'all',
  genre = 'all',
  actor = '',
  min_rating = null,
  year_from = null,
  year_to = null,
  sort_by = 'popularity',
  limit = 24,
  offset = 0,
} = {}) {
  const params = new URLSearchParams({
    q,
    language,
    genre,
    actor,
    sort_by,
    limit,
    offset,
    api_key: getApiKey(),
  });
  if (min_rating != null && min_rating > 0) params.set('min_rating', min_rating);
  if (year_from != null && year_from > 0) params.set('year_from', year_from);
  if (year_to != null && year_to > 0) params.set('year_to', year_to);
  return fetchJSON(`${BASE}/search?${params}`);
}

export async function apiGetMovie(movieId, region = 'IN') {
  return fetchJSON(`${BASE}/movie/${movieId}?region=${region}&api_key=${getApiKey()}`);
}

export async function apiRecommend({ movie_id, top_k = 10, language_filter = null, genre_filter = null, sort_by = 'ai_match' }, region = 'IN') {
  return fetchJSON(`${BASE}/recommend?region=${region}&api_key=${getApiKey()}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ movie_id, top_k, language_filter, genre_filter, sort_by }),
  });
}

export async function apiExplore({
  language = 'all',
  genre = 'all',
  actor = '',
  min_rating = null,
  year_from = null,
  year_to = null,
  sort_by = 'popularity',
  limit = 24,
  offset = 0,
} = {}) {
  const params = new URLSearchParams({
    language,
    genre,
    actor,
    sort_by,
    limit,
    offset,
    api_key: getApiKey(),
  });
  if (min_rating != null && min_rating > 0) params.set('min_rating', min_rating);
  if (year_from != null && year_from > 0) params.set('year_from', year_from);
  if (year_to != null && year_to > 0) params.set('year_to', year_to);
  return fetchJSON(`${BASE}/explore?${params}`);
}

export async function apiGetPersonMovies(personId, { limit = 24, offset = 0, region = 'IN' } = {}) {
  return fetchJSON(`${BASE}/person/${personId}/movies?limit=${limit}&offset=${offset}&region=${region}&api_key=${getApiKey()}`);
}

export async function apiGetGenres() {
  return fetchJSON(`${BASE}/genres`);
}

export async function apiRegister({ name, email, password }) {
  return fetchJSON(`${BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, password }),
  });
}

export async function apiLogin({ email, password }) {
  return fetchJSON(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
}

export async function apiForgotPassword({ email }) {
  return fetchJSON(`${BASE}/auth/forgot-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
}

export async function apiValidateResetToken(token) {
  return fetchJSON(`${BASE}/auth/reset-password/validate?token=${encodeURIComponent(token)}`);
}

export async function apiResetPassword({ token, password, confirm_password }) {
  return fetchJSON(`${BASE}/auth/reset-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, password, confirm_password }),
  });
}

export async function apiGetWatchlist(userId, region = 'IN') {
  return fetchJSON(`${BASE}/watchlist/${userId}?region=${region}&api_key=${getApiKey()}`);
}

export async function apiGetWatchlistIds(userId) {
  return fetchJSON(`${BASE}/watchlist/${userId}/ids`);
}

export async function apiAddWatchlist(userId, movieId) {
  return fetchJSON(`${BASE}/watchlist/add`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, movie_id: movieId }),
  });
}

export async function apiRemoveWatchlist(userId, movieId) {
  return fetchJSON(`${BASE}/watchlist/remove`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, movie_id: movieId }),
  });
}

// Watched History
export async function apiGetWatched(userId, region = 'IN') {
  return fetchJSON(`${BASE}/watched/${userId}?region=${region}&api_key=${getApiKey()}`);
}

export async function apiGetWatchedIds(userId) {
  return fetchJSON(`${BASE}/watched/${userId}/ids`);
}

export async function apiAddWatched(userId, movieId, rating = null) {
  return fetchJSON(`${BASE}/watched/add`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, movie_id: movieId, rating }),
  });
}

export async function apiRemoveWatched(userId, movieId) {
  return fetchJSON(`${BASE}/watched/remove`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, movie_id: movieId }),
  });
}

// User Preferences
export async function apiGetPreferences(userId) {
  return fetchJSON(`${BASE}/preferences/${userId}`);
}

export async function apiSavePreferences(userId, languages, genres) {
  return fetchJSON(`${BASE}/preferences/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, languages, genres }),
  });
}

// Person (actor/director) profiles
export async function apiGetPerson(personId) {
  return fetchJSON(`${BASE}/person/${personId}?api_key=${getApiKey()}`);
}

export async function apiSearchPerson(q) {
  return fetchJSON(`${BASE}/person/search?q=${encodeURIComponent(q)}&api_key=${getApiKey()}`);
}

// Personalized recommendations
export async function apiGetPersonalized(userId, topK = 12, region = 'IN') {
  return fetchJSON(`${BASE}/personalized/${userId}?top_k=${topK}&region=${region}&api_key=${getApiKey()}`);
}

// Catalog Discovery & Admin Refresh
export async function apiAdminRefreshCatalog({ languages = null, pages_per_language = 2, admin_key = null } = {}) {
  return fetchJSON(`${BASE}/admin/catalog/refresh?api_key=${getApiKey()}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ languages, pages_per_language, admin_key }),
  });
}

export async function apiGetCatalogStats() {
  return fetchJSON(`${BASE}/catalog/stats`);
}

