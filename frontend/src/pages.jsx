import { useState, useEffect, useCallback } from 'react';
import { useAuth, useWatchlist, useWatched, useToast } from './context';
import {
  MovieAutocomplete,
  SelectedHero,
  MovieList,
  FeaturedCard,
  OttRow,
  Poster,
  StarRating,
  LangBadge,
  WatchedBtn,
  WlBtn,
  MovieDetailsModal,
  PersonModal,
} from './components';
import {
  apiGetTitles,
  apiGetMovie,
  apiRecommend,
  apiExplore,
  apiGetGenres,
  apiSearch,
  apiGetWatchlist,
  apiGetWatched,
  apiRemoveWatched,
  apiGetPreferences,
  apiSavePreferences,
  apiGetPersonalized,
} from './api';

const LANGUAGES = [
  { code: 'all', label: 'All Languages' },
  { code: 'ta', label: 'Tamil (தமிழ்)' },
  { code: 'ml', label: 'Malayalam (മലയാളം)' },
  { code: 'te', label: 'Telugu (తెలుగు)' },
  { code: 'kn', label: 'Kannada (ಕನ್ನಡ)' },
  { code: 'hi', label: 'Hindi (हिंदी)' },
  { code: 'en', label: 'English' },
];

const ERA_FILTERS = [
  { label: 'All Release Eras', from: null, to: null },
  { label: '2020s (2020–2026)', from: 2020, to: 2026 },
  { label: '2010s (2010–2019)', from: 2010, to: 2019 },
  { label: '2000s (2000–2009)', from: 2000, to: 2009 },
  { label: '1990s (1990–1999)', from: 1990, to: 1999 },
  { label: 'Classic (Pre-1990)', from: 1900, to: 1989 },
];

const RATING_FILTERS = [
  { label: 'All Verified Ratings', min: null },
  { label: '★ 8.0+ Exceptional', min: 8.0 },
  { label: '★ 7.5+ Great', min: 7.5 },
  { label: '★ 7.0+ Good', min: 7.0 },
];

