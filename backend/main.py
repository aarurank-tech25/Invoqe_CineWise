"""
CineWise FastAPI Backend
========================
Exposes the existing TF-IDF + Cosine Similarity recommendation engine,
TMDB metadata, and SQLite auth as a REST API consumed by the React frontend.
"""

import os
import sys
import logging
from typing import Optional
from contextlib import asynccontextmanager
import pandas as pd

# ---------------------------------------------------------------------------
# Load .env file early so TMDB_API_KEY is available via os.environ
# ---------------------------------------------------------------------------
def _load_dotenv():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and not os.environ.get(k):
                    os.environ[k] = v

_load_dotenv()

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Path setup so src.* modules resolve correctly
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import asyncio
from src.recommender import MovieRecommender
from src.movie_metadata import (
    get_movie_metadata,
    get_batch_movie_metadata,
    get_api_key,
    clear_metadata_cache,
    SUPPORTED_INDIAN_LANGUAGES,
    fetch_person_details,
    search_tmdb_person,
    search_tmdb_movies_multi,
    discover_catalog_movies,
)
from src.database import (
    init_db,
    register_user,
    login_user,
    add_favorite,
    remove_favorite,
    get_favorites,
    get_favorite_count,
    create_password_reset_token,
    verify_password_reset_token,
    reset_password_with_token,
    add_watched,
    remove_watched,
    get_watched,
    get_watched_ids,
    is_watched,
    get_watched_count,
    get_user_preferences,
    save_user_preferences,
)
from backend.email_service import (
    send_password_reset_email,
    is_smtp_configured,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cinewise")

_engine: Optional[MovieRecommender] = None


async def _periodic_catalog_refresh():
    """Optional scheduled background catalog refresh."""
    refresh_hours = int(os.environ.get("CATALOG_REFRESH_INTERVAL_HOURS", 0))
    if refresh_hours <= 0:
        return
    logger.info(f"Catalog periodic refresh scheduled every {refresh_hours} hours")
    while True:
        await asyncio.sleep(refresh_hours * 3600)
        try:
            resolved_key = _get_api_key()
            if resolved_key:
                logger.info("Executing scheduled catalog refresh...")
                discover_catalog_movies(api_key=resolved_key, pages_per_language=2)
                if _engine:
                    _engine.reload()
                logger.info(f"Scheduled refresh complete: {len(_engine.df) if _engine else 0} movies indexed")
        except Exception as e:
            logger.error(f"Scheduled catalog refresh error: {e}")


def get_engine() -> MovieRecommender:
    global _engine
    if _engine is None:
        raise HTTPException(status_code=503, detail="Recommendation engine not yet loaded")
    return _engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _engine
    logger.info("Loading movie recommendation engine...")
    init_db()
    _engine = MovieRecommender()
    logger.info(f"Engine ready: {len(_engine.df)} movies indexed")
    refresh_task = asyncio.create_task(_periodic_catalog_refresh())
    yield
    refresh_task.cancel()
    logger.info("Shutting down CineWise backend")


app = FastAPI(title="CineWise API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class RecommendRequest(BaseModel):
    movie_id: int
    top_k: int = 10
    language_filter: Optional[str] = None
    genre_filter: Optional[str] = None
    sort_by: Optional[str] = "ai_match"


class AuthRegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class AuthLoginRequest(BaseModel):
    email: str
    password: str


class WatchlistRequest(BaseModel):
    user_id: int
    movie_id: int


class WatchedRequest(BaseModel):
    user_id: int
    movie_id: int
    rating: Optional[float] = None


class PreferencesRequest(BaseModel):
    user_id: Optional[int] = None
    languages: Optional[list] = None
    genres: Optional[list] = None
    preferred_languages: Optional[list] = None
    preferred_genres: Optional[list] = None


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str
    confirm_password: Optional[str] = None


class CatalogRefreshRequest(BaseModel):
    languages: Optional[list] = None
    pages_per_language: int = 2
    admin_key: Optional[str] = None



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _get_api_key(override: str = "") -> Optional[str]:
    return get_api_key(override)


def _enrich_meta(meta: dict) -> dict:
    meta.setdefault("poster_url", None)
    meta.setdefault("overview", "")
    meta.setdefault("genres", [])
    meta.setdefault("genre_str", "")
    meta.setdefault("director", "")
    meta.setdefault("directors", [])
    meta.setdefault("writers", [])
    meta.setdefault("writer_str", "")
    meta.setdefault("cast", [])
    meta.setdefault("cast_names", [])
    meta.setdefault("tagline", "")
    meta.setdefault("runtime", 0)
    meta.setdefault("certification", "")
    meta.setdefault("vote_average", 0.0)
    meta.setdefault("vote_count", 0)
    meta.setdefault("release_year", 0)
    meta.setdefault("original_language", "en")
    meta.setdefault("streaming", {})
    meta.setdefault("similarity_score", 0.0)
    meta.setdefault("trailer_url", None)
    meta.setdefault("trailer_key", None)
    meta.setdefault("trailer_name", None)
    meta.setdefault("backdrop_url", None)

    raw_lang = str(meta.get("original_language", "")).lower()
    meta["language_display"] = SUPPORTED_INDIAN_LANGUAGES.get(raw_lang, raw_lang.upper())

    streaming = meta.get("streaming") or {}
    flatrate = streaming.get("flatrate", []) if streaming else []
    free = streaming.get("free", []) if streaming else []
    rent = streaming.get("rent", []) if streaming else []
    buy = streaming.get("buy", []) if streaming else []
    providers = streaming.get("providers", []) if streaming else []
    meta["streaming_providers"] = providers[:6]
    meta["streaming_flatrate"] = flatrate
    meta["streaming_free"] = free
    meta["streaming_rent"] = rent[:3]
    meta["streaming_buy"] = buy[:3]
    meta["streaming_link"] = streaming.get("link", "") if streaming else ""
    meta["streaming_available"] = bool(providers)
    meta["ai_match_pct"] = round(float(meta.get("similarity_score", 0)) * 100, 1)

    return meta


def _extract_insights(selected: dict, rec: dict) -> dict:
    sel_genres = set(g.lower().strip() for g in selected.get("genres", []) if g)
    rec_genres = set(g.lower().strip() for g in rec.get("genres", []) if g)
    shared_genres = [g.title() for g in (sel_genres & rec_genres)]

    sel_lang = str(selected.get("original_language", "")).lower()
    rec_lang = str(rec.get("original_language", "")).lower()
    same_lang = sel_lang == rec_lang and bool(sel_lang)

    stopwords = {
        "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "with",
        "by", "from", "of", "about", "is", "are", "was", "were", "be", "been",
        "have", "has", "this", "that", "it", "he", "she", "they", "who", "which",
        "movie", "film", "story", "life", "one", "two", "man", "woman", "time",
        "world", "young", "must", "take", "make", "get", "see", "come", "go",
    }

    def tokenize(text: str) -> set:
        clean = "".join([c.lower() if c.isalnum() else " " for c in (text or "")])
        return {w for w in clean.split() if len(w) > 3 and w not in stopwords}

    shared_themes = sorted(tokenize(selected.get("overview", "")) & tokenize(rec.get("overview", "")))[:3]

    return {
        "shared_genres": shared_genres[:3],
        "same_language": same_lang,
        "shared_themes": shared_themes,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    engine = get_engine()
    return {
        "status": "ok",
        "movies_indexed": len(engine.df),
        "api_configured": bool(_get_api_key()),
    }


@app.get("/api/titles")
def get_titles(language: str = Query(default="all")):
    engine = get_engine()
    lang_filter = None if language.lower() == "all" else language
    titles = engine.get_all_titles(language_filter=lang_filter)
    return {"titles": titles, "count": len(titles)}


@app.get("/api/search")
def search_movies(
    q: str = Query(default=""),
    language: str = Query(default="all"),
    genre: str = Query(default="all"),
    actor: str = Query(default=""),
    min_rating: Optional[float] = Query(default=None),
    year_from: Optional[int] = Query(default=None),
    year_to: Optional[int] = Query(default=None),
    sort_by: str = Query(default="popularity"),
    limit: int = Query(default=24, le=100),
    offset: int = Query(default=0),
    api_key: str = Query(default=""),
):
    engine = get_engine()
    resolved_key = _get_api_key(api_key)
    df = engine.df.copy()

    if q.strip():
        term = q.strip()
        title_mask = df["title"].astype(str).str.contains(term, case=False, na=False)
        cast_mask = pd.Series(False, index=df.index)
        if "cast" in df.columns:
            cast_mask = df["cast"].astype(str).str.contains(term, case=False, na=False)
        director_mask = pd.Series(False, index=df.index)
        if "director" in df.columns:
            director_mask = df["director"].astype(str).str.contains(term, case=False, na=False)
        df = df[title_mask | cast_mask | director_mask]

    if actor.strip():
        act_term = actor.strip()
        act_mask = pd.Series(False, index=df.index)
        if "cast" in df.columns:
            act_mask = df["cast"].astype(str).str.contains(act_term, case=False, na=False)
        # Also check TMDB person credits if key available
        if not act_mask.any() and resolved_key:
            persons = search_tmdb_person(act_term, api_key=resolved_key)
            if persons:
                p_id = persons[0].get("id")
                if p_id:
                    p_info = fetch_person_details(p_id, api_key=resolved_key)
                    if p_info and p_info.get("known_for"):
                        kf_ids = {m["id"] for m in p_info["known_for"]}
                        act_mask = df["id"].isin(kf_ids)
        if act_mask.any():
            df = df[act_mask]

    if language.lower() != "all":
        df = df[df["original_language"] == language.lower()]

    if genre.lower() != "all":
        df = df[df["genre"].astype(str).str.contains(genre, case=False, na=False)]

    if min_rating is not None and min_rating > 0:
        df = df[df["vote_average"] >= float(min_rating)]

    if year_from is not None and year_from > 0:
        df = df[df["release_year"] >= int(year_from)]

    if year_to is not None and year_to > 0:
        df = df[df["release_year"] <= int(year_to)]

    sort_map = {
        "popularity": ("popularity", False),
        "rating": ("vote_average", False),
        "newest": ("release_year", False),
        "oldest": ("release_year", True),
    }
    col, asc = sort_map.get(sort_by, ("popularity", False))
    df = df.sort_values(by=col, ascending=asc)

    total = len(df)
    page_df = df.iloc[offset: offset + limit]

    results = []
    for _, row in page_df.iterrows():
        meta = get_movie_metadata(int(row["id"]), local_data=row, api_key=resolved_key, region="IN")
        enriched = _enrich_meta(meta)
        if min_rating is not None and min_rating > 0 and float(enriched.get("vote_average", 0)) < float(min_rating):
            continue
        results.append(enriched)

    # Dynamic fallback: if catalog returned 0 results and search query exists, discover via TMDB
    if total == 0 and q.strip() and resolved_key:
        tmdb_hits = search_tmdb_movies_multi(q.strip(), api_key=resolved_key, limit=limit)
        if tmdb_hits:
            return {"total": len(tmdb_hits), "offset": 0, "limit": limit, "movies": [_enrich_meta(m) for m in tmdb_hits]}

    return {"total": total, "offset": offset, "limit": limit, "movies": results}


@app.get("/api/movie/{movie_id}")
def get_movie(movie_id: int, api_key: str = Query(default=""), region: str = Query(default="IN")):
    engine = get_engine()
    resolved_key = _get_api_key(api_key)
    match = engine.df[engine.df["id"] == movie_id]
    if not match.empty:
        row = match.iloc[0]
        meta = get_movie_metadata(movie_id, local_data=row, api_key=resolved_key, region=region)
        return _enrich_meta(meta)

    # Fallback to TMDB for uncataloged movie
    meta = get_movie_metadata(movie_id, api_key=resolved_key, region=region)
    if meta and (meta.get("title") or meta.get("overview")):
        return _enrich_meta(meta)

    raise HTTPException(status_code=404, detail=f"Movie id {movie_id} not found")


@app.post("/api/recommend")
def recommend(req: RecommendRequest, api_key: str = Query(default=""), region: str = Query(default="IN")):
    engine = get_engine()
    resolved_key = _get_api_key(api_key)

    match = engine.df[engine.df["id"] == req.movie_id]
    lang_filter = None if (not req.language_filter or req.language_filter.lower() == "all") else req.language_filter
    extra_k = req.top_k * 4 if req.genre_filter and req.genre_filter.lower() != "all" else req.top_k

    if not match.empty:
        movie_index = match.index[0]
        movie_row = match.iloc[0]
        selected_meta = get_movie_metadata(
            req.movie_id, local_data=movie_row, api_key=resolved_key, region=region
        )
        selected_meta = _enrich_meta(selected_meta)
        recs_df = engine.recommend(movie_index=movie_index, top_k=extra_k, language_filter=lang_filter)
    else:
        # Movie not in local CSV: fetch its metadata from TMDB and use content-based recommend_external
        selected_meta = get_movie_metadata(req.movie_id, api_key=resolved_key, region=region)
        if not selected_meta or not (selected_meta.get("title") or selected_meta.get("overview")):
            raise HTTPException(status_code=404, detail=f"Movie id {req.movie_id} not found in catalog or TMDB")
        selected_meta = _enrich_meta(selected_meta)
        recs_df = engine.recommend_external(
            selected_meta, top_k=extra_k, language_filter=lang_filter, genre_filter=req.genre_filter
        )

    if req.genre_filter and req.genre_filter.lower() != "all" and not recs_df.empty:
        recs_df = recs_df[recs_df["genre"].str.contains(req.genre_filter, case=False, na=False)]
        recs_df = recs_df.head(req.top_k)

    if recs_df.empty:
        return {"selected": selected_meta, "recommendations": [], "total": 0}

    rec_records = recs_df.to_dict(orient="records")
    recs_meta_list = get_batch_movie_metadata(rec_records, api_key=resolved_key, region=region)

    enriched = []
    for i, meta in enumerate(recs_meta_list):
        meta["rank"] = i + 1
        meta = _enrich_meta(meta)
        meta["ai_insights"] = _extract_insights(selected_meta, meta)
        enriched.append(meta)

    if req.sort_by == "rating":
        enriched.sort(key=lambda m: float(m.get("vote_average", 0)), reverse=True)
    elif req.sort_by == "year":
        enriched.sort(key=lambda m: int(m.get("release_year", 0)), reverse=True)

    return {
        "selected": selected_meta,
        "recommendations": enriched,
        "total": len(enriched),
    }


@app.post("/api/admin/catalog/refresh")
def admin_refresh_catalog(
    req: Optional[CatalogRefreshRequest] = None,
    api_key: str = Query(default=""),
):
    """
    Admin catalog discovery refresh.
    Discovers new movies across Tamil, Telugu, Malayalam, Kannada, Hindi, English, and international languages.
    Caches posters, eliminates duplicates by TMDB ID, and refreshes the recommendation engine.
    """
    resolved_key = _get_api_key(api_key)
    if not resolved_key:
        raise HTTPException(status_code=400, detail="TMDB API key not configured")

    req_data = req or CatalogRefreshRequest()
    env_admin_key = os.environ.get("CINEWISE_ADMIN_KEY")
    if env_admin_key and req_data.admin_key != env_admin_key:
        raise HTTPException(status_code=403, detail="Invalid admin credentials")

    langs = req_data.languages or ["ta", "te", "ml", "kn", "hi", "en"]
    pages = max(1, min(req_data.pages_per_language, 5))

    logger.info(f"Starting catalog refresh for languages: {langs}, pages={pages}")
    summary = discover_catalog_movies(
        languages=langs,
        pages_per_language=pages,
        api_key=resolved_key,
    )

    # Reload recommender engine to index new movies into TF-IDF matrix
    engine = get_engine()
    engine.reload()
    summary["movies_indexed"] = len(engine.df)
    return summary


@app.get("/api/catalog/stats")
def get_catalog_stats():
    """Return catalog metadata, language breakdown, and total indexed count."""
    engine = get_engine()
    df = engine.df
    lang_counts = df["original_language"].value_counts().to_dict()
    return {
        "total_movies": len(df),
        "unique_genres": sorted(df["genre"].dropna().unique().tolist()[:25]),
        "language_breakdown": lang_counts,
        "api_configured": bool(_get_api_key()),
    }



@app.get("/api/explore")
def explore(
    language: str = Query(default="all"),
    genre: str = Query(default="all"),
    actor: str = Query(default=""),
    min_rating: Optional[float] = Query(default=None),
    year_from: Optional[int] = Query(default=None),
    year_to: Optional[int] = Query(default=None),
    sort_by: str = Query(default="popularity"),
    limit: int = Query(default=24, le=100),
    offset: int = Query(default=0),
    api_key: str = Query(default=""),
):
    engine = get_engine()
    resolved_key = _get_api_key(api_key)
    df = engine.df.copy()

    if actor.strip():
        act_term = actor.strip()
        act_mask = pd.Series(False, index=df.index)
        if "cast" in df.columns:
            act_mask = df["cast"].astype(str).str.contains(act_term, case=False, na=False)
        if not act_mask.any() and resolved_key:
            persons = search_tmdb_person(act_term, api_key=resolved_key)
            if persons:
                p_id = persons[0].get("id")
                if p_id:
                    p_info = fetch_person_details(p_id, api_key=resolved_key)
                    if p_info and p_info.get("known_for"):
                        kf_ids = {m["id"] for m in p_info["known_for"]}
                        act_mask = df["id"].isin(kf_ids)
        if act_mask.any():
            df = df[act_mask]

    if language.lower() != "all":
        df = df[df["original_language"] == language.lower()]

    if genre.lower() != "all":
        df = df[df["genre"].astype(str).str.contains(genre, case=False, na=False)]

    if min_rating is not None and min_rating > 0:
        df = df[df["vote_average"] >= float(min_rating)]

    if year_from is not None and year_from > 0:
        df = df[df["release_year"] >= int(year_from)]

    if year_to is not None and year_to > 0:
        df = df[df["release_year"] <= int(year_to)]

    sort_map = {
        "popularity": ("popularity", False),
        "rating": ("vote_average", False),
        "newest": ("release_year", False),
        "oldest": ("release_year", True),
    }
    col, asc = sort_map.get(sort_by, ("popularity", False))
    df = df.sort_values(by=col, ascending=asc)

    total = len(df)
    page_df = df.iloc[offset: offset + limit]

    movies = []
    for _, row in page_df.iterrows():
        meta = get_movie_metadata(int(row["id"]), local_data=row, api_key=resolved_key, region="IN")
        enriched = _enrich_meta(meta)
        if min_rating is not None and min_rating > 0 and float(enriched.get("vote_average", 0)) < float(min_rating):
            continue
        movies.append(enriched)

    return {"total": total, "offset": offset, "limit": limit, "movies": movies}


@app.get("/api/genres")
def get_genres():
    engine = get_engine()
    genres_set = set()
    for g in engine.df["genre"].dropna():
        for genre in str(g).split(","):
            genre = genre.strip()
            if genre and genre.lower() not in ("unknown", ""):
                genres_set.add(genre)
    return {"genres": sorted(genres_set)}


# Auth
@app.post("/api/auth/register")
def auth_register(req: AuthRegisterRequest):
    if not req.name or not req.email or not req.password:
        raise HTTPException(status_code=400, detail="All fields required")
    if "@" not in req.email:
        raise HTTPException(status_code=400, detail="Invalid email address")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    result = register_user(req.name, req.email, req.password)
    if not result["success"]:
        raise HTTPException(status_code=409, detail=result["message"])
    return result


@app.post("/api/auth/login")
def auth_login(req: AuthLoginRequest):
    if not req.email or not req.password:
        raise HTTPException(status_code=400, detail="Email and password required")
    result = login_user(req.email, req.password)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["message"])
    return result


@app.post("/api/auth/forgot-password")
def auth_forgot_password(req: ForgotPasswordRequest):
    email = req.email.strip()
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    res = create_password_reset_token(email)
    if res.get("rate_limited"):
        raise HTTPException(status_code=429, detail=res["message"])

    email_status = {}
    if res.get("user_found") and res.get("raw_token"):
        email_status = send_password_reset_email(
            to_email=res["user_email"],
            user_name=res["user_name"],
            raw_token=res["raw_token"],
        )

    return {
        "success": True,
        "message": res["message"],
        "dev_mode": email_status.get("mode") == "development",
        "dev_reset_url": email_status.get("dev_reset_url"),
        "email_sent": email_status.get("sent", False),
    }


@app.get("/api/auth/reset-password/validate")
def auth_validate_reset_token(token: str = Query(...)):
    check = verify_password_reset_token(token)
    if not check["valid"]:
        return {"valid": False, "message": check["message"]}
    
    # Mask email for privacy (e.g., a***n@gmail.com)
    email = check.get("email", "")
    masked_email = ""
    if "@" in email:
        parts = email.split("@")
        name_part = parts[0]
        domain_part = parts[1]
        if len(name_part) > 2:
            masked_email = f"{name_part[0]}***{name_part[-1]}@{domain_part}"
        else:
            masked_email = f"{name_part[0]}***@{domain_part}"

    return {
        "valid": True,
        "message": "Token is valid.",
        "email": masked_email,
        "name": check.get("name", ""),
    }


@app.post("/api/auth/reset-password")
def auth_reset_password(req: ResetPasswordRequest):
    if not req.token or not req.token.strip():
        raise HTTPException(status_code=400, detail="Reset token is required.")

    if not req.password:
        raise HTTPException(status_code=400, detail="Password is required.")

    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    if req.confirm_password is not None and req.password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    result = reset_password_with_token(req.token, req.password)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


# Watchlist
@app.get("/api/watchlist/{user_id}")
def get_watchlist(user_id: int, api_key: str = Query(default=""), region: str = Query(default="IN")):
    engine = get_engine()
    resolved_key = _get_api_key(api_key)
    fav_ids = get_favorites(user_id)
    watched_ids_set = set(get_watched_ids(user_id))
    movies = []
    for movie_id in fav_ids:
        match = engine.df[engine.df["id"] == movie_id]
        local_row = match.iloc[0] if not match.empty else {"id": movie_id, "title": f"Movie #{movie_id}"}
        meta = get_movie_metadata(movie_id, local_data=local_row, api_key=resolved_key, region=region)
        enriched = _enrich_meta(meta)
        enriched["is_watched"] = movie_id in watched_ids_set
        movies.append(enriched)
    return {"user_id": user_id, "movies": movies, "count": len(movies)}


@app.get("/api/watchlist/{user_id}/ids")
def get_watchlist_ids(user_id: int):
    return {"user_id": user_id, "movie_ids": get_favorites(user_id)}


@app.post("/api/watchlist/add")
@app.post("/api/favorites/add")
def watchlist_add(req: WatchlistRequest):
    result = add_favorite(req.user_id, req.movie_id)
    if not result["success"]:
        raise HTTPException(status_code=409, detail=result["message"])
    return result


@app.post("/api/watchlist/remove")
@app.post("/api/favorites/remove")
def watchlist_remove(req: WatchlistRequest):
    return remove_favorite(req.user_id, req.movie_id)


# ---------------------------------------------------------------------------
# Watched History
# ---------------------------------------------------------------------------
@app.get("/api/watched/{user_id}")
def get_watched_history(user_id: int, api_key: str = Query(default=""), region: str = Query(default="IN")):
    engine = get_engine()
    resolved_key = _get_api_key(api_key)
    history = get_watched(user_id)
    movies = []
    for entry in history:
        movie_id = entry["movie_id"]
        match = engine.df[engine.df["id"] == movie_id]
        local_row = match.iloc[0] if not match.empty else {"id": movie_id, "title": f"Movie #{movie_id}"}
        meta = get_movie_metadata(movie_id, local_data=local_row, api_key=resolved_key, region=region)
        enriched = _enrich_meta(meta)
        enriched["user_rating"] = entry.get("rating")
        enriched["watched_at"] = entry.get("watched_at")
        movies.append(enriched)
    return {"user_id": user_id, "movies": movies, "count": len(movies)}


@app.get("/api/watched/{user_id}/ids")
def get_watched_history_ids(user_id: int):
    return {"user_id": user_id, "movie_ids": get_watched_ids(user_id)}


@app.post("/api/watched/add")
def watched_add(req: WatchedRequest):
    result = add_watched(req.user_id, req.movie_id, rating=req.rating)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@app.post("/api/watched/remove")
def watched_remove(req: WatchedRequest):
    return remove_watched(req.user_id, req.movie_id)


# ---------------------------------------------------------------------------
# User Preferences
# ---------------------------------------------------------------------------
@app.get("/api/preferences/{user_id}")
def get_preferences(user_id: int):
    return get_user_preferences(user_id)


@app.post("/api/preferences/save")
def save_preferences(req: PreferencesRequest):
    langs = req.languages or req.preferred_languages or []
    gnrs = req.genres or req.preferred_genres or []
    result = save_user_preferences(req.user_id, langs, gnrs)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@app.post("/api/preferences/{user_id}")
def save_preferences_by_id(user_id: int, req: PreferencesRequest):
    langs = req.languages or req.preferred_languages or []
    gnrs = req.genres or req.preferred_genres or []
    result = save_user_preferences(user_id, langs, gnrs)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


# ---------------------------------------------------------------------------
# Person (Actor / Director) Details
# ---------------------------------------------------------------------------
@app.get("/api/person/{person_id}")
def get_person(person_id: int, api_key: str = Query(default="")):
    resolved_key = _get_api_key(api_key)
    person = fetch_person_details(person_id, api_key=resolved_key)
    if not person:
        raise HTTPException(status_code=404, detail=f"Person id {person_id} not found")
    return person


@app.get("/api/person/search")
def search_person(q: str = Query(default=""), api_key: str = Query(default="")):
    if not q.strip():
        return {"results": []}
    resolved_key = _get_api_key(api_key)
    results = search_tmdb_person(q.strip(), api_key=resolved_key)
    return {"results": results, "count": len(results)}


@app.get("/api/person/{person_id}/movies")
def get_person_movies(
    person_id: int,
    limit: int = Query(default=24, le=100),
    offset: int = Query(default=0),
    api_key: str = Query(default=""),
    region: str = Query(default="IN"),
):
    """
    Return all catalog movies featuring a specific person (actor/actress or director).
    Cross-references TMDB person credits with our dataset and local cast records.
    """
    engine = get_engine()
    resolved_key = _get_api_key(api_key)
    person = fetch_person_details(person_id, api_key=resolved_key)
    if not person:
        raise HTTPException(status_code=404, detail=f"Person id {person_id} not found")

    df = engine.df.copy()
    matched_ids = set()

    # 1. Match from known_for movie IDs
    for m in person.get("known_for", []):
        if m.get("id"):
            matched_ids.add(int(m["id"]))

    # 2. Check local cast / director strings
    p_name = person.get("name", "").strip()
    if p_name:
        if "cast" in df.columns:
            name_cast_match = df[df["cast"].astype(str).str.contains(p_name, case=False, na=False)]
            matched_ids.update(name_cast_match["id"].astype(int).tolist())
        if "director" in df.columns:
            name_dir_match = df[df["director"].astype(str).str.contains(p_name, case=False, na=False)]
            matched_ids.update(name_dir_match["id"].astype(int).tolist())

    matched_df = df[df["id"].isin(matched_ids)] if matched_ids else df.head(0)

    # Sort by rating / popularity
    if not matched_df.empty:
        matched_df = matched_df.sort_values(by=["vote_average", "popularity"], ascending=False)

    total = len(matched_df)
    page_df = matched_df.iloc[offset: offset + limit]

    movies = []
    for _, row in page_df.iterrows():
        meta = get_movie_metadata(int(row["id"]), local_data=row, api_key=resolved_key, region=region)
        movies.append(_enrich_meta(meta))

    return {
        "person": {
            "id": person["id"],
            "name": person["name"],
            "known_for_department": person.get("known_for_department", "Acting"),
            "profile_url": person.get("profile_url"),
        },
        "total": total,
        "offset": offset,
        "limit": limit,
        "movies": movies,
    }


# ---------------------------------------------------------------------------
# Personalized Recommendations (based on watchlist + watched + preferences)
# ---------------------------------------------------------------------------
@app.get("/api/personalized/{user_id}")
def get_personalized(
    user_id: int,
    top_k: int = Query(default=12, le=24),
    api_key: str = Query(default=""),
    region: str = Query(default="IN"),
):
    """
    Return AI recommendations based on user's watchlist, watched history, and preferences.
    Uses the existing TF-IDF cosine similarity engine; seeds from saved/watched movies.
    Includes rich 'Because you liked...' explanations based on real matching features.
    """
    engine = get_engine()
    resolved_key = _get_api_key(api_key)
    prefs = get_user_preferences(user_id)
    fav_ids = get_favorites(user_id)
    watched_history = get_watched(user_id)
    watched_ids = [w["movie_id"] for w in watched_history]
    watched_set = set(watched_ids)
    all_user_ids = set(fav_ids) | watched_set

    # Pick seeds: up to 3 favorites + up to 2 watched movies
    seeds = []
    seed_titles = []
    seed_reasons = {}

    for fid in fav_ids[:3]:
        match = engine.df[engine.df["id"] == fid]
        if not match.empty:
            t = str(match.iloc[0].get("title", f"Movie #{fid}"))
            seeds.append((fid, match.index[0], t, "watchlist"))
            seed_titles.append(t)
            seed_reasons[fid] = f"Because you added \"{t}\" to your watchlist"

    for wid in [w for w in watched_ids if w not in set(fav_ids)][:2]:
        match = engine.df[engine.df["id"] == wid]
        if not match.empty:
            t = str(match.iloc[0].get("title", f"Movie #{wid}"))
            seeds.append((wid, match.index[0], t, "watched"))
            seed_titles.append(t)
            seed_reasons[wid] = f"Because you watched \"{t}\""

    # If no seeds from watchlist or watched, fall back to preferred genres/languages
    if not seeds:
        pref_genres = prefs.get("preferred_genres", [])
        pref_langs = prefs.get("preferred_languages", [])
        df_sub = engine.df.copy()
        if pref_langs:
            df_sub = df_sub[df_sub["original_language"].isin(pref_langs)]
        if pref_genres:
            genre_pat = "|".join([g for g in pref_genres if g])
            if genre_pat:
                df_sub = df_sub[df_sub["genre"].astype(str).str.contains(genre_pat, case=False, na=False)]
        
        if df_sub.empty:
            df_sub = engine.df.sort_values(by="popularity", ascending=False).head(top_k)
        else:
            df_sub = df_sub.sort_values(by=["vote_average", "popularity"], ascending=False).head(top_k)

        movies = []
        for _, row in df_sub.iterrows():
            meta = get_movie_metadata(int(row["id"]), local_data=row, api_key=resolved_key, region=region)
            enriched = _enrich_meta(meta)
            enriched["because_reason"] = "Recommended based on your preferred genres and languages"
            movies.append(enriched)

        return {
            "movies": movies,
            "based_on": ["Your Preferred Genres & Languages"],
            "count": len(movies),
            "message": "Curated based on your profile preferences." if movies else "Add movies to your watchlist to unlock tailored AI matches."
        }

    # Generate recommendations using existing TF-IDF cosine similarity engine
    all_recs: dict = {}
    for seed_id, movie_index, title, seed_type in seeds:
        lang_filter = prefs.get("preferred_languages", [])
        lang_filter = lang_filter[0] if len(lang_filter) == 1 else None
        recs_df = engine.recommend(movie_index=movie_index, top_k=top_k * 3, language_filter=lang_filter)
        for _, row in recs_df.iterrows():
            mid = int(row["id"])
            if mid in all_user_ids:
                continue
            score = float(row.get("similarity_score", 0))
            if mid not in all_recs:
                all_recs[mid] = {"row": row, "score": score, "seed_id": seed_id, "seed_title": title, "seed_type": seed_type}
            else:
                if score > all_recs[mid]["score"]:
                    all_recs[mid] = {"row": row, "score": score, "seed_id": seed_id, "seed_title": title, "seed_type": seed_type}

    sorted_recs = sorted(all_recs.values(), key=lambda x: x["score"], reverse=True)[:top_k]
    movies = []
    for entry in sorted_recs:
        row = entry["row"]
        meta = get_movie_metadata(int(row["id"]), local_data=row, api_key=resolved_key, region=region)
        enriched = _enrich_meta(meta)
        enriched["seed_movie_id"] = entry["seed_id"]
        enriched["seed_title"] = entry["seed_title"]
        enriched["similarity_score"] = entry["score"]
        enriched["ai_match_pct"] = round(entry["score"] * 100, 1)
        reason_template = "Because you added \"{title}\" to your watchlist" if entry["seed_type"] == "watchlist" else "Because you watched \"{title}\""
        enriched["because_reason"] = reason_template.format(title=entry["seed_title"])
        movies.append(enriched)

    return {
        "movies": movies,
        "based_on": seed_titles,
        "count": len(movies),
        "message": f"Generated from {len(seeds)} of your saved titles using TF-IDF cosine similarity."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True,
                app_dir=os.path.dirname(os.path.abspath(__file__)))

