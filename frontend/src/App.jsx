import { useState, useEffect, useCallback } from 'react';
import { AppProvider, useAuth, useWatchlist } from './context';
import { HomePage, ExplorePage, WatchlistPage, ProfilePage } from './pages';
import { LoginPage, RegisterPage, ForgotPasswordPage, ResetPasswordPage } from './authPages';
import './index.css';

const PAGES = ['recommendations', 'explore', 'watchlist', 'profile', 'login', 'register', 'forgot-password', 'reset-password'];

const PAGE_TITLES = {
  recommendations: 'AI Movie Recommendations',
  explore:         'Explore Film Catalog',
  watchlist:       'My Personal Watchlist',
  profile:         'Your CineWise Profile',
};

const PAGE_SUBS = {
  recommendations: 'Content-Based Semantic Discovery · 10,029 Multi-Language Titles',
  explore:         'Browse Global & Indian Cinema by Genre, Language & Popularity',
};

function CineWise() {
  // Read initial page and token from URL query params
  const [page, setPage] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    const p = params.get('page');
    if (p && PAGES.includes(p)) return p;
    return 'recommendations';
  });

  const [resetToken, setResetToken] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('token') || '';
  });

  const [region, setRegion] = useState('IN');

  const { user, logout, isLoggedIn } = useAuth();
  const { watchlistIds } = useWatchlist();

  // Sync navigation with browser URL history
  const navigateTo = useCallback((newPage, token = null) => {
    setPage(newPage);
    if (token !== null) setResetToken(token);

    const url = new URL(window.location);
    if (newPage === 'recommendations') {
      url.searchParams.delete('page');
      url.searchParams.delete('token');
    } else {
      url.searchParams.set('page', newPage);
      if (token) url.searchParams.set('token', token);
      else if (newPage !== 'reset-password') url.searchParams.delete('token');
    }
    window.history.pushState({}, '', url);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  // Handle browser back/forward buttons
  useEffect(() => {
    const handlePopState = () => {
      const params = new URLSearchParams(window.location.search);
      const p = params.get('page') || 'recommendations';
      const tok = params.get('token') || '';
      setPage(p);
      setResetToken(tok);
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // When Explore selects a movie → switch to Recommendations page
  const handleExploreMovieSelect = (movieId, titleLabel) => {
    sessionStorage.setItem('cw_preseed_title', titleLabel);
    sessionStorage.setItem('cw_preseed_id', String(movieId));
    navigateTo('recommendations');
  };

  const isAuthPage = ['login', 'register', 'forgot-password', 'reset-password'].includes(page);

  return (
    <div className="site-wrapper" style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      {/* ── Main Navigation Header ── */}
      <header className="nav" role="banner">
        <div className="nav-inner">
          {/* Compact CineWise Logo and Brand Name */}
          <button
            className="nav-logo"
            onClick={() => navigateTo('recommendations')}
            aria-label="CineWise home"
            title="CineWise — AI Movie Discovery Platform"
          >
            <img
              src="/cinewise-logo.png"
              alt="CineWise Logo"
              className="nav-logo-image"
            />
            <div className="nav-logo-title-group">
              <span className="nav-logo-text">Cine<span>Wise</span></span>
              <span className="nav-logo-badge-text">AI DISCOVERY</span>
            </div>
          </button>

          {/* Primary Navigation Tabs */}
          <nav className="nav-links" aria-label="Main navigation">
            <button
              id="nav-recommendations"
              className={`nav-tab${page === 'recommendations' ? ' active' : ''}`}
              onClick={() => navigateTo('recommendations')}
            >
              Recommendations
            </button>
            <button
              id="nav-explore"
              className={`nav-tab${page === 'explore' ? ' active' : ''}`}
              onClick={() => navigateTo('explore')}
            >
              Explore
            </button>
            <button
              id="nav-watchlist"
              className={`nav-tab${page === 'watchlist' ? ' active' : ''}`}
              onClick={() => isLoggedIn ? navigateTo('watchlist') : navigateTo('login')}
            >
              Watchlist
              {watchlistIds.size > 0 && <span className="nav-watchlist-badge">{watchlistIds.size}</span>}
            </button>
          </nav>

          {/* Right-Side Controls */}
          <div className="nav-right">
            {/* Region selector for streaming availability */}
            <select
              id="region-select"
              className="nav-region-select"
              value={region}
              onChange={e => setRegion(e.target.value)}
              aria-label="Streaming region"
              title="Streaming Availability Region"
            >
              <option value="IN">🌏 India</option>
              <option value="US">🇺🇸 US</option>
              <option value="GB">🇬🇧 UK</option>
            </select>

            {/* User Profile or Sign In Button */}
            {isLoggedIn ? (
              <button
                id="nav-user"
                className="nav-user-btn"
                onClick={() => navigateTo('profile')}
                title={`Signed in as ${user.name}`}
              >
                <span className="user-avatar-circle">{user.name.charAt(0).toUpperCase()}</span>
                <span className="user-name-short">{user.name.split(' ')[0]}</span>
              </button>
            ) : (
              <button
                id="nav-signin"
                className="nav-signin-btn"
                onClick={() => navigateTo('login')}
              >
                Sign In
              </button>
            )}
          </div>
        </div>
      </header>

      {/* ── Page Banner (Visible on Non-Auth Views) ── */}
      {!isAuthPage && (
        <section className="page-banner" aria-label="Page title">
          <div className="page-banner-inner">
            <div className="banner-left">
              <h1 className="banner-title" id="page-heading">{PAGE_TITLES[page]}</h1>
              {PAGE_SUBS[page] && <div className="banner-sub">{PAGE_SUBS[page]}</div>}
            </div>

            {page === 'watchlist' && (
              <div className="banner-count-badge">
                {watchlistIds.size} saved title{watchlistIds.size !== 1 ? 's' : ''}
              </div>
            )}
            {page === 'profile' && user && (
              <div className="banner-count-badge">
                {user.email}
              </div>
            )}
          </div>
        </section>
      )}

      {/* ── Main Application Content ── */}
      <main id="main" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Core Cinema Discovery Pages */}
        {page === 'recommendations' && <HomePage region={region} />}
        {page === 'explore' && <ExplorePage region={region} onMovieSelect={handleExploreMovieSelect} />}
        {page === 'watchlist' && <WatchlistPage region={region} onMovieSelect={handleExploreMovieSelect} />}
        {page === 'profile' && (
          <ProfilePage onLogout={() => { logout(); navigateTo('recommendations'); }} />
        )}

        {/* Dedicated Authentication Screens */}
        {page === 'login' && (
          <LoginPage
            onNavigate={navigateTo}
            onSuccess={() => navigateTo('recommendations')}
          />
        )}
        {page === 'register' && (
          <RegisterPage
            onNavigate={navigateTo}
            onSuccess={() => navigateTo('login')}
          />
        )}
        {page === 'forgot-password' && (
          <ForgotPasswordPage
            onNavigate={navigateTo}
            onDirectReset={(token) => navigateTo('reset-password', token)}
          />
        )}
        {page === 'reset-password' && (
          <ResetPasswordPage
            token={resetToken}
            onNavigate={navigateTo}
          />
        )}
      </main>

      {/* ── Cinematic Footer ── */}
      {!isAuthPage && (
        <footer className="site-footer">
          <div className="footer-brand-line">
            <img src="/cinewise-logo.png" alt="CineWise" style={{ height: 26, width: 'auto', verticalAlign: 'middle', marginRight: 8 }} />
            <strong>CineWise</strong> — AI-Powered Movie Discovery &amp; Recommendation Platform
          </div>
          <div style={{ marginTop: 6, color: 'var(--text-on-dark-dim)' }}>
            Content-Based TF-IDF &amp; Cosine Similarity Engine · Curated Global &amp; Indian Cinema
          </div>
          <div style={{ marginTop: 4, fontSize: '0.72rem', color: 'rgba(255,255,255,0.4)' }}>
            Tamil · Malayalam · Telugu · Kannada · Hindi · English
          </div>
        </footer>
      )}
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <CineWise />
    </AppProvider>
  );
}