// ─────────────────────────────────────────────────────────────────────────────
// Home Page — Search + Selected Movie Spotlight + TF-IDF Recommendations
// ─────────────────────────────────────────────────────────────────────────────
export function HomePage({ region, onNavigateToExplore }) {
  const { user } = useAuth();
  const [titles, setTitles] = useState([]);
  const [genres, setGenres] = useState([]);
  const [selectedTitle, setSelectedTitle] = useState('');
  const [selectedMovieId, setSelectedMovieId] = useState(null);
  const [langFilter, setLangFilter] = useState('all');
  const [genreFilter, setGenreFilter] = useState('all');
  const [topK, setTopK] = useState(10);
  const [sortBy, setSortBy] = useState('ai_match');
  const [selectedMeta, setSelectedMeta] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [recTotal, setRecTotal] = useState(0);
  const [showcase, setShowcase] = useState([]);
  const [showcaseTab, setShowcaseTab] = useState('trending'); // 'trending', 'indian', 'top_rated'
  const [personalized, setPersonalized] = useState([]);
  const [personalizedMsg, setPersonalizedMsg] = useState('');
  const [loadingMeta, setLoadingMeta] = useState(false);
  const [loadingRecs, setLoadingRecs] = useState(false);
  const [loadingShowcase, setLoadingShowcase] = useState(false);
  const [loadingPersonalized, setLoadingPersonalized] = useState(false);
  const [error, setError] = useState('');

  // Modals state
  const [detailsModalMovie, setDetailsModalMovie] = useState(null);
  const [personModal, setPersonModal] = useState(null); // { id, name }

  // Check preseeded title from Explore or Watchlist
  useEffect(() => {
    const preseedTitle = sessionStorage.getItem('cw_preseed_title');
    const preseedId = sessionStorage.getItem('cw_preseed_id');
    if (preseedTitle) {
      sessionStorage.removeItem('cw_preseed_title');
      sessionStorage.removeItem('cw_preseed_id');
      setSelectedTitle(preseedTitle);
      if (preseedId) {
        setSelectedMovieId(Number(preseedId));
        apiGetMovie(Number(preseedId), region)
          .then(m => setSelectedMeta(m))
          .catch(() => {});
      } else {
        resolveMovieId(preseedTitle);
      }
    }
  }, []);

  // Load titles and genres on mount or language change
  useEffect(() => {
    apiGetTitles(langFilter).then(d => setTitles(d.titles || [])).catch(() => {});
    apiGetGenres().then(d => setGenres(d.genres || [])).catch(() => {});
  }, [langFilter]);

  // Load showcase movies according to selected showcase tab
  useEffect(() => {
    setLoadingShowcase(true);
    let lang = langFilter !== 'all' ? langFilter : 'all';
    let sort = 'popularity';

    if (showcaseTab === 'indian') {
      lang = langFilter !== 'all' ? langFilter : 'ta'; // Defaults to South Asian / Tamil catalog
      sort = 'popularity';
    } else if (showcaseTab === 'top_rated') {
      sort = 'rating';
    }

    apiExplore({ sort_by: sort, limit: 16, language: lang })
      .then(d => setShowcase(d.movies || []))
      .catch(() => {})
      .finally(() => setLoadingShowcase(false));
  }, [langFilter, showcaseTab]);

  // Load personalized recommendations if user is logged in
  useEffect(() => {
    if (!user?.id) {
      setPersonalized([]);
      setPersonalizedMsg('');
      return;
    }
    setLoadingPersonalized(true);
    apiGetPersonalized(user.id, 8, region)
      .then(d => {
        setPersonalized(d.movies || []);
        setPersonalizedMsg(d.message || '');
      })
      .catch(() => {})
      .finally(() => setLoadingPersonalized(false));
  }, [user?.id, region]);

  const resolveMovieId = useCallback(async (titleStr) => {
    if (!titleStr) {
      setSelectedMovieId(null);
      setSelectedMeta(null);
      setRecommendations([]);
      return;
    }
    setLoadingMeta(true);
    setError('');
    try {
      const clean = titleStr.split(' (')[0].trim();
      const data = await apiSearch({ q: clean, limit: 6 });
      const movies = data.movies || [];
      if (!movies.length) {
        setError(`"${titleStr}" was not found in the movie catalog.`);
        setLoadingMeta(false);
        return;
      }
      const exact = movies.find(m => {
        const label = `${m.title} (${m.release_year})`;
        return label === titleStr || m.title.toLowerCase() === clean.toLowerCase();
      });
      const movie = exact || movies[0];
      setSelectedMovieId(movie.id);
      setSelectedMeta(movie);
    } catch (e) {
      setError(e.message || 'Error finding movie details.');
    } finally {
      setLoadingMeta(false);
    }
  }, []);

  const fetchRecs = useCallback(async (movieId) => {
    if (!movieId) return;
    setLoadingRecs(true);
    setRecommendations([]);
    setError('');
    try {
      const data = await apiRecommend({
        movie_id: movieId,
        top_k: topK,
        language_filter: langFilter !== 'all' ? langFilter : null,
        genre_filter: genreFilter !== 'all' ? genreFilter : null,
        sort_by: sortBy,
      }, region);

      if (data.selected) setSelectedMeta(data.selected);
      setRecommendations(data.recommendations || []);
      setRecTotal(data.total || 0);
    } catch (e) {
      setError(`Recommendation engine error: ${e.message}`);
    } finally {
      setLoadingRecs(false);
    }
  }, [topK, langFilter, genreFilter, sortBy, region]);

  useEffect(() => {
    if (selectedMovieId) {
      fetchRecs(selectedMovieId);
    }
  }, [selectedMovieId, topK, langFilter, genreFilter, sortBy, fetchRecs]);

  const handleSelect = (title) => {
    setSelectedTitle(title);
    resolveMovieId(title);
  };

  const handleFeaturedSelect = (movie) => {
    const label = movie.release_year > 0 ? `${movie.title} (${movie.release_year})` : movie.title;
    setSelectedTitle(label);
    setSelectedMovieId(movie.id);
    setSelectedMeta(movie);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handlePivot = (movie) => {
    handleFeaturedSelect(movie);
  };

  const handleClearSelection = () => {
    setSelectedTitle('');
    setSelectedMovieId(null);
    setSelectedMeta(null);
    setRecommendations([]);
    setError('');
  };

  const handleExplorePerson = (personName) => {
    if (onNavigateToExplore) {
      onNavigateToExplore(personName);
    } else {
      sessionStorage.setItem('cw_explore_query', personName);
      window.location.search = `?page=explore&q=${encodeURIComponent(personName)}`;
    }
  };

  const SORT_OPTS = [
    { code: 'ai_match', label: '✨ AI Match %' },
    { code: 'rating',   label: '★ Highest Rated' },
    { code: 'year',     label: '📅 Release Year' },
  ];

  return (
    <div className="content-wrap">
      <div className="content-inner">
        {/* ── Modern Search & Discovery Hub ── */}
        <section className="search-hub" aria-label="Movie search and filters">
          <div className="search-hub-top">
            <div className="search-input-col">
              <MovieAutocomplete
                titles={titles}
                onSelect={handleSelect}
                placeholder="Search by movie title (e.g., Inception, Vikram, Interstellar, Jailer, Leo)..."
                initialValue={selectedTitle}
              />
            </div>
            <button
              id="btn-get-recommendations"
              type="button"
              className="btn-primary search-action-btn"
              onClick={() => {
                if (selectedTitle.trim()) resolveMovieId(selectedTitle);
              }}
              title="Generate recommendations for current input"
            >
              ✦ Get Recommendations
            </button>
          </div>

          {/* Refined Filter Toolbar with Custom Styled Controls */}
          <div className="search-hub-filters">
            <div className="filter-item">
              <label className="filter-label" htmlFor="lang-filter">Language</label>
              <div className="custom-select-wrap">
                <select
                  id="lang-filter"
                  className="custom-select"
                  value={langFilter}
                  onChange={e => {
                    setLangFilter(e.target.value);
                    if (selectedMovieId) fetchRecs(selectedMovieId);
                  }}
                  aria-label="Filter recommendations by language"
                >
                  {LANGUAGES.map(l => (
                    <option key={l.code} value={l.code}>{l.label}</option>
                  ))}
                </select>
                <span className="select-arrow" aria-hidden="true">▾</span>
              </div>
            </div>

            <div className="filter-item">
              <label className="filter-label" htmlFor="genre-filter">Genre</label>
              <div className="custom-select-wrap">
                <select
                  id="genre-filter"
                  className="custom-select"
                  value={genreFilter}
                  onChange={e => {
                    setGenreFilter(e.target.value);
                    if (selectedMovieId) fetchRecs(selectedMovieId);
                  }}
                  aria-label="Filter recommendations by genre"
                >
                  <option value="all">All Genres</option>
                  {genres.map(g => (
                    <option key={g} value={g}>{g}</option>
                  ))}
                </select>
                <span className="select-arrow" aria-hidden="true">▾</span>
              </div>
            </div>

            <div className="filter-item">
              <label className="filter-label" htmlFor="top-k">Result Count</label>
              <div className="custom-select-wrap">
                <select
                  id="top-k"
                  className="custom-select"
                  value={topK}
                  onChange={e => setTopK(Number(e.target.value))}
                  aria-label="Number of recommendations to display"
                >
                  <option value={5}>5 Recommendations</option>
                  <option value={10}>10 Recommendations</option>
                  <option value={15}>15 Recommendations</option>
                  <option value={20}>20 Recommendations</option>
                </select>
                <span className="select-arrow" aria-hidden="true">▾</span>
              </div>
            </div>

            {selectedMeta && (
              <div className="filter-item filter-reset-wrap">
                <button
                  type="button"
                  className="btn-clear-selection"
                  onClick={handleClearSelection}
                  title="Clear selected movie and view featured catalog"
                >
                  ✕ Clear Selection
                </button>
              </div>
            )}
          </div>
        </section>

        {error && (
          <div className="alert alert-error" role="alert" style={{ marginTop: 14 }}>
            <span className="alert-icon">⚠️</span>
            <div>{error}</div>
          </div>
        )}

        {loadingMeta && (
          <div className="loading-row">
            <span className="spinner" /> Loading movie details &amp; computing feature vectors…
          </div>
        )}

        {/* ── Selected Movie Spotlight Card ── */}
        {selectedMeta && !loadingMeta && (
          <SelectedHero
            movie={selectedMeta}
            onRecommend={() => fetchRecs(selectedMovieId)}
            onOpenDetails={(m) => setDetailsModalMovie(m)}
            onExplorePerson={handleExplorePerson}
          />
        )}

        {/* ── Recommendations Section ── */}
        {selectedMeta && !loadingRecs && recommendations.length > 0 && (
          <div className="recommendations-section">
            <div className="rec-section-header">
              <div className="rec-header-titles">
                <h2 className="rec-section-title">
                  AI Recommendations for &ldquo;{selectedMeta.title}&rdquo;
                </h2>
                <p className="rec-section-sub">
                  Ranked by Content-Based Cosine Similarity over 10,029 titles across plot, genre, cast &amp; semantic features.
                </p>
              </div>

              {/* Custom Sort Chips */}
              <div className="sort-bar">
                <span className="sort-label">Order by:</span>
                {SORT_OPTS.map(opt => (
                  <button
                    key={opt.code}
                    id={`sort-${opt.code}`}
                    type="button"
                    className={`sort-chip${sortBy === opt.code ? ' active' : ''}`}
                    onClick={() => setSortBy(opt.code)}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            <MovieList
              movies={recommendations}
              selectedTitle={selectedMeta?.title}
              onPivot={handlePivot}
              onOpenDetails={(m) => setDetailsModalMovie(m)}
            />
          </div>
        )}

        {loadingRecs && (
          <div className="loading-row">
            <span className="spinner" /> Generating cosine-similarity recommendations…
          </div>
        )}

        {!loadingRecs && selectedMeta && recommendations.length === 0 && !error && (
          <div className="empty-state">
            <div className="empty-icon">🔍</div>
            <h3>No matching recommendations found</h3>
            <p>Try switching to &quot;All Languages&quot; or selecting a broader genre.</p>
          </div>
        )}

        {/* ── Personalized Recommendations (Logged In) ── */}
        {!selectedMeta && user && personalized.length > 0 && (
          <section className="personalized-section" aria-label="Personalized AI Recommendations">
            <div className="showcase-header">
              <div className="showcase-heading-group">
                <div className="personalized-badge">✦ TAILORED FOR YOU</div>
                <h2 className="showcase-title">Because of What You Like</h2>
                <p className="showcase-subtitle">
                  {personalizedMsg || 'Intelligently derived from your saved movies and preferences.'}
                </p>
              </div>
            </div>
            <div className="featured-grid">
              {personalized.map(m => (
                <div key={m.id} className="personalized-card-wrapper">
                  {m.because_reason && (
                    <div className="because-reason-banner">
                      <span>💡</span> {m.because_reason}
                    </div>
                  )}
                  <FeaturedCard
                    movie={m}
                    onSelect={handleFeaturedSelect}
                    onOpenDetails={(mov) => setDetailsModalMovie(mov)}
                  />
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ── Featured Discoveries (Displayed when no movie is currently selected) ── */}
        {!selectedMeta && !loadingMeta && (
          <section className="showcase-section" aria-label="Curated movie showcase">
            <div className="showcase-header">
              <div className="showcase-heading-group">
                <h2 className="showcase-title">Curated Discoveries &amp; Featured Cinema</h2>
                <p className="showcase-subtitle">
                  Click any film or choose &ldquo;Get Recommendations&rdquo; to instantly uncover intelligent semantic matches.
                </p>
              </div>

              <div className="showcase-tabs" role="tablist">
                <button
                  type="button"
                  className={`showcase-tab${showcaseTab === 'trending' ? ' active' : ''}`}
                  onClick={() => setShowcaseTab('trending')}
                >
                  🔥 Trending Global
                </button>
                <button
                  type="button"
                  className={`showcase-tab${showcaseTab === 'indian' ? ' active' : ''}`}
                  onClick={() => setShowcaseTab('indian')}
                >
                  🇮🇳 Indian Cinema
                </button>
                <button
                  type="button"
                  className={`showcase-tab${showcaseTab === 'top_rated' ? ' active' : ''}`}
                  onClick={() => setShowcaseTab('top_rated')}
                >
                  ⭐ Top Rated
                </button>
              </div>
            </div>

            {loadingShowcase && (
              <div className="loading-row">
                <span className="spinner" /> Loading curated showcase…
              </div>
            )}

            {!loadingShowcase && showcase.length > 0 && (
              <div className="featured-grid">
                {showcase.map(m => (
                  <FeaturedCard
                    key={m.id}
                    movie={m}
                    onSelect={handleFeaturedSelect}
                    onOpenDetails={(mov) => setDetailsModalMovie(mov)}
                  />
                ))}
              </div>
            )}
          </section>
        )}
      </div>

      {/* Global Movie Details Modal */}
      {detailsModalMovie && (
        <MovieDetailsModal
          movie={detailsModalMovie}
          movieId={detailsModalMovie.id}
          region={region}
          onClose={() => setDetailsModalMovie(null)}
          onPivot={handlePivot}
          onExplorePerson={handleExplorePerson}
        />
      )}

      {/* Global Person Profile Modal */}
      {personModal && (
        <PersonModal
          personId={personModal.id}
          personName={personModal.name}
          onClose={() => setPersonModal(null)}
          onExplorePerson={handleExplorePerson}
          onOpenMovie={(mov) => setDetailsModalMovie(mov)}
        />
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Explore Catalog Page — Advanced Filtering (Actor, Year Era, Rating, Lang, Genre)
// ─────────────────────────────────────────────────────────────────────────────
export function ExplorePage({ region, onMovieSelect, initialActorFilter = '' }) {
  const [movies, setMovies] = useState([]);
  const [genres, setGenres] = useState([]);
  const [total, setTotal] = useState(0);
  const [lang, setLang] = useState('all');
  const [genre, setGenre] = useState('all');
  const [actor, setActor] = useState(initialActorFilter);
  const [eraIdx, setEraIdx] = useState(0);
  const [ratingIdx, setRatingIdx] = useState(0);
  const [sortBy, setSortBy] = useState('popularity');
  const [query, setQuery] = useState('');
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [detailsModalMovie, setDetailsModalMovie] = useState(null);
  const LIMIT = 24;

  useEffect(() => {
    apiGetGenres().then(d => setGenres(d.genres || [])).catch(() => {});
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    const era = ERA_FILTERS[eraIdx];
    const rat = RATING_FILTERS[ratingIdx];

    const fn = query.trim() || actor.trim() || rat.min || era.from
      ? apiSearch({
          q: query,
          language: lang,
          genre,
          actor,
          min_rating: rat.min,
          year_from: era.from,
          year_to: era.to,
          sort_by: sortBy,
          limit: LIMIT,
          offset,
        })
      : apiExplore({
          language: lang,
          genre,
          actor,
          min_rating: rat.min,
          year_from: era.from,
          year_to: era.to,
          sort_by: sortBy,
          limit: LIMIT,
          offset,
        });

    fn.then(d => {
      setMovies(d.movies || []);
      setTotal(d.total || 0);
    })
      .catch(e => { console.error('Explore load error', e); setError(e.message || 'Failed to load movies'); })
      .finally(() => setLoading(false));
  }, [query, lang, genre, actor, eraIdx, ratingIdx, sortBy, offset]);

  useEffect(() => { setOffset(0); }, [query, lang, genre, actor, eraIdx, ratingIdx, sortBy]);
  useEffect(() => { load(); }, [load]);

  const handleSelect = (movie) => {
    const label = movie.release_year > 0 ? `${movie.title} (${movie.release_year})` : movie.title;
    onMovieSelect(movie.id, label);
  };

  const handleExplorePerson = (personName) => {
    setActor(personName);
    setQuery('');
    setOffset(0);
  };

  return (
    <div className="content-wrap">
      <div className="content-inner">
        {/* Search & Filter Toolbar */}
        <div className="search-hub" style={{ marginTop: 14 }}>
          <div className="search-hub-top">
            <div className="search-input-col">
              <div className="search-input-inner">
                <span className="search-icon" aria-hidden="true">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="11" cy="11" r="8" />
                    <line x1="21" y1="21" x2="16.65" y2="16.65" />
                  </svg>
                </span>
                <input
                  id="explore-search"
                  className="search-input"
                  placeholder="Filter catalog by movie title or actor (e.g., Vikram, Kamal Haasan, Inception, Interstellar)…"
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                />
                {query && (
                  <button type="button" className="search-clear" onClick={() => setQuery('')}>
                    ×
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Filter Bar with Language, Genre, Era, Rating, Actor, Sort */}
          <div className="search-hub-filters">
            <div className="filter-item">
              <label className="filter-label" htmlFor="explore-lang">Language</label>
              <div className="custom-select-wrap">
                <select
                  id="explore-lang"
                  className="custom-select"
                  value={lang}
                  onChange={e => setLang(e.target.value)}
                >
                  {LANGUAGES.map(l => (
                    <option key={l.code} value={l.code}>{l.label}</option>
                  ))}
                </select>
                <span className="select-arrow" aria-hidden="true">▾</span>
              </div>
            </div>

            <div className="filter-item">
              <label className="filter-label" htmlFor="explore-genre">Genre</label>
              <div className="custom-select-wrap">
                <select
                  id="explore-genre"
                  className="custom-select"
                  value={genre}
                  onChange={e => setGenre(e.target.value)}
                >
                  <option value="all">All Genres</option>
                  {genres.map(g => (
                    <option key={g} value={g}>{g}</option>
                  ))}
                </select>
                <span className="select-arrow" aria-hidden="true">▾</span>
              </div>
            </div>

            <div className="filter-item">
              <label className="filter-label" htmlFor="explore-era">Release Era</label>
              <div className="custom-select-wrap">
                <select
                  id="explore-era"
                  className="custom-select"
                  value={eraIdx}
                  onChange={e => setEraIdx(Number(e.target.value))}
                >
                  {ERA_FILTERS.map((ef, idx) => (
                    <option key={ef.label} value={idx}>{ef.label}</option>
                  ))}
                </select>
                <span className="select-arrow" aria-hidden="true">▾</span>
              </div>
            </div>

            <div className="filter-item">
              <label className="filter-label" htmlFor="explore-rating">Min Rating</label>
              <div className="custom-select-wrap">
                <select
                  id="explore-rating"
                  className="custom-select"
                  value={ratingIdx}
                  onChange={e => setRatingIdx(Number(e.target.value))}
                >
                  {RATING_FILTERS.map((rf, idx) => (
                    <option key={rf.label} value={idx}>{rf.label}</option>
                  ))}
                </select>
                <span className="select-arrow" aria-hidden="true">▾</span>
              </div>
            </div>

            <div className="filter-item">
              <label className="filter-label" htmlFor="explore-sort">Sort Order</label>
              <div className="custom-select-wrap">
                <select
                  id="explore-sort"
                  className="custom-select"
                  value={sortBy}
                  onChange={e => setSortBy(e.target.value)}
                >
                  <option value="popularity">Most Popular</option>
                  <option value="rating">Highest Rated</option>
                  <option value="newest">Newest Release</option>
                  <option value="oldest">Oldest Release</option>
                </select>
                <span className="select-arrow" aria-hidden="true">▾</span>
              </div>
            </div>

            {actor && (
              <div className="filter-item filter-reset-wrap">
                <button
                  type="button"
                  className="btn-clear-selection"
                  onClick={() => setActor('')}
                  title="Clear actor filter"
                >
                  ✕ Actor: {actor}
                </button>
              </div>
            )}
          </div>
        </div>

        {loading && (
          <div className="loading-row">
            <span className="spinner" /> Loading movie catalog…
          </div>
        )}
        {error && (
          <div className="alert alert-error" role="alert" style={{ marginTop: 14 }}>
            <span className="alert-icon">⚠️</span>
            <div>{error}</div>
          </div>
        )}

        {!loading && (
          <div className="explore-count">
            {total > 0
              ? `Displaying ${Math.min(LIMIT, movies.length)} of ${total.toLocaleString()} catalog titles`
              : 'No movies matching current filters'}
          </div>
        )}

        {!loading && movies.length > 0 && (
          <div className="featured-grid">
            {movies.map(m => (
              <FeaturedCard
                key={m.id}
                movie={m}
                onSelect={handleSelect}
                onOpenDetails={(mov) => setDetailsModalMovie(mov)}
              />
            ))}
          </div>
        )}

        {!loading && movies.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon">🎬</div>
            <h3>No movies found</h3>
            <p>Try modifying your title search, actor name, or filter criteria.</p>
          </div>
        )}

        {total > LIMIT && (
          <div className="pagination">
            <button
              id="prev-page"
              className="btn-secondary"
              onClick={() => setOffset(Math.max(0, offset - LIMIT))}
              disabled={offset === 0}
            >
              ← Previous
            </button>
            <span className="page-info">
              Page {Math.floor(offset / LIMIT) + 1} of {Math.ceil(total / LIMIT)}
            </span>
            <button
              id="next-page"
              className="btn-secondary"
              onClick={() => setOffset(offset + LIMIT)}
              disabled={offset + LIMIT >= total}
            >
              Next →
            </button>
          </div>
        )}
      </div>

      {detailsModalMovie && (
        <MovieDetailsModal
          movie={detailsModalMovie}
          movieId={detailsModalMovie.id}
          region={region}
          onClose={() => setDetailsModalMovie(null)}
          onPivot={handleSelect}
          onExplorePerson={handleExplorePerson}
        />
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Watchlist & Watched History Page
// ─────────────────────────────────────────────────────────────────────────────
export function WatchlistPage({ region, onMovieSelect }) {
  const { user } = useAuth();
  const { addToast } = useToast();
  const { removeFromWatchlist, removeFromWatched } = useWatchlist();
  const [tab, setTab] = useState('watchlist'); // 'watchlist' or 'watched'
  const [watchlistMovies, setWatchlistMovies] = useState([]);
  const [watchedMovies, setWatchedMovies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [detailsModalMovie, setDetailsModalMovie] = useState(null);

  const loadData = useCallback(() => {
    if (!user) return;
    setLoading(true);
    Promise.all([
      apiGetWatchlist(user.id, region).catch(() => ({ movies: [] })),
      apiGetWatched(user.id, region).catch(() => ({ movies: [] })),
    ])
      .then(([wlData, watchedData]) => {
        setWatchlistMovies(wlData.movies || []);
        setWatchedMovies(watchedData.movies || []);
      })
      .finally(() => setLoading(false));
  }, [user, region]);

  useEffect(() => { loadData(); }, [loadData]);

  const handleRec = (movie) => {
    const label = movie.release_year > 0 ? `${movie.title} (${movie.release_year})` : movie.title;
    onMovieSelect(movie.id, label);
  };

  const handleRemoveWl = async (m) => {
    try {
      await removeFromWatchlist(m.id);
      setWatchlistMovies(prev => prev.filter(x => x.id !== m.id));
      addToast(`Removed "${m.title}" from watchlist`, 'info');
    } catch {
      addToast('Error removing movie', 'error');
    }
  };

  const handleRemoveWatched = async (m) => {
    try {
      await apiRemoveWatched(user.id, m.id);
      setWatchedMovies(prev => prev.filter(x => x.id !== m.id));
      addToast(`Removed "${m.title}" from watched history`, 'info');
    } catch {
      addToast('Error removing movie', 'error');
    }
  };

  if (!user) return (
    <div className="content-wrap">
      <div className="content-inner">
        <div className="empty-state" style={{ marginTop: 24 }}>
          <div className="empty-icon">🔖</div>
          <h3>Sign in to access your Watchlist &amp; History</h3>
          <p>Create a free CineWise account to curate your personal collection and receive tailored AI matches.</p>
        </div>
      </div>
    </div>
  );

  const currentList = tab === 'watchlist' ? watchlistMovies : watchedMovies;

  return (
    <div className="content-wrap">
      <div className="content-inner">
        {/* Watchlist / Watched Tab Switcher */}
        <div className="watchlist-tabs" role="tablist" style={{ marginTop: 18 }}>
          <button
            type="button"
            className={`watchlist-tab${tab === 'watchlist' ? ' active' : ''}`}
            onClick={() => setTab('watchlist')}
          >
            🔖 Saved Watchlist ({watchlistMovies.length})
          </button>
          <button
            type="button"
            className={`watchlist-tab${tab === 'watched' ? ' active' : ''}`}
            onClick={() => setTab('watched')}
          >
            👁 Watched History ({watchedMovies.length})
          </button>
        </div>

        {loading && (
          <div className="loading-row">
            <span className="spinner" /> Loading your collection…
          </div>
        )}

        {!loading && currentList.length === 0 && (
          <div className="empty-state" style={{ marginTop: 24 }}>
            <div className="empty-icon">{tab === 'watchlist' ? '📋' : '👁'}</div>
            <h3>{tab === 'watchlist' ? 'Your Watchlist is empty' : 'No watched movies recorded yet'}</h3>
            <p>
              {tab === 'watchlist'
                ? 'Browse movies and click "+ Watchlist" to save titles for later.'
                : 'Mark movies you have seen as watched to build your personal viewing log and get smarter recommendations.'}
            </p>
          </div>
        )}

        {!loading && currentList.length > 0 && (
          <div className="recommendations-section" style={{ marginTop: 18 }}>
            <div className="rec-section-header">
              <div className="rec-header-titles">
                <h2 className="rec-section-title">
                  {tab === 'watchlist' ? 'My Saved Watchlist' : 'My Watched Movie History'}
                </h2>
                <p className="rec-section-sub">
                  {currentList.length} title{currentList.length !== 1 ? 's' : ''} in your private library
                </p>
              </div>
            </div>

            <div className="movie-list">
              {currentList.map((m, i) => (
                <div key={m.id} className="movie-row">
                  <div className="row-rank-wrap">
                    <div className="row-rank-badge">#{i + 1}</div>
                  </div>
                  <div className="row-poster-col" onClick={() => setDetailsModalMovie(m)} style={{ cursor: 'pointer' }}>
                    <Poster url={m.poster_url} title={m.title} className="row-poster-frame" />
                  </div>
                  <div className="row-info">
                    <div className="row-title-line">
                      <h3
                        className="row-title clickable"
                        onClick={() => setDetailsModalMovie(m)}
                        title={`View full details for ${m.title}`}
                      >
                        {m.title}
                      </h3>
                      {m.release_year > 0 && <span className="row-year">({m.release_year})</span>}
                    </div>
                    <div className="row-meta">
                      <StarRating rating={m.vote_average} voteCount={m.vote_count} />
                      {m.language_display && (
                        <>
                          <span className="meta-sep">·</span>
                          <LangBadge display={m.language_display} />
                        </>
                      )}
                      {m.watched_at && (
                        <>
                          <span className="meta-sep">·</span>
                          <span className="watched-date-badge">Watched on {m.watched_at.slice(0, 10)}</span>
                        </>
                      )}
                    </div>
                    {m.overview && (
                      <p className="row-synopsis">
                        {m.overview.slice(0, 180)}{m.overview.length > 180 ? '…' : ''}
                      </p>
                    )}
                    <OttRow providers={m.streaming_providers} link={m.streaming_link} />
                  </div>
                  <div className="row-actions">
                    <button
                      type="button"
                      className="row-action-btn view-details-btn"
                      onClick={() => setDetailsModalMovie(m)}
                    >
                      👁 View Details
                    </button>
                    <button
                      id={`wl-rec-${m.id}`}
                      type="button"
                      className="row-action-btn pivot-btn"
                      onClick={() => handleRec(m)}
                    >
                      ✦ Recommend From This
                    </button>
                    {tab === 'watchlist' ? (
                      <button
                        type="button"
                        className="row-action-btn btn-danger-sm"
                        onClick={() => handleRemoveWl(m)}
                        title="Remove from watchlist"
                      >
                        ✕ Remove
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="row-action-btn btn-danger-sm"
                        onClick={() => handleRemoveWatched(m)}
                        title="Remove from watched history"
                      >
                        ✕ Remove
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {detailsModalMovie && (
        <MovieDetailsModal
          movie={detailsModalMovie}
          movieId={detailsModalMovie.id}
          region={region}
          onClose={() => setDetailsModalMovie(null)}
          onPivot={onMovieSelect}
        />
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// User Profile Page — Account Info, Viewing Stats & Preferences Editor
// ─────────────────────────────────────────────────────────────────────────────
export function ProfilePage({ onLogout }) {
  const { user } = useAuth();
  const { watchlistIds } = useWatchlist();
  const { watchedIds } = useWatched();
  const { addToast } = useToast();

  const [genresList, setGenresList] = useState([]);
  const [prefLangs, setPrefLangs] = useState(['en', 'ta', 'hi']);
  const [prefGenres, setPrefGenres] = useState(['Action', 'Sci-Fi', 'Drama']);
  const [savingPrefs, setSavingPrefs] = useState(false);
  const [loadingPrefs, setLoadingPrefs] = useState(false);

  useEffect(() => {
    apiGetGenres().then(d => setGenresList(d.genres || [])).catch(() => {});
    if (user?.id) {
      setLoadingPrefs(true);
      apiGetPreferences(user.id)
        .then(d => {
          if (d.preferred_languages?.length) setPrefLangs(d.preferred_languages);
          if (d.preferred_genres?.length) setPrefGenres(d.preferred_genres);
        })
        .catch(() => {})
        .finally(() => setLoadingPrefs(false));
    }
  }, [user?.id]);

  const toggleLang = (code) => {
    if (code === 'all') return;
    setPrefLangs(prev => prev.includes(code) ? prev.filter(c => c !== code) : [...prev, code]);
  };

  const toggleGenre = (genre) => {
    setPrefGenres(prev => prev.includes(genre) ? prev.filter(g => g !== genre) : [...prev, genre]);
  };

  const handleSavePreferences = async () => {
    if (!user?.id) return;
    setSavingPrefs(true);
    try {
      await apiSavePreferences(user.id, prefLangs, prefGenres);
      addToast('Preferences saved successfully! AI recommendations updated.', 'success');
    } catch {
      addToast('Error saving preferences', 'error');
    } finally {
      setSavingPrefs(false);
    }
  };

  if (!user) return (
    <div className="content-wrap">
      <div className="content-inner">
        <div className="empty-state" style={{ marginTop: 24 }}>
          <h3>Sign in to view your profile</h3>
        </div>
      </div>
    </div>
  );

  return (
    <div className="content-wrap">
      <div className="content-inner">
        {/* Statistics Cards */}
        <div className="stat-grid">
          <div className="stat-card">
            <div className="stat-val">{user.name.split(' ')[0]}</div>
            <div className="stat-lbl">Account Member</div>
          </div>
          <div className="stat-card">
            <div className="stat-val">{watchlistIds.size}</div>
            <div className="stat-lbl">Watchlist Titles</div>
          </div>
          <div className="stat-card">
            <div className="stat-val">{watchedIds.size}</div>
            <div className="stat-lbl">Watched Movies</div>
          </div>
          <div className="stat-card">
            <div className="stat-val">{user.created_at?.slice(0, 10) || 'Active'}</div>
            <div className="stat-lbl">Registered Date</div>
          </div>
        </div>

        {/* Personalized Movie Preferences Card */}
        <div className="account-card" style={{ marginTop: 20 }}>
          <div className="account-card-header">
            <h3>Personal Cinema Preferences</h3>
            <span className="card-badge-gold">AI TUNING</span>
          </div>
          <p className="account-card-sub">
            Customize your preferred movie languages and genres to enhance personalized recommendations.
          </p>

          {loadingPrefs && <div className="loading-row"><span className="spinner"></span> Loading preferences…</div>}

          {!loadingPrefs && (
            <>
              {/* Preferred Languages */}
              <div className="pref-group">
                <label className="pref-label">Preferred Languages</label>
                <div className="pref-chips">
                  {LANGUAGES.filter(l => l.code !== 'all').map(l => {
                    const active = prefLangs.includes(l.code);
                    return (
                      <button
                        key={l.code}
                        type="button"
                        className={`pref-chip${active ? ' active' : ''}`}
                        onClick={() => toggleLang(l.code)}
                      >
                        {active ? '✓ ' : '+ '}{l.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Preferred Genres */}
              <div className="pref-group" style={{ marginTop: 16 }}>
                <label className="pref-label">Preferred Genres</label>
                <div className="pref-chips">
                  {genresList.map(g => {
                    const active = prefGenres.includes(g);
                    return (
                      <button
                        key={g}
                        type="button"
                        className={`pref-chip${active ? ' active' : ''}`}
                        onClick={() => toggleGenre(g)}
                      >
                        {active ? '✓ ' : '+ '}{g}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div style={{ marginTop: 20 }}>
                <button
                  id="btn-save-preferences"
                  type="button"
                  className="btn-primary"
                  onClick={handleSavePreferences}
                  disabled={savingPrefs}
                >
                  {savingPrefs ? 'Saving Preferences…' : 'Save Preferences'}
                </button>
              </div>
            </>
          )}
        </div>

        {/* Account Information Card */}
        <div className="account-card" style={{ marginTop: 20 }}>
          <h3>Account Information</h3>
          <div className="account-detail">
            <div><strong>Full Name:</strong> {user.name}</div>
            <div><strong>Email Address:</strong> {user.email}</div>
            <div><strong>Account ID:</strong> #{user.id}</div>
            <div><strong>Member Since:</strong> {user.created_at}</div>
          </div>
          <div style={{ marginTop: 20 }}>
            <button id="btn-logout" className="btn-danger" onClick={onLogout}>
              Sign Out
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
