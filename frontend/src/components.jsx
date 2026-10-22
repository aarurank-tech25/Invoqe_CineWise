import { useState, memo, useRef, useEffect, useCallback } from 'react';
import { useAuth, useWatchlist, useWatched, useToast } from './context';
import { apiLogin, apiRegister, apiGetPerson, apiGetMovie, apiRecommend, apiAddWatched, apiRemoveWatched } from './api';

// ─────────────────────────────────────────────────────────────────────────────
// Watched Action Button
// ─────────────────────────────────────────────────────────────────────────────
export function WatchedBtn({ movieId, movieTitle }) {
  const { user } = useAuth();
  const { inWatched, addToWatched, removeFromWatched } = useWatched();
  const { addToast } = useToast();
  const [loading, setLoading] = useState(false);
  const watched = inWatched(movieId);

  const handle = async (e) => {
    e.stopPropagation();
    if (!user) { addToast('Sign in to track your watched movies', 'info'); return; }
    setLoading(true);
    try {
      if (watched) {
        await removeFromWatched(movieId);
        addToast('Removed from watched history', 'info');
      } else {
        await addToWatched(movieId);
        addToast('Marked as watched! ⭐', 'success');
      }
    } finally { setLoading(false); }
  };

  return (
    <button
      id={`watched-${movieId}`}
      type="button"
      className={`watched-btn${watched ? ' watched' : ''}`}
      onClick={handle}
      disabled={loading}
      aria-label={watched ? `Mark ${movieTitle} as unwatched` : `Mark ${movieTitle} as watched`}
      title={watched ? 'Watched (click to remove)' : 'Mark as watched'}
    >
      {loading ? '…' : watched ? '✓ Watched' : '👁 Watched'}
    </button>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Poster Image with Consistent 2:3 Portrait Aspect Ratio and Fallback
// ─────────────────────────────────────────────────────────────────────────────
export const Poster = memo(function Poster({ url, title, width, height, className = 'poster-frame' }) {
  const [imgSrc, setImgSrc] = useState(url);
  const [hasError, setHasError] = useState(false);

  // Determine if the initial URL is valid
  const bad = new Set(['', 'null', 'undefined', 'nan', 'none', '<na>', 'nat']);
  const isValidInitial = url && typeof url === 'string' && !bad.has(url.trim().toLowerCase()) && url.trim().startsWith('http');

  // Fallback asset path (placed in public folder)
  const fallbackSrc = 'file:///C:/Users/Aceus/.gemini/antigravity-ide/brain/5035738a-bb5b-4ea5-8900-8afa3b508a8b/poster_placeholder_1792679284214.jpg';

  // If the URL is invalid from the start, use fallback immediately
  if (!isValidInitial && !hasError) {
    setImgSrc(fallbackSrc);
    setHasError(true);
  }

  const handleError = () => {
    if (!hasError) {
      setImgSrc(fallbackSrc);
      setHasError(true);
    }
  };

  const style = {};
  if (width) style.width = width;
  if (height) style.height = height;

  return (
    <div className={className} style={style}>
      <img
        className="poster-img"
        src={imgSrc}
        alt={title ? `${title} poster` : 'Movie poster'}
        loading="lazy"
        onError={handleError}
      />
    </div>
  );
});

// ─────────────────────────────────────────────────────────────────────────────
// Star Rating with Gold Stars
// ─────────────────────────────────────────────────────────────────────────────
export function StarRating({ rating, voteCount }) {
  if (!rating || Number(rating) <= 0) return null;
  const fmt = (n) => n >= 1e6 ? `${(n/1e6).toFixed(1)}M` : n >= 1e3 ? `${(n/1e3).toFixed(0)}K` : String(n);
  return (
    <span className="star-rating" title={`${Number(rating).toFixed(1)} / 10 rating`}>
      <span className="star" aria-hidden="true">★</span>
      <strong>{Number(rating).toFixed(1)}</strong>
      <span className="votes">/ 10{voteCount > 0 ? ` (${fmt(voteCount)})` : ''}</span>
    </span>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// AI Match Badge (Cosine Similarity)
// ─────────────────────────────────────────────────────────────────────────────
export function AiBadge({ pct }) {
  if (!pct || pct <= 0) return null;
  return (
    <span className="ai-badge" title="Content-based TF-IDF & Cosine Similarity score">
      <span className="ai-badge-sparkle">✨</span> {Number(pct).toFixed(0)}% match
    </span>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Genre Pills
// ─────────────────────────────────────────────────────────────────────────────
export function GenrePills({ genres, genreStr }) {
  const list = genres?.length ? genres : (genreStr ? genreStr.split(',').map(s => s.trim()).filter(Boolean) : []);
  if (!list.length) return null;
  return (
    <div className="genre-pills">
      {list.slice(0, 4).map(g => <span key={g} className="genre-pill">{g}</span>)}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Language Badge
// ─────────────────────────────────────────────────────────────────────────────
export function LangBadge({ display }) {
  if (!display) return null;
  return <span className="lang-badge">{display}</span>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Verified OTT Streaming — Full Tier Display With Logos
// ─────────────────────────────────────────────────────────────────────────────
export function OttSection({ movie }) {
  const flatrate = movie.streaming_flatrate || [];
  const free = movie.streaming_free || [];
  const rent = movie.streaming_rent || [];
  const buy = movie.streaming_buy || [];
  const link = movie.streaming_link || '';
  const available = movie.streaming_available;

  if (!available) {
    return (
      <div className="ott-section">
        <div className="ott-section-head">
          <span className="ott-section-icon">📡</span>
          <span className="ott-section-title">Where to Watch in India</span>
        </div>
        <div className="ott-unavailable">OTT availability is currently unavailable.</div>
      </div>
    );
  }

  const renderProviders = (providers, label, className) => {
    if (!providers?.length) return null;
    return (
      <div className={`ott-tier ${className}`}>
        <span className="ott-tier-label">{label}</span>
        <div className="ott-tier-providers">
          {providers.map((p) => (
            <div key={p.provider_id || p.provider_name} className="ott-provider-chip">
              {p.logo_url ? (
                <img
                  src={p.logo_url}
                  alt={p.provider_name}
                  className="ott-logo"
                  title={p.provider_name}
                  onError={e => { e.target.style.display='none'; e.target.nextSibling.style.display='block'; }}
                />
              ) : null}
              <span className="ott-provider-name" style={p.logo_url ? { display: 'none' } : {}}>
                {p.provider_name}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="ott-section">
      <div className="ott-section-head">
        <span className="ott-section-icon">📺</span>
        <span className="ott-section-title">Where to Watch in India</span>
        {link && (
          <a href={link} target="_blank" rel="noopener noreferrer" className="ott-all-options">
            All Options ↗
          </a>
        )}
      </div>
      {renderProviders(flatrate, 'Subscription', 'ott-flatrate')}
      {renderProviders(free, 'Free / Ad-supported', 'ott-free')}
      {renderProviders(rent, 'Rent', 'ott-rent')}
      {renderProviders(buy, 'Buy', 'ott-buy')}
    </div>
  );
}

// Legacy compact OTT row for movie cards
export function OttRow({ providers, link }) {
  if (!providers?.length) {
    return <div className="ott-strip"><span>📺</span> <span className="ott-none">Streaming info unavailable for India</span></div>;
  }
  return (
    <div className="ott-strip">
      <span style={{ fontSize: '0.85rem' }}>📺</span>
      <span className="ott-providers-wrap">
        {providers.map(p => <span key={p} className="ott-chip">{p}</span>)}
      </span>
      {link && <a href={link} target="_blank" rel="noopener noreferrer" className="ott-link">Watch Options ↗</a>}
    </div>
  );
}


// ─────────────────────────────────────────────────────────────────────────────
// Watchlist Button
// ─────────────────────────────────────────────────────────────────────────────
export function WlBtn({ movieId, movieTitle }) {
  const { user } = useAuth();
  const { inWatchlist, addToWatchlist, removeFromWatchlist } = useWatchlist();
  const { addToast } = useToast();
  const [loading, setLoading] = useState(false);
  const saved = inWatchlist(movieId);

  const handle = async (e) => {
    e.stopPropagation();
    if (!user) { addToast('Sign in to save movies to your watchlist', 'info'); return; }
    setLoading(true);
    try {
      if (saved) {
        await removeFromWatchlist(movieId);
        addToast('Removed from watchlist', 'info');
      } else {
        await addToWatchlist(movieId);
        addToast('Added to watchlist!', 'success');
      }
    } finally { setLoading(false); }
  };

  return (
    <button
      id={`wl-${movieId}`}
      className={`wl-btn${saved ? ' saved' : ''}`}
      onClick={handle}
      disabled={loading}
      aria-label={saved ? `Remove ${movieTitle} from watchlist` : `Add ${movieTitle} to watchlist`}
      title={saved ? 'Remove from watchlist' : 'Add to watchlist'}
    >
      {loading ? '…' : saved ? '✓ Saved' : '+ Watchlist'}
    </button>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// AI Insight (Semantic overlaps)
// ─────────────────────────────────────────────────────────────────────────────
export function AiInsight({ insights, selectedTitle }) {
  if (!insights) return null;
  const parts = [];
  if (insights.shared_genres?.length) {
    parts.push(`Shares genres: ${insights.shared_genres.join(', ')}`);
  }
  if (insights.same_language) {
    parts.push('Same original language');
  }
  if (insights.shared_themes?.length) {
    parts.push(`Common themes: ${insights.shared_themes.join(', ')}`);
  }
  if (!parts.length) return null;

  return (
    <div className="ai-insight-box">
      <span className="ai-insight-label">AI Match Factor:</span> {parts.join(' · ')}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Movie Row — Numbered Vertical Recommendation List Item
// ─────────────────────────────────────────────────────────────────────────────
export function MovieRow({ movie, rank, selectedTitle, onPivot, onOpenDetails }) {
  const synopsis = movie.overview || '';
  const trunc = synopsis.length > 210 ? synopsis.slice(0, 208) + '…' : synopsis;
  const castStr = movie.cast_names?.length ? movie.cast_names.slice(0, 4).join(' · ') : null;

  return (
    <div className="movie-row" id={`mrow-${movie.id}`} role="listitem">
      {/* Rank Indicator */}
      {rank != null && (
        <div className="row-rank-wrap">
          <div className={`row-rank-badge${rank <= 3 ? ' top-rank' : ''}`}>
            #{rank}
          </div>
        </div>
      )}

      {/* Poster + Quick Action Toggles */}
      <div className="row-poster-col">
        <div
          className="row-poster-interactive"
          onClick={() => onOpenDetails && onOpenDetails(movie)}
          title={`View full details for ${movie.title}`}
          role="button"
          tabIndex={0}
        >
          <Poster url={movie.poster_url} title={movie.title} className="row-poster-frame" />
          <div className="row-poster-overlay">
            <span>👁 Quick View</span>
          </div>
        </div>
        <div className="row-poster-actions">
          <WlBtn movieId={movie.id} movieTitle={movie.title} />
          <WatchedBtn movieId={movie.id} movieTitle={movie.title} />
        </div>
      </div>

      {/* Movie Details Column */}
      <div className="row-info">
        <div className="row-title-line">
          <h3
            className="row-title clickable"
            onClick={() => onOpenDetails && onOpenDetails(movie)}
            title={`View full details for ${movie.title}`}
          >
            {movie.title}
          </h3>
          {movie.release_year > 0 && <span className="row-year">({movie.release_year})</span>}
          {movie.ai_match_pct > 0 && <AiBadge pct={movie.ai_match_pct} />}
        </div>

        <div className="row-meta">
          <StarRating rating={movie.vote_average} voteCount={movie.vote_count} />
          {movie.runtime > 0 && (
            <>
              <span className="meta-sep">·</span>
              <span className="row-runtime">{Math.floor(movie.runtime / 60)}h {movie.runtime % 60}m</span>
            </>
          )}
          {movie.certification && (
            <>
              <span className="meta-sep">·</span>
              <span className="cert-badge">{movie.certification}</span>
            </>
          )}
          {movie.language_display && (
            <>
              <span className="meta-sep">·</span>
              <LangBadge display={movie.language_display} />
            </>
          )}
        </div>

        <GenrePills genres={movie.genres} genreStr={movie.genre_str} />

        {trunc && <p className="row-synopsis">{trunc}</p>}

        <div className="row-credits">
          {movie.director && (
            <div><span className="credit-label">Director:</span> <span className="credit-value">{movie.director}</span></div>
          )}
          {castStr && (
            <div><span className="credit-label">Stars:</span> <span className="credit-value">{castStr}</span></div>
          )}
        </div>

        {movie.ai_insights && <AiInsight insights={movie.ai_insights} selectedTitle={selectedTitle} />}
        <OttRow providers={movie.streaming_providers} link={movie.streaming_link} />
      </div>

      {/* Action Buttons */}
      <div className="row-actions">
        {onOpenDetails && (
          <button
            id={`details-${movie.id}`}
            type="button"
            className="row-action-btn view-details-btn"
            onClick={() => onOpenDetails(movie)}
            title="Open comprehensive movie details, cast & OTT streaming"
          >
            👁 View Details
          </button>
        )}
        {onPivot && (
          <button
            id={`pivot-${movie.id}`}
            type="button"
            className="row-action-btn pivot-btn"
            onClick={() => onPivot(movie)}
            title="Generate AI recommendations based on this movie"
          >
            ↺ Recommend From This
          </button>
        )}
        <a
          href={`https://www.imdb.com/find?q=${encodeURIComponent(movie.title)}`}
          target="_blank"
          rel="noopener noreferrer"
          className="imdb-link"
          title="Search on IMDb"
        >
          ↗ IMDb
        </a>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Movie List Wrapper
// ─────────────────────────────────────────────────────────────────────────────
export function MovieList({ movies, selectedTitle, onPivot, onOpenDetails, title, startRank = 1 }) {
  if (!movies?.length) return null;
  return (
    <div className="movie-list" role="list" aria-label={title || 'Movie list'}>
      {title && (
        <div className="movie-list-head">
          <span className="movie-list-head-title">{title}</span>
          <span className="movie-list-head-count">{movies.length} titles evaluated</span>
        </div>
      )}
      {movies.map((m, i) => (
        <MovieRow
          key={m.id}
          movie={m}
          rank={startRank + i}
          selectedTitle={selectedTitle}
          onPivot={onPivot}
          onOpenDetails={onOpenDetails}
        />
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Selected Movie Hero Spotlight Card
// ─────────────────────────────────────────────────────────────────────────────
export function SelectedHero({ movie, onRecommend, onOpenDetails, onExplorePerson }) {
  const { user } = useAuth();
  const { inWatchlist, addToWatchlist, removeFromWatchlist } = useWatchlist();
  const { addToast } = useToast();
  const [wlLoading, setWlLoading] = useState(false);
  const saved = inWatchlist(movie.id);

  const handleWl = async () => {
    if (!user) { addToast('Sign in to manage your watchlist', 'info'); return; }
    setWlLoading(true);
    try {
      if (saved) { await removeFromWatchlist(movie.id); addToast('Removed from watchlist', 'info'); }
      else { await addToWatchlist(movie.id); addToast('Added to watchlist!', 'success'); }
    } finally { setWlLoading(false); }
  };

  const castStr = movie.cast_names?.length ? movie.cast_names.slice(0, 5).join(' · ') : null;

  return (
    <div className="hero-card" id="selected-hero">
      <div className="hero-poster-frame" onClick={() => onOpenDetails && onOpenDetails(movie)} style={{ cursor: 'pointer' }}>
        <Poster url={movie.poster_url} title={movie.title} className="hero-poster-img-wrap" />
      </div>

      <div className="hero-info">
        <div className="hero-badge-tag">SELECTED SPOTLIGHT PROFILE</div>
        <h2 className="hero-title clickable" onClick={() => onOpenDetails && onOpenDetails(movie)}>
          {movie.title}
          {movie.release_year > 0 && <span className="hero-year">({movie.release_year})</span>}
        </h2>

        {movie.tagline && <p className="hero-tagline">&ldquo;{movie.tagline}&rdquo;</p>}

        <div className="hero-meta-row">
          <StarRating rating={movie.vote_average} voteCount={movie.vote_count} />
          {movie.runtime > 0 && (
            <>
              <span className="meta-sep">·</span>
              <span className="hero-runtime">{Math.floor(movie.runtime / 60)}h {movie.runtime % 60}m</span>
            </>
          )}
          {movie.certification && (
            <>
              <span className="meta-sep">·</span>
              <span className="cert-badge">{movie.certification}</span>
            </>
          )}
          {movie.language_display && (
            <>
              <span className="meta-sep">·</span>
              <LangBadge display={movie.language_display} />
            </>
          )}
        </div>

        <GenrePills genres={movie.genres} genreStr={movie.genre_str} />

        <p className="hero-synopsis">{movie.overview || 'No plot synopsis available in catalog.'}</p>

        <div className="hero-credits">
          {movie.director && (
            <div><span className="credit-label">Director:</span> <span className="credit-value">{movie.director}</span></div>
          )}
          {castStr && (
            <div><span className="credit-label">Stars:</span> <span className="credit-value">{castStr}</span></div>
          )}
        </div>

        <div className="hero-ott">
          <OttSection movie={movie} />
        </div>

        {/* Cast & Crew Section with Actor Profiles */}
        {movie.cast?.length > 0 && (
          <CastSection
            cast={movie.cast}
            onExplorePerson={onExplorePerson}
            onOpenMovie={onOpenDetails}
          />
        )}

        <div className="hero-actions">
          {onRecommend && (
            <button id={`hero-refresh-${movie.id}`} className="btn-primary" onClick={onRecommend}>
              ↺ Refresh Recommendations
            </button>
          )}
          {onOpenDetails && (
            <button id={`hero-details-${movie.id}`} className="btn-secondary" onClick={() => onOpenDetails(movie)}>
              👁 View Full Movie Details
            </button>
          )}
          <button id={`hero-wl-${movie.id}`} className="btn-secondary" onClick={handleWl} disabled={wlLoading}>
            {wlLoading ? '…' : saved ? '✓ In Watchlist' : '+ Add to Watchlist'}
          </button>
          <WatchedBtn movieId={movie.id} movieTitle={movie.title} />
          {movie.trailer_url && (
            <a
              href={movie.trailer_url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-trailer"
              aria-label="Watch verified official trailer on YouTube"
              title="Watch official trailer on YouTube"
            >
              ▶ Official Trailer
            </a>
          )}
          <a
            href={`https://www.imdb.com/find?q=${encodeURIComponent(movie.title)}`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-ghost"
          >
            ↗ View on IMDb
          </a>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Person Modal — Actor / Director Profile with Known-For & Exploration
// ─────────────────────────────────────────────────────────────────────────────
export function PersonModal({ personId, personName, onClose, onExplorePerson, onOpenMovie }) {
  const [person, setPerson] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');

  useEffect(() => {
    if (!personId) return;
    setLoading(true);
    setErr('');
    apiGetPerson(personId)
      .then(data => { setPerson(data); setLoading(false); })
      .catch(e => { setErr(e.message || 'Failed to load profile'); setLoading(false); });
  }, [personId]);

  // Close on Escape
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const bio = person?.biography || 'Biography is currently unavailable.';
  const bioTrunc = bio.length > 700 ? bio.slice(0, 698) + '…' : bio;

  return (
    <div className="modal-overlay person-modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal-box person-modal" role="dialog" aria-modal="true" aria-label={`${personName || 'Actor'} profile`}>
        <button className="modal-close" onClick={onClose} aria-label="Close profile">×</button>

        {loading && (
          <div className="modal-loading">
            <div className="spinner"></div>
            <span>Loading profile details…</span>
          </div>
        )}

        {err && <div className="alert alert-error">{err}</div>}

        {!loading && person && (
          <div className="person-profile">
            <div className="person-profile-header">
              <div className="person-avatar-wrap">
                {person.profile_url ? (
                  <img
                    src={person.profile_url}
                    alt={person.name}
                    className="person-avatar"
                    onError={e => { e.target.src = ''; e.target.className = 'person-avatar-placeholder'; }}
                  />
                ) : (
                  <div className="person-avatar-placeholder">👤</div>
                )}
              </div>
              <div className="person-info-col">
                <h2 className="person-name">{person.name}</h2>
                <div className="person-dept">{person.known_for_department || 'Acting'}</div>
                {person.place_of_birth && (
                  <div className="person-birth">📍 Born in {person.place_of_birth}</div>
                )}
                {person.birthday && (
                  <div className="person-birthday">🎂 Born on {person.birthday}</div>
                )}

                {/* Explore button */}
                <div style={{ marginTop: 12 }}>
                  <button
                    type="button"
                    className="btn-explore-person"
                    onClick={() => {
                      if (onExplorePerson) onExplorePerson(person.name, person.id);
                      onClose();
                    }}
                  >
                    🎬 Explore Movies Featuring {person.name}
                  </button>
                </div>
              </div>
            </div>

            <div className="person-bio">
              <div className="person-bio-label">Biography</div>
              <p>{bioTrunc}</p>
            </div>

            {person.known_for?.length > 0 && (
              <div className="person-known-for">
                <div className="person-known-for-label">Known For ({person.known_for.length} Titles)</div>
                <div className="person-movie-scroll">
                  {person.known_for.map(m => (
                    <div
                      key={m.id}
                      className="person-movie-card"
                      onClick={() => {
                        if (onOpenMovie) {
                          onOpenMovie(m);
                          onClose();
                        }
                      }}
                      role="button"
                      tabIndex={0}
                      title={`View details for ${m.title}`}
                    >
                      {m.poster_url ? (
                        <img src={m.poster_url} alt={m.title} className="person-movie-poster" onError={e => { e.target.style.display='none'; }} />
                      ) : (
                        <div className="person-movie-poster-placeholder">🎬</div>
                      )}
                      <div className="person-movie-title">{m.title}</div>
                      {m.character && <div className="person-movie-char">{m.character}</div>}
                      {m.release_year > 0 && <div className="person-movie-year">{m.release_year}</div>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Cast Section — Horizontal Cast Cards with Photos & View Profile
// ─────────────────────────────────────────────────────────────────────────────
export function CastSection({ cast, onExplorePerson, onOpenMovie }) {
  const [selectedPerson, setSelectedPerson] = useState(null);
  if (!cast?.length) return null;

  return (
    <div className="cast-section">
      <div className="cast-section-title">Cast &amp; Crew</div>
      <div className="cast-scroll">
        {cast.slice(0, 15).map(member => (
          <div
            key={member.id || member.name}
            className="cast-card"
            onClick={() => setSelectedPerson(member)}
            title={`View ${member.name} profile`}
            role="button"
            tabIndex={0}
            aria-label={`View ${member.name} profile`}
          >
            <div className="cast-photo-wrap">
              {member.profile_url ? (
                <img
                  src={member.profile_url}
                  alt={member.name}
                  className="cast-photo"
                  loading="lazy"
                  onError={e => { e.target.style.display='none'; e.target.nextSibling.style.display='flex'; }}
                />
              ) : null}
              <div className="cast-photo-fallback" style={member.profile_url ? { display: 'none' } : {}}>👤</div>
            </div>
            <div className="cast-name">{member.name}</div>
            {member.character ? (
              <div className="cast-character" title={member.character}>
                {member.character.length > 22 ? member.character.slice(0, 20) + '…' : member.character}
              </div>
            ) : (
              <div className="cast-character muted">Cast</div>
            )}
            <div className="cast-view-profile">View Profile ↗</div>
          </div>
        ))}
      </div>
      {selectedPerson && (
        <PersonModal
          personId={selectedPerson.id}
          personName={selectedPerson.name}
          onClose={() => setSelectedPerson(null)}
          onExplorePerson={onExplorePerson}
          onOpenMovie={onOpenMovie}
        />
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Movie Details Modal — Comprehensive Movie Page Experience
// ─────────────────────────────────────────────────────────────────────────────
export function MovieDetailsModal({ movie, movieId, onClose, onPivot, onExplorePerson, region = 'IN' }) {
  const [data, setData] = useState(movie || null);
  const [loading, setLoading] = useState(!movie || !movie.overview || !movie.cast);
  const [recs, setRecs] = useState([]);
  const [loadingRecs, setLoadingRecs] = useState(false);
  const { user } = useAuth();
  const { inWatchlist, addToWatchlist, removeFromWatchlist } = useWatchlist();
  const { inWatched, addToWatched, removeFromWatched } = useWatched();
  const { addToast } = useToast();

  const idToLoad = movieId || movie?.id;

  useEffect(() => {
    if (!idToLoad) return;
    setLoading(true);
    apiGetMovie(idToLoad, region)
      .then(m => {
        setData(m);
        setLoading(false);
      })
      .catch(() => setLoading(false));

    setLoadingRecs(true);
    apiRecommend({ movie_id: idToLoad, top_k: 6 }, region)
      .then(res => {
        setRecs(res.recommendations || []);
        setLoadingRecs(false);
      })
      .catch(() => setLoadingRecs(false));
  }, [idToLoad, region]);

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  if (!data && loading) {
    return (
      <div className="modal-overlay movie-modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
        <div className="modal-box movie-details-modal" role="dialog" aria-modal="true">
          <button className="modal-close" onClick={onClose}>×</button>
          <div className="modal-loading"><div className="spinner"></div><span>Loading movie details…</span></div>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const saved = inWatchlist(data.id);
  const watched = inWatched(data.id);

  const toggleWl = async () => {
    if (!user) { addToast('Sign in to manage your watchlist', 'info'); return; }
    if (saved) { await removeFromWatchlist(data.id); addToast('Removed from watchlist', 'info'); }
    else { await addToWatchlist(data.id); addToast('Added to watchlist!', 'success'); }
  };

  const toggleWatched = async () => {
    if (!user) { addToast('Sign in to track your watched history', 'info'); return; }
    if (watched) { await removeFromWatched(data.id); addToast('Removed from watched history', 'info'); }
    else { await addToWatched(data.id); addToast('Marked as watched! ⭐', 'success'); }
  };

  return (
    <div className="modal-overlay movie-modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal-box movie-details-modal" role="dialog" aria-modal="true" aria-label={data.title}>
        <button className="modal-close" onClick={onClose} aria-label="Close modal">×</button>

        {/* Backdrop Banner Header with Gradient */}
        <div
          className="movie-modal-backdrop"
          style={data.backdrop_url ? { backgroundImage: `url(${data.backdrop_url})` } : {}}
        >
          <div className="movie-modal-backdrop-overlay" />
          <div className="movie-modal-header-content">
            <div className="movie-modal-poster-wrap">
              <Poster url={data.poster_url} title={data.title} className="movie-modal-poster" />
            </div>
            <div className="movie-modal-header-info">
              <div className="movie-modal-tag">CINEMA PROFILE</div>
              <h2 className="movie-modal-title">
                {data.title}
                {data.release_year > 0 && <span className="movie-modal-year">({data.release_year})</span>}
              </h2>
              {data.tagline && <p className="movie-modal-tagline">&ldquo;{data.tagline}&rdquo;</p>}
              <div className="movie-modal-meta-row">
                <StarRating rating={data.vote_average} voteCount={data.vote_count} />
                {data.runtime > 0 && (
                  <>
                    <span className="meta-sep">·</span>
                    <span>{Math.floor(data.runtime / 60)}h {data.runtime % 60}m</span>
                  </>
                )}
                {data.certification && (
                  <>
                    <span className="meta-sep">·</span>
                    <span className="cert-badge">{data.certification}</span>
                  </>
                )}
                {data.release_date && (
                  <>
                    <span className="meta-sep">·</span>
                    <span>{data.release_date}</span>
                  </>
                )}
                {data.language_display && (
                  <>
                    <span className="meta-sep">·</span>
                    <LangBadge display={data.language_display} />
                  </>
                )}
              </div>
              <GenrePills genres={data.genres} genreStr={data.genre_str} />
            </div>
          </div>
        </div>

        {/* Action Bar */}
        <div className="movie-modal-actions-bar">
          <button className={`btn-action${saved ? ' active' : ''}`} onClick={toggleWl}>
            {saved ? '✓ In Watchlist' : '+ Add to Watchlist'}
          </button>
          <button className={`btn-action${watched ? ' active' : ''}`} onClick={toggleWatched}>
            {watched ? '✓ Watched' : '👁 Mark as Watched'}
          </button>
          {data.trailer_url && (
            <a
              href={data.trailer_url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-trailer-gold"
              title="Watch official trailer on YouTube"
            >
              ▶ Official Trailer
            </a>
          )}
          {onPivot && (
            <button
              className="btn-pivot-gold"
              onClick={() => { onClose(); onPivot(data); }}
              title="Generate AI recommendations based on this movie"
            >
              ✦ Recommend From This
            </button>
          )}
          <a
            href={`https://www.imdb.com/find?q=${encodeURIComponent(data.title)}`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-ghost-sm"
          >
            ↗ IMDb
          </a>
        </div>

        {/* Modal Body */}
        <div className="movie-modal-body">
          {/* Plot Synopsis */}
          <div className="movie-modal-synopsis-section">
            <h3 className="section-heading">Storyline</h3>
            <p className="movie-modal-synopsis">{data.overview || 'No synopsis available in movie catalog.'}</p>
          </div>

          {/* Director & Writers */}
          {(data.director || data.writer_str) && (
            <div className="movie-modal-crew-section">
              {data.director && (
                <div className="crew-item">
                  <span className="crew-role">Director</span>
                  <span className="crew-name">{data.director}</span>
                </div>
              )}
              {data.writer_str && (
                <div className="crew-item">
                  <span className="crew-role">Writers</span>
                  <span className="crew-name">{data.writer_str}</span>
                </div>
              )}
            </div>
          )}

          {/* Where to Watch in India (OTT) */}
          <div className="movie-modal-ott-section">
            <OttSection movie={data} />
          </div>

          {/* Cast & Crew Section */}
          {data.cast?.length > 0 && (
            <div className="movie-modal-cast-section">
              <CastSection
                cast={data.cast}
                onExplorePerson={onExplorePerson}
                onOpenMovie={(m) => setData(m)}
              />
            </div>
          )}

          {/* Similar Movies from AI Engine */}
          <div className="movie-modal-similar-section">
            <h3 className="section-heading">Similar Movies You May Like</h3>
            <p className="section-subtext">Computed using content-based TF-IDF &amp; Cosine Similarity</p>
            {loadingRecs && <div className="loading-row"><span className="spinner"></span> Computing similar movies…</div>}
            {!loadingRecs && recs.length > 0 && (
              <div className="similar-movies-grid">
                {recs.map(sm => (
                  <div
                    key={sm.id}
                    className="similar-movie-card"
                    onClick={() => { setData(sm); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                    role="button"
                    tabIndex={0}
                    title={`View details for ${sm.title}`}
                  >
                    <Poster url={sm.poster_url} title={sm.title} className="similar-poster" />
                    <div className="similar-info">
                      <div className="similar-title" title={sm.title}>{sm.title}</div>
                      <div className="similar-meta">
                        {sm.release_year > 0 && <span>{sm.release_year}</span>}
                        {sm.ai_match_pct > 0 && <span className="similar-match">{sm.ai_match_pct}% Match</span>}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Featured Card — Compact, Perfectly Aligned Movie Discovery Card
// ─────────────────────────────────────────────────────────────────────────────
export function FeaturedCard({ movie, onSelect, onOpenDetails }) {
  const [imgErr, setImgErr] = useState(false);
  const bad = new Set(['', 'null', 'undefined', 'nan', 'none', '<na>']);
  const validUrl = movie.poster_url && !bad.has((movie.poster_url || '').toLowerCase()) && movie.poster_url.startsWith('http') && !imgErr;

  const genreDisplay = movie.genres?.length
    ? movie.genres.slice(0, 2).join(' · ')
    : (movie.genre_str?.split(',').slice(0, 2).map(s => s.trim()).join(' · ') || 'Cinema');

  const handleCardClick = () => {
    if (onOpenDetails) onOpenDetails(movie);
    else onSelect(movie);
  };

  return (
    <div
      className="featured-card"
      onClick={handleCardClick}
      role="button"
      tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && handleCardClick()}
      aria-label={`View details or get recommendations for ${movie.title}`}
    >
      <div className="featured-card-poster-wrap">
        {validUrl ? (
          <img
            className="featured-card-poster"
            src={movie.poster_url}
            alt={movie.title}
            loading="lazy"
            onError={() => setImgErr(true)}
          />
        ) : (
          <div className="featured-card-poster placeholder poster-placeholder">
            <div className="poster-placeholder-icon">🎬</div>
            <div className="poster-placeholder-text">{movie.title}</div>
          </div>
        )}

        {/* Floating rating badge */}
        {movie.vote_average > 0 && (
          <div className="featured-poster-rating">
            <span className="star">★</span> {Number(movie.vote_average).toFixed(1)}
          </div>
        )}

        {/* Floating release year */}
        {movie.release_year > 0 && (
          <div className="featured-poster-year">
            {movie.release_year}
          </div>
        )}
      </div>

      <div className="featured-card-body">
        <h4 className="featured-card-title" title={movie.title}>
          {movie.title}
        </h4>

        <div className="featured-card-meta">
          <span className="featured-card-genre" title={genreDisplay}>
            {genreDisplay}
          </span>
          {movie.language_display && (
            <span className="featured-card-lang">{movie.language_display}</span>
          )}
        </div>

        <div className="featured-card-btn-group">
          {onOpenDetails && (
            <button
              id={`feat-det-${movie.id}`}
              type="button"
              className="featured-card-btn-subtle"
              onClick={e => {
                e.stopPropagation();
                onOpenDetails(movie);
              }}
              title="View complete movie details & where to watch"
            >
              👁 Details
            </button>
          )}
          <button
            id={`feat-${movie.id}`}
            type="button"
            className="featured-card-btn"
            onClick={e => {
              e.stopPropagation();
              onSelect(movie);
            }}
            title="Generate AI recommendations based on this movie"
          >
            ✦ Recommend
          </button>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Movie Autocomplete Search with Custom Search Control
// ─────────────────────────────────────────────────────────────────────────────
export function MovieAutocomplete({ titles, onSelect, onSubmit, placeholder = 'Search by title (e.g., Inception, Interstellar, Vikram)...', initialValue = '' }) {
  const [query, setQuery] = useState(initialValue);
  const [open, setOpen] = useState(false);
  const [hi, setHi] = useState(0);
  const inputRef = useRef(null);

  useEffect(() => { setQuery(initialValue); }, [initialValue]);

  const filtered = query.trim().length >= 2
    ? titles.filter(t => t.toLowerCase().includes(query.toLowerCase())).slice(0, 30)
    : [];

  const pick = (title) => {
    setQuery(title);
    setOpen(false);
    onSelect(title);
  };

  const onKeyDown = (e) => {
    if (!open || !filtered.length) {
      if (e.key === 'Enter') {
        e.preventDefault();
        if (query.trim()) onSelect(query.trim());
      }
      return;
    }
    if (e.key === 'ArrowDown') { e.preventDefault(); setHi(h => Math.min(h+1, filtered.length-1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setHi(h => Math.max(h-1, 0)); }
    else if (e.key === 'Enter') {
      e.preventDefault();
      if (filtered[hi]) pick(filtered[hi]);
      else if (query.trim()) onSelect(query.trim());
    }
    else if (e.key === 'Escape') setOpen(false);
  };

  return (
    <div className="autocomplete-wrap">
      <div className="search-input-inner">
        <span className="search-icon" aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </span>
        <input
          id="movie-search-input"
          ref={inputRef}
          className="search-input"
          type="text"
          placeholder={placeholder}
          value={query}
          onChange={e => { setQuery(e.target.value); setOpen(true); setHi(0); }}
          onFocus={() => query.length >= 2 && setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 220)}
          onKeyDown={onKeyDown}
          autoComplete="off"
          aria-label="Search movie by title"
          aria-expanded={open && filtered.length > 0}
          aria-autocomplete="list"
        />
        {query && (
          <button
            type="button"
            className="search-clear"
            onClick={() => { setQuery(''); onSelect(''); setOpen(false); }}
            aria-label="Clear search query"
          >
            ×
          </button>
        )}
      </div>

      {open && filtered.length > 0 && (
        <div className="autocomplete-list" role="listbox">
          {filtered.map((t, i) => (
            <div
              key={t}
              className={`autocomplete-item${i === hi ? ' hi' : ''}`}
              role="option"
              aria-selected={i === hi}
              onMouseDown={() => pick(t)}
            >
              <span className="autocomplete-item-text">{t}</span>
              <span className="autocomplete-item-action">Select →</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Auth Modal (Legacy fallback if invoked)
// ─────────────────────────────────────────────────────────────────────────────
export function AuthModal({ mode: initMode, onClose }) {
  const [mode, setMode] = useState(initMode || 'login');
  const [form, setForm] = useState({ name: '', email: '', password: '', pass2: '' });
  const [err, setErr] = useState('');
  const [ok, setOk] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const { addToast } = useToast();
  const set = k => e => setForm(f => ({ ...f, [k]: e.target.value }));

  const doLogin = async () => {
    setErr(''); setLoading(true);
    try {
      const res = await apiLogin({ email: form.email, password: form.password });
      if (res.user) { login(res.user); addToast(`Welcome back, ${res.user.name}!`, 'success'); onClose(); }
    } catch (e) { setErr(e.message); } finally { setLoading(false); }
  };

  const doRegister = async () => {
    setErr('');
    if (!form.name || !form.email || !form.password) { setErr('All fields are required'); return; }
    if (form.password !== form.pass2) { setErr('Passwords do not match'); return; }
    if (form.password.length < 6) { setErr('Password must be at least 6 characters'); return; }
    setLoading(true);
    try {
      await apiRegister({ name: form.name, email: form.email, password: form.password });
      setOk('Account created! You can now sign in.');
      setMode('login');
    } catch (e) { setErr(e.message); } finally { setLoading(false); }
  };

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal-box" role="dialog" aria-modal="true">
        <button className="modal-close" onClick={onClose} aria-label="Close">×</button>
        <h2 className="modal-title">{mode === 'login' ? 'Sign in to CineWise' : 'Create an Account'}</h2>
        {err && <div className="alert alert-error">{err}</div>}
        {ok && <div className="alert alert-success">{ok}</div>}
        {mode === 'register' && (
          <div className="form-group">
            <label className="form-label" htmlFor="reg-name">Full Name</label>
            <input id="reg-name" className="form-input" type="text" value={form.name} onChange={set('name')} placeholder="Alex Smith" />
          </div>
        )}
        <div className="form-group">
          <label className="form-label" htmlFor="auth-email">Email</label>
          <input id="auth-email" className="form-input" type="email" value={form.email} onChange={set('email')} placeholder="you@example.com" />
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor="auth-pass">Password</label>
          <input id="auth-pass" className="form-input" type="password" value={form.password} onChange={set('password')} placeholder="••••••••" />
        </div>
        {mode === 'register' && (
          <div className="form-group">
            <label className="form-label" htmlFor="auth-pass2">Confirm Password</label>
            <input id="auth-pass2" className="form-input" type="password" value={form.pass2} onChange={set('pass2')} placeholder="••••••••" />
          </div>
        )}
        <button
          id={mode === 'login' ? 'btn-do-login' : 'btn-do-register'}
          className="btn-primary"
          style={{ width: '100%', height: 42, fontSize: '0.92rem' }}
          onClick={mode === 'login' ? doLogin : doRegister}
          disabled={loading}
        >
          {loading ? '…' : mode === 'login' ? 'Sign In' : 'Create Account'}
        </button>
        <div className="form-link-row">
          {mode === 'login'
            ? <>No account? <button className="form-link" onClick={() => { setMode('register'); setErr(''); }}>Create one</button></>
            : <>Already registered? <button className="form-link" onClick={() => { setMode('login'); setErr(''); }}>Sign in</button></>
          }
        </div>
      </div>
    </div>
  );
}
