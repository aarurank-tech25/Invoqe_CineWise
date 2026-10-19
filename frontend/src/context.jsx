import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { apiGetWatchlistIds, apiAddWatchlist, apiRemoveWatchlist, apiGetWatchedIds, apiAddWatched, apiRemoveWatched } from './api';

// ── Auth context ──────────────────────────────────────────────────────────
const AuthCtx = createContext(null);
export const useAuth = () => useContext(AuthCtx);

// ── Watchlist context ─────────────────────────────────────────────────────
const WatchlistCtx = createContext(null);
export const useWatchlist = () => useContext(WatchlistCtx);

// ── Watched context ───────────────────────────────────────────────────────
const WatchedCtx = createContext(null);
export const useWatched = () => useContext(WatchedCtx);

// ── Toast context ─────────────────────────────────────────────────────────
const ToastCtx = createContext(null);
export const useToast = () => useContext(ToastCtx);

// ── Combined provider ─────────────────────────────────────────────────────
export function AppProvider({ children }) {
  // Auth
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('cinewise_user') || 'null'); } catch { return null; }
  });

  const login = useCallback((userData) => {
    setUser(userData);
    localStorage.setItem('cinewise_user', JSON.stringify(userData));
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    localStorage.removeItem('cinewise_user');
    setWatchlistIds(new Set());
    setWatchedIds(new Set());
  }, []);

  // Watchlist IDs (set of movie ids)
  const [watchlistIds, setWatchlistIds] = useState(new Set());
  // Watched IDs (set of movie ids)
  const [watchedIds, setWatchedIds] = useState(new Set());

  useEffect(() => {
    if (user?.id) {
      apiGetWatchlistIds(user.id)
        .then(data => setWatchlistIds(new Set(data.movie_ids)))
        .catch(() => {});
      apiGetWatchedIds(user.id)
        .then(data => setWatchedIds(new Set(data.movie_ids)))
        .catch(() => {});
    }
  }, [user?.id]);

  const addToWatchlist = useCallback(async (movieId) => {
    if (!user) return false;
    try {
      await apiAddWatchlist(user.id, movieId);
      setWatchlistIds(prev => new Set([...prev, movieId]));
      return true;
    } catch { return false; }
  }, [user]);

  const removeFromWatchlist = useCallback(async (movieId) => {
    if (!user) return false;
    try {
      await apiRemoveWatchlist(user.id, movieId);
      setWatchlistIds(prev => { const s = new Set(prev); s.delete(movieId); return s; });
      return true;
    } catch { return false; }
  }, [user]);

  const inWatchlist = useCallback((movieId) => watchlistIds.has(movieId), [watchlistIds]);

  const addToWatched = useCallback(async (movieId, rating = null) => {
    if (!user) return false;
    try {
      await apiAddWatched(user.id, movieId, rating);
      setWatchedIds(prev => new Set([...prev, movieId]));
      return true;
    } catch { return false; }
  }, [user]);

  const removeFromWatched = useCallback(async (movieId) => {
    if (!user) return false;
    try {
      await apiRemoveWatched(user.id, movieId);
      setWatchedIds(prev => { const s = new Set(prev); s.delete(movieId); return s; });
      return true;
    } catch { return false; }
  }, [user]);

  const inWatched = useCallback((movieId) => watchedIds.has(movieId), [watchedIds]);

  // Toasts
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback((message, type = 'info') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 3500);
  }, []);

  return (
    <AuthCtx.Provider value={{ user, login, logout, isLoggedIn: !!user }}>
      <WatchlistCtx.Provider value={{ watchlistIds, addToWatchlist, removeFromWatchlist, inWatchlist, setWatchlistIds }}>
        <WatchedCtx.Provider value={{ watchedIds, addToWatched, removeFromWatched, inWatched, setWatchedIds }}>
          <ToastCtx.Provider value={{ toasts, addToast }}>
            {children}
            <ToastContainer toasts={toasts} />
          </ToastCtx.Provider>
        </WatchedCtx.Provider>
      </WatchlistCtx.Provider>
    </AuthCtx.Provider>
  );
}

function ToastContainer({ toasts }) {
  if (!toasts.length) return null;
  return (
    <div className="toast-container" role="status" aria-live="polite">
      {toasts.map(t => (
        <div key={t.id} className={`toast toast-${t.type}`}>{t.message}</div>
      ))}
    </div>
  );
}
