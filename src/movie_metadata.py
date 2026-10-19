"""
movie_metadata.py - Dynamic TMDB Metadata, Posters & Streaming Availability Engine
====================================================================================
This module provides:
  1. Live metadata enrichment: cast, directors, taglines, ratings, runtimes
  2. Dynamic poster resolution for ANY movie:
       - local URL/path -> TMDB ID lookup -> TMDB title/year/lang search -> fallback
       - Zero hardcoding: completely generic across all languages and datasets
  3. Where to Watch / OTT Streaming Availability:
       - Powered by TMDB Watch Providers API (JustWatch data)
       - Target region support (India "IN", US, UK, etc.)
       - Two-tier caching (in-memory + persistent data/ott_cache.json)
       - Clean fallback when unavailable ("Streaming availability unavailable")
  4. Multi-tier caching:
       - In-memory metadata cache (_METADATA_CACHE)
       - Persistent file-backed poster disk cache (data/poster_cache.json)
       - Persistent file-backed OTT disk cache (data/ott_cache.json)
  5. Multi-language TMDB Indian movie discovery (ta, ml, te, kn, hi)
  6. Resilient offline fallback:
       - Complete metadata & posters generated from local CSV dataset if API is unconfigured
"""

import os
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any, List, Union
import requests
import pandas as pd

# ---------------------------------------------------------------------------
# TMDB Constants
# ---------------------------------------------------------------------------
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
TMDB_BACKDROP_BASE_URL = "https://image.tmdb.org/t/p/w1280"
TMDB_LOGO_BASE_URL = "https://image.tmdb.org/t/p/w92"
TMDB_PROFILE_BASE_URL = "https://image.tmdb.org/t/p/w185"
DEFAULT_TIMEOUT_SEC = 6.0

# Supported Indian language display mapping
SUPPORTED_INDIAN_LANGUAGES = {
    "ta": "Tamil",
    "ml": "Malayalam",
    "te": "Telugu",
    "kn": "Kannada",
    "hi": "Hindi",
    "en": "English",
}

# TMDB genre ID to name mapping
TMDB_GENRE_MAP = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
    80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
    14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
    9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
    10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western",
}

# ---------------------------------------------------------------------------
# In-memory metadata cache
# ---------------------------------------------------------------------------
_METADATA_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_LOCK = threading.Lock()

# ---------------------------------------------------------------------------
# Persistent poster disk cache (data/poster_cache.json)
# ---------------------------------------------------------------------------
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_POSTER_CACHE_FILE = os.path.join(_BASE_DIR, "data", "poster_cache.json")
_POSTER_DISK_CACHE: Dict[str, str] = {}
_POSTER_CACHE_LOCK = threading.Lock()


def _load_poster_disk_cache() -> None:
    """Load the persistent poster URL cache from disk into memory."""
    global _POSTER_DISK_CACHE
    if not os.path.exists(_POSTER_CACHE_FILE):
        return
    try:
        with open(_POSTER_CACHE_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            with _POSTER_CACHE_LOCK:
                _POSTER_DISK_CACHE = data
    except Exception:
        pass


def _persist_poster_url(movie_id: int, poster_url: str) -> None:
    """Write a newly resolved poster URL to the JSON disk cache."""
    if not poster_url or not movie_id:
        return
    key = str(int(movie_id))
    with _POSTER_CACHE_LOCK:
        if _POSTER_DISK_CACHE.get(key) == poster_url:
            return
        _POSTER_DISK_CACHE[key] = poster_url
        try:
            os.makedirs(os.path.dirname(_POSTER_CACHE_FILE), exist_ok=True)
            with open(_POSTER_CACHE_FILE, "w", encoding="utf-8") as fh:
                json.dump(_POSTER_DISK_CACHE, fh)
        except Exception:
            pass


def _get_disk_cached_poster(movie_id: int) -> Optional[str]:
    """Return the disk-cached poster URL for a movie ID, or None."""
    if not movie_id:
        return None
    with _POSTER_CACHE_LOCK:
        return _POSTER_DISK_CACHE.get(str(int(movie_id)))


# Load poster disk cache eagerly at import time
_load_poster_disk_cache()


# ---------------------------------------------------------------------------
# Persistent OTT / Streaming disk cache (data/ott_cache.json)
# ---------------------------------------------------------------------------
_OTT_CACHE_FILE = os.path.join(_BASE_DIR, "data", "ott_cache.json")
_OTT_DISK_CACHE: Dict[str, Dict[str, Any]] = {}
_OTT_CACHE_LOCK = threading.Lock()


def _load_ott_disk_cache() -> None:
    """Load persistent OTT streaming cache from disk."""
    global _OTT_DISK_CACHE
    if not os.path.exists(_OTT_CACHE_FILE):
        return
    try:
        with open(_OTT_CACHE_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            with _OTT_CACHE_LOCK:
                _OTT_DISK_CACHE = data
    except Exception:
        pass


def _persist_streaming_info(movie_id: int, region: str, info: Dict[str, Any]) -> None:
    """Write resolved streaming availability info to persistent disk cache."""
    if not movie_id or not info:
        return
    cache_key = f"{int(movie_id)}_{str(region or 'IN').upper()}"
    with _OTT_CACHE_LOCK:
        _OTT_DISK_CACHE[cache_key] = info
        try:
            os.makedirs(os.path.dirname(_OTT_CACHE_FILE), exist_ok=True)
            with open(_OTT_CACHE_FILE, "w", encoding="utf-8") as fh:
                json.dump(_OTT_DISK_CACHE, fh)
        except Exception:
            pass


def _get_disk_cached_streaming(movie_id: int, region: str) -> Optional[Dict[str, Any]]:
    """Return disk-cached streaming info for a movie ID and region, or None."""
    if not movie_id:
        return None
    cache_key = f"{int(movie_id)}_{str(region or 'IN').upper()}"
    with _OTT_CACHE_LOCK:
        return _OTT_DISK_CACHE.get(cache_key)


# Load OTT disk cache eagerly at import time
_load_ott_disk_cache()


# ---------------------------------------------------------------------------
# Persistent Person / Cast disk cache (data/person_cache.json)
# ---------------------------------------------------------------------------
_PERSON_CACHE_FILE = os.path.join(_BASE_DIR, "data", "person_cache.json")
_PERSON_DISK_CACHE: Dict[str, Dict[str, Any]] = {}
_PERSON_CACHE_LOCK = threading.Lock()


def _load_person_disk_cache() -> None:
    """Load persistent actor/director profile cache from disk."""
    global _PERSON_DISK_CACHE
    if not os.path.exists(_PERSON_CACHE_FILE):
        return
    try:
        with open(_PERSON_CACHE_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            with _PERSON_CACHE_LOCK:
                _PERSON_DISK_CACHE = data
    except Exception:
        pass


def _persist_person_info(person_id: int, info: Dict[str, Any]) -> None:
    """Write person profile info to persistent disk cache."""
    if not person_id or not info:
        return
    key = str(int(person_id))
    with _PERSON_CACHE_LOCK:
        _PERSON_DISK_CACHE[key] = info
        try:
            os.makedirs(os.path.dirname(_PERSON_CACHE_FILE), exist_ok=True)
            with open(_PERSON_CACHE_FILE, "w", encoding="utf-8") as fh:
                json.dump(_PERSON_DISK_CACHE, fh)
        except Exception:
            pass


def _get_disk_cached_person(person_id: int) -> Optional[Dict[str, Any]]:
    """Return disk-cached person info, or None."""
    if not person_id:
        return None
    key = str(int(person_id))
    with _PERSON_CACHE_LOCK:
        return _PERSON_DISK_CACHE.get(key)


_load_person_disk_cache()


# ---------------------------------------------------------------------------
# 1. API KEY RESOLUTION (SECURE)
# ---------------------------------------------------------------------------

def get_api_key(explicit_key: Optional[str] = None) -> Optional[str]:
    """
    Retrieve TMDB API key from (in priority order):
      1. Explicitly provided key
      2. Streamlit secrets (TMDB_API_KEY or tmdb_api_key)
      3. Environment variables (TMDB_API_KEY, TMDB_KEY)
    Returns sanitized key string or None.
    """
    if explicit_key and str(explicit_key).strip():
        return str(explicit_key).strip()
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            for skey in ("TMDB_API_KEY", "tmdb_api_key"):
                if skey in st.secrets and st.secrets[skey]:
                    return str(st.secrets[skey]).strip()
    except Exception:
        pass
    env_key = os.environ.get("TMDB_API_KEY") or os.environ.get("TMDB_KEY") or os.environ.get("TMDB_API_READ_ACCESS_TOKEN")
    if env_key and str(env_key).strip():
        return str(env_key).strip()
    return None


def is_api_configured(explicit_key: Optional[str] = None) -> bool:
    """Return True if a TMDB API key is available."""
    return get_api_key(explicit_key) is not None


# ---------------------------------------------------------------------------
# 2. TMDB API LOW-LEVEL HELPERS
# ---------------------------------------------------------------------------

def _build_request_auth(api_key: str):
    """Build HTTP params + headers for a TMDB request."""
    headers = {"Accept": "application/json", "User-Agent": "CineWise-AI/2.0"}
    params: Dict[str, Any] = {}
    if api_key.startswith("Bearer "):
        headers["Authorization"] = api_key
    elif len(api_key) > 64 or api_key.startswith("ey"):
        headers["Authorization"] = f"Bearer {api_key}"
    else:
        params["api_key"] = api_key
    return params, headers


def fetch_tmdb_movie_details(
    movie_id: int,
    api_key: Optional[str] = None,
    timeout: float = DEFAULT_TIMEOUT_SEC,
) -> Optional[Dict[str, Any]]:
    """
    Fetch full movie details + credits + watch providers from TMDB /movie/{id}.
    Returns parsed JSON dict or None on any error.
    """
    key = get_api_key(api_key)
    if not key or int(movie_id) <= 0:
        return None
    url = f"{TMDB_BASE_URL}/movie/{int(movie_id)}"
    params, headers = _build_request_auth(key)
    params["append_to_response"] = "credits,watch/providers,videos"
    params["language"] = "en-US"
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 401:
            print("[movie_metadata] TMDB: Invalid API key (401).")
        elif resp.status_code == 404:
            print(f"[movie_metadata] TMDB: Movie ID {movie_id} not found (404).")
        return None
    except requests.Timeout:
        return None
    except Exception as exc:
        print(f"[movie_metadata] TMDB error for movie ID {movie_id}: {exc}")
        return None


def search_tmdb_movie(
    title: str,
    year: Optional[int] = None,
    language: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: float = DEFAULT_TIMEOUT_SEC,
) -> Optional[Dict[str, Any]]:
    """
    Search TMDB for a movie by title (+ optional year and language).
    Selects the best result using a scoring function.
    """
    key = get_api_key(api_key)
    if not key or not title or not str(title).strip():
        return None
    url = f"{TMDB_BASE_URL}/search/movie"
    params, headers = _build_request_auth(key)
    params["query"] = str(title).strip()
    params["language"] = "en-US"
    params["include_adult"] = "false"
    if year and int(year) > 0:
        params["primary_release_year"] = int(year)

    def _pick_best(results: List[Dict]) -> Optional[Dict]:
        if not results:
            return None
        title_lower = str(title).strip().lower()
        lang_lower = str(language).strip().lower() if language else None

        def score(r: Dict) -> float:
            s = 0.0
            t = str(r.get("title", "")).lower()
            ot = str(r.get("original_title", "")).lower()
            if t == title_lower or ot == title_lower:
                s += 10.0
            elif title_lower in t or title_lower in ot:
                s += 5.0
            if lang_lower and str(r.get("original_language", "")).lower() == lang_lower:
                s += 3.0
            s += min(float(r.get("popularity", 0.0)) / 1000.0, 1.0)
            return s

        ranked = sorted(results, key=score, reverse=True)
        best = ranked[0]
        best_id = best.get("id")
        if best_id:
            details = fetch_tmdb_movie_details(int(best_id), api_key=key, timeout=timeout)
            if details:
                return details
        return best

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            hit = _pick_best(resp.json().get("results", []))
            if hit:
                return hit
    except Exception:
        pass

    # Fallback retry without year if year was passed and failed
    if year:
        try:
            params.pop("primary_release_year", None)
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                return _pick_best(resp.json().get("results", []))
        except Exception:
            pass

    return None


# ---------------------------------------------------------------------------
# 3. OTT / WHERE TO WATCH AVAILABILITY
# ---------------------------------------------------------------------------

def _parse_region_watch_providers(wp_data: Any, region: str = "IN") -> Dict[str, Any]:
    """Parse region-specific streaming providers from TMDB Watch Providers data."""
    reg = str(region or "IN").strip().upper()
    default_empty = {
        "available": False,
        "region": reg,
        "providers": [],
        "flatrate": [],
        "free": [],
        "rent": [],
        "buy": [],
        "link": None,
        "message": "OTT availability is currently unavailable.",
    }
    if not wp_data or not isinstance(wp_data, dict):
        return default_empty

    results = wp_data.get("results", {}) if "results" in wp_data else wp_data
    if not isinstance(results, dict):
        return default_empty

    region_data = results.get(reg)
    # If target region not found, try fallback standard regions (e.g. IN, US, GB)
    if not region_data:
        for fallback_reg in ("IN", "US", "GB"):
            if fallback_reg in results:
                region_data = results[fallback_reg]
                reg = fallback_reg
                break

    if not region_data or not isinstance(region_data, dict):
        return default_empty

    def _fmt_prov(p: Dict[str, Any]) -> Dict[str, Any]:
        logo_path = p.get("logo_path")
        return {
            "provider_id": p.get("provider_id"),
            "provider_name": p.get("provider_name", "Unknown"),
            "logo_path": logo_path,
            "logo_url": f"{TMDB_LOGO_BASE_URL}{logo_path}" if logo_path else None,
        }

    flatrate = [_fmt_prov(p) for p in region_data.get("flatrate", []) if p.get("provider_name")]
    raw_free = region_data.get("free", []) + region_data.get("ads", [])
    free = [_fmt_prov(p) for p in raw_free if p.get("provider_name")]
    rent = [_fmt_prov(p) for p in region_data.get("rent", []) if p.get("provider_name")]
    buy = [_fmt_prov(p) for p in region_data.get("buy", []) if p.get("provider_name")]
    link = region_data.get("link")

    available = bool(flatrate or free or rent or buy)
    provider_names = [p["provider_name"] for p in (flatrate or free or rent or buy)]

    return {
        "available": available,
        "region": reg,
        "providers": provider_names,
        "flatrate": flatrate,
        "free": free,
        "rent": rent,
        "buy": buy,
        "link": link,
        "message": "" if available else "OTT availability is currently unavailable.",
    }


def fetch_watch_providers(
    movie_id: int,
    region: str = "IN",
    api_key: Optional[str] = None,
    timeout: float = DEFAULT_TIMEOUT_SEC,
) -> Dict[str, Any]:
    """
    Fetch streaming providers for a TMDB movie ID from /movie/{id}/watch/providers.
    Returns standardized streaming dictionary for target region.
    """
    key = get_api_key(api_key)
    reg = str(region or "IN").strip().upper()
    default_res = {
        "available": False,
        "region": reg,
        "providers": [],
        "rent": [],
        "buy": [],
        "link": None,
        "message": "Streaming availability unavailable",
    }
    if not key or int(movie_id) <= 0:
        return default_res

    url = f"{TMDB_BASE_URL}/movie/{int(movie_id)}/watch/providers"
    params, headers = _build_request_auth(key)
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json().get("results", {})
            return _parse_region_watch_providers(data, region=reg)
    except Exception:
        pass
    return default_res


def get_streaming_providers(
    movie_id: int,
    region: str = "IN",
    api_key: Optional[str] = None,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """
    Public entry point to retrieve OTT streaming availability.
    Flow:
      1. Check disk / in-memory cache
      2. If not cached and API key available -> fetch from TMDB Watch Providers
      3. Persist to cache and return
      4. If unavailable -> returns "Streaming availability unavailable"
    """
    mid = int(movie_id) if movie_id else 0
    reg = str(region or "IN").strip().upper()
    if mid <= 0:
        return {
            "available": False,
            "region": reg,
            "providers": [],
            "rent": [],
            "buy": [],
            "link": None,
            "message": "Streaming availability unavailable",
        }

    if use_cache:
        cached = _get_disk_cached_streaming(mid, reg)
        if cached:
            return cached

    info = fetch_watch_providers(mid, region=reg, api_key=api_key)
    if info.get("available") and use_cache:
        _persist_streaming_info(mid, reg, info)

    return info


# ---------------------------------------------------------------------------
# 4. GENERIC POSTER RESOLUTION PIPELINE (NO HARDCODING)
# ---------------------------------------------------------------------------

def resolve_poster_url(
    movie_id: Optional[int] = None,
    title: Optional[str] = None,
    year: Optional[int] = None,
    language: Optional[str] = None,
    existing_poster_path: Optional[str] = None,
    existing_poster_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: float = DEFAULT_TIMEOUT_SEC,
) -> Optional[str]:
    """
    Generic 7-step priority resolution for ANY movie poster.
      Step 1: Check existing_poster_url
      Step 2: Check existing_poster_path
      Step 3: Check persistent disk cache (data/poster_cache.json)
      Step 4: TMDB ID direct lookup (/movie/{id})
      Step 5: TMDB multi-attribute search (title + year + language)
      Step 6: TMDB title-only search
      Step 7: Return None -> triggers clean placeholder card
    """
    _bad = {"", "nan", "None", "null", "undefined", "<NA>", "NaT"}

    def _valid_url(u: Any) -> bool:
        return bool(u and isinstance(u, str)
                    and u.strip() not in _bad
                    and u.strip().startswith(("http://", "https://")))

    def _path_to_url(p: Any) -> Optional[str]:
        if not p or not isinstance(p, str) or p.strip() in _bad:
            return None
        p = p.strip()
        if p.startswith(("http://", "https://")):
            return p
        return (f"{TMDB_IMAGE_BASE_URL}{p}" if p.startswith("/")
                else f"{TMDB_IMAGE_BASE_URL}/{p}")

    # Step 1
    if _valid_url(existing_poster_url):
        return existing_poster_url.strip()

    # Step 2
    u = _path_to_url(existing_poster_path)
    if u:
        return u

    # Step 3 — disk cache
    mid = int(movie_id) if movie_id else 0
    if mid > 0:
        cached = _get_disk_cached_poster(mid)
        if cached:
            return cached

    # Steps 4-6 require API key
    key = get_api_key(api_key)
    if not key:
        return None

    poster_url: Optional[str] = None

    # Step 4 — TMDB direct ID lookup
    if mid > 0:
        data = fetch_tmdb_movie_details(mid, api_key=key, timeout=timeout)
        if data and data.get("poster_path"):
            poster_url = _path_to_url(data["poster_path"])

    # Step 5 — TMDB search by title + year + language
    clean_title = str(title).strip() if title else ""
    if clean_title and not poster_url:
        data = search_tmdb_movie(
            clean_title,
            year=int(year) if year and int(year) > 0 else None,
            language=str(language).strip() if language else None,
            api_key=key,
            timeout=timeout,
        )
        if data and data.get("poster_path"):
            poster_url = _path_to_url(data["poster_path"])

    # Step 6 — TMDB search by title only
    if clean_title and not poster_url and year and int(year) > 0:
        data = search_tmdb_movie(clean_title, api_key=key, timeout=timeout)
        if data and data.get("poster_path"):
            poster_url = _path_to_url(data["poster_path"])

    # Persist result to disk cache
    if poster_url and mid > 0:
        _persist_poster_url(mid, poster_url)

    return poster_url


# ---------------------------------------------------------------------------
# 5. INDIAN MOVIE DISCOVERY
# ---------------------------------------------------------------------------

def discover_indian_movies(
    language_code: str,
    api_key: Optional[str] = None,
    max_pages: int = 5,
) -> List[Dict[str, Any]]:
    """
    Discover movies by original language via TMDB Discover API.
    Supported codes: ta, ml, te, kn, hi, en
    Returns standardized movie dicts with poster_url pre-populated.
    """
    key = api_key or get_api_key()
    if not key:
        return []
    url = f"{TMDB_BASE_URL}/discover/movie"
    lang_code = str(language_code).strip().lower()
    movies: List[Dict[str, Any]] = []
    seen_ids: set = set()

    for page in range(1, max(1, max_pages) + 1):
        params, headers = _build_request_auth(key)
        params["with_original_language"] = lang_code
        params["sort_by"] = "popularity.desc"
        params["page"] = page
        params["include_adult"] = "false"
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code != 200:
                break
            data = resp.json()
            results = data.get("results", [])
            if not results:
                break
            for movie in results:
                m_id = movie.get("id")
                if not m_id or m_id in seen_ids:
                    continue
                seen_ids.add(m_id)
                poster_path = movie.get("poster_path")
                poster_url = f"{TMDB_IMAGE_BASE_URL}{poster_path}" if poster_path else None
                release_date = str(movie.get("release_date") or "")
                release_year = 0
                if len(release_date) >= 4 and release_date[:4].isdigit():
                    release_year = int(release_date[:4])
                genre_ids = movie.get("genre_ids", []) or []
                genre_names = [TMDB_GENRE_MAP[gid] for gid in genre_ids if gid in TMDB_GENRE_MAP]
                genre_str = ", ".join(genre_names) if genre_names else "Drama"
                movies.append({
                    "id": int(m_id), "tmdb_id": int(m_id),
                    "title": movie.get("title") or movie.get("original_title") or f"Movie #{m_id}",
                    "original_title": movie.get("original_title", ""),
                    "original_language": movie.get("original_language", lang_code),
                    "overview": movie.get("overview", "") or "",
                    "release_date": release_date, "release_year": release_year,
                    "genre": genre_str,
                    "popularity": float(movie.get("popularity", 0.0)),
                    "vote_average": float(movie.get("vote_average", 0.0)),
                    "vote_count": int(movie.get("vote_count", 0)),
                    "poster_path": poster_path, "poster_url": poster_url,
                })
                if poster_url and m_id:
                    _persist_poster_url(int(m_id), poster_url)
        except Exception:
            break

    return movies


def save_indian_movies_cache(
    new_movies: List[Dict[str, Any]],
    cache_path: Optional[str] = None,
) -> int:
    """Save newly discovered movies to data/tmdb_indian_movies.csv without duplicates."""
    if not new_movies:
        return 0
    if cache_path is None:
        cache_path = os.path.join(_BASE_DIR, "data", "tmdb_indian_movies.csv")
    new_df = pd.DataFrame(new_movies)
    if "tmdb_id" in new_df.columns and "id" not in new_df.columns:
        new_df["id"] = new_df["tmdb_id"]
    if os.path.exists(cache_path):
        try:
            existing_df = pd.read_csv(cache_path)
            combined = pd.concat([existing_df, new_df], ignore_index=True)
            combined = combined.drop_duplicates(subset=["id"], keep="first")
        except Exception:
            combined = new_df.drop_duplicates(subset=["id"], keep="first")
    else:
        combined = new_df.drop_duplicates(subset=["id"], keep="first")
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    combined.to_csv(cache_path, index=False)
    return len(combined)


def search_tmdb_movies_multi(
    query: str,
    language: Optional[str] = None,
    api_key: Optional[str] = None,
    limit: int = 15,
    timeout: float = DEFAULT_TIMEOUT_SEC,
) -> List[Dict[str, Any]]:
    """
    Search TMDB for movies matching a query string and return multiple standardized movie dicts.
    Useful when a search term is not found in the local catalog.
    """
    key = get_api_key(api_key)
    if not key or not query or not str(query).strip():
        return []

    url = f"{TMDB_BASE_URL}/search/movie"
    params, headers = _build_request_auth(key)
    params["query"] = str(query).strip()
    params["language"] = "en-US"
    params["include_adult"] = "false"

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            return []
        data = resp.json()
        results = data.get("results", [])
        movies = []
        for m in results[:limit]:
            m_id = m.get("id")
            if not m_id:
                continue
            poster_path = m.get("poster_path")
            poster_url = f"{TMDB_IMAGE_BASE_URL}{poster_path}" if poster_path else None
            release_date = str(m.get("release_date") or "")
            release_year = 0
            if len(release_date) >= 4 and release_date[:4].isdigit():
                release_year = int(release_date[:4])
            genre_ids = m.get("genre_ids", []) or []
            genre_names = [TMDB_GENRE_MAP[gid] for gid in genre_ids if gid in TMDB_GENRE_MAP]
            genre_str = ", ".join(genre_names) if genre_names else "Drama"

            movies.append({
                "id": int(m_id),
                "tmdb_id": int(m_id),
                "title": m.get("title") or m.get("original_title") or f"Movie #{m_id}",
                "original_title": m.get("original_title", ""),
                "original_language": m.get("original_language", "en"),
                "overview": m.get("overview", "") or "",
                "release_date": release_date,
                "release_year": release_year,
                "genre": genre_str,
                "popularity": float(m.get("popularity", 0.0)),
                "vote_average": float(m.get("vote_average", 0.0)),
                "vote_count": int(m.get("vote_count", 0)),
                "poster_path": poster_path,
                "poster_url": poster_url,
            })
            if poster_url:
                _persist_poster_url(int(m_id), poster_url)
        return movies
    except Exception as exc:
        print(f"[movie_metadata] TMDB multi-search error: {exc}")
        return []


def discover_catalog_movies(
    languages: Optional[List[str]] = None,
    pages_per_language: int = 2,
    api_key: Optional[str] = None,
    sort_by: str = "popularity.desc",
) -> Dict[str, Any]:
    """
    Discover movies across multiple languages and integrate them into the catalog cache
    without duplicates. Caches posters and prevents duplicates using TMDB ID.
    Languages supported include Tamil, Telugu, Malayalam, Kannada, Hindi, English, and international.
    """
    target_languages = languages or ["ta", "te", "ml", "kn", "hi", "en"]
    discovered_all: List[Dict[str, Any]] = []
    stats_by_lang = {}

    for lang in target_languages:
        try:
            movies = discover_indian_movies(
                language_code=lang,
                api_key=api_key,
                max_pages=pages_per_language,
            )
            stats_by_lang[lang] = len(movies)
            discovered_all.extend(movies)
        except Exception as e:
            stats_by_lang[lang] = 0
            print(f"[movie_metadata] Discovery error for language {lang}: {e}")

    # Deduplicate in-memory before persisting
    unique_movies = {}
    for m in discovered_all:
        unique_movies[int(m["id"])] = m

    new_list = list(unique_movies.values())
    total_in_cache = save_indian_movies_cache(new_list)

    return {
        "status": "success",
        "languages_scanned": target_languages,
        "movies_fetched": len(new_list),
        "total_catalog_cache": total_in_cache,
        "by_language": stats_by_lang,
    }


# ---------------------------------------------------------------------------
# 6. METADATA PARSERS
# ---------------------------------------------------------------------------

def _parse_tmdb_response(
    data: Dict[str, Any],
    movie_id: int,
    region: str = "IN",
) -> Dict[str, Any]:
    """Parse a raw TMDB /movie/{id} response into standardized metadata."""
    poster_path = data.get("poster_path")
    poster_url = f"{TMDB_IMAGE_BASE_URL}{poster_path}" if poster_path else None
    backdrop_path = data.get("backdrop_path")
    backdrop_url = f"{TMDB_BACKDROP_BASE_URL}{backdrop_path}" if backdrop_path else None
    # Parse official/best trailer
    videos_data = data.get("videos", {}) or {}
    video_list = videos_data.get("results", []) if isinstance(videos_data, dict) else []
    trailer_url = None
    trailer_key = None
    trailer_name = None
    for v in video_list:
        if v.get("site") == "YouTube" and v.get("type") in ("Trailer", "Teaser"):
            trailer_key = v.get("key")
            trailer_name = v.get("name", "Official Trailer")
            trailer_url = f"https://www.youtube.com/watch?v={trailer_key}"
            if v.get("official") or v.get("type") == "Trailer":
                break

    # Parse up to 15 cast members with photos and character names
    credits_data = data.get("credits", {}) or {}
    cast_list = []
    for member in credits_data.get("cast", [])[:15]:
        name = member.get("name")
        if name:
            p_path = member.get("profile_path")
            cast_list.append({
                "id": member.get("id"),
                "name": name,
                "character": member.get("character", ""),
                "profile_path": p_path,
                "profile_url": f"{TMDB_PROFILE_BASE_URL}{p_path}" if p_path else None,
                "order": member.get("order", 0),
            })

    # Parse directors and writers
    director = None
    directors = []
    writers = []
    for crew_member in credits_data.get("crew", []):
        c_name = crew_member.get("name")
        if not c_name:
            continue
        job = crew_member.get("job")
        if job == "Director":
            if not director:
                director = c_name
            if c_name not in directors:
                directors.append(c_name)
        elif job in ("Writer", "Screenplay", "Author", "Story"):
            if c_name not in writers:
                writers.append(c_name)

    genres = [g.get("name") for g in data.get("genres", []) if g.get("name")]
    release_date = data.get("release_date", "") or ""
    release_year = 0
    if len(release_date) >= 4 and release_date[:4].isdigit():
        release_year = int(release_date[:4])
    actual_id = int(data.get("id") or movie_id)

    # Parse watch/providers if included in response
    wp_data = data.get("watch/providers") or data.get("watch_providers")
    streaming_info = _parse_region_watch_providers(wp_data, region=region)
    if streaming_info.get("available") and actual_id > 0:
        _persist_streaming_info(actual_id, region, streaming_info)

    return {
        "id": actual_id, "title": data.get("title", ""),
        "original_title": data.get("original_title", ""),
        "tagline": data.get("tagline", "") or "",
        "overview": data.get("overview", "") or "",
        "release_date": release_date, "release_year": release_year,
        "genres": genres, "genre_str": ", ".join(genres) if genres else "Unknown",
        "vote_average": float(data.get("vote_average", 0.0)),
        "vote_count": int(data.get("vote_count", 0)),
        "poster_url": poster_url, "backdrop_url": backdrop_url,
        "cast": cast_list, "cast_names": [c["name"] for c in cast_list],
        "director": director, "directors": directors,
        "writers": writers, "writer_str": ", ".join(writers[:3]) if writers else "",
        "runtime": data.get("runtime"),
        "original_language": data.get("original_language", ""),
        "trailer_url": trailer_url, "trailer_key": trailer_key, "trailer_name": trailer_name,
        "streaming": streaming_info,
        "is_from_api": True,
    }


def _build_fallback_metadata(
    movie_id: int,
    local_data: Optional[Union[Dict[str, Any], pd.Series]] = None,
    region: str = "IN",
) -> Dict[str, Any]:
    """
    Build metadata from local dataset row when TMDB API is unavailable.
    Calls resolve_poster_url (disk cache only, no API) to find poster.
    """
    if local_data is None:
        local_data = {}
    elif isinstance(local_data, pd.Series):
        local_data = local_data.to_dict()

    title = str(local_data.get("title", f"Movie #{movie_id}"))
    overview = str(local_data.get("overview", "") or "")
    genre_val = str(local_data.get("genre", "Unknown") or "Unknown")
    genres = ([] if genre_val.lower() == "unknown"
              else [g.strip() for g in genre_val.split(",") if g.strip()])
    release_year = 0
    try:
        release_year = int(local_data.get("release_year", 0) or 0)
    except (ValueError, TypeError):
        pass
    vote_avg = 0.0
    try:
        vote_avg = float(local_data.get("vote_average", 0.0) or 0.0)
    except (ValueError, TypeError):
        pass
    vote_cnt = 0
    try:
        vote_cnt = int(local_data.get("vote_count", 0) or 0)
    except (ValueError, TypeError):
        pass
    release_date = str(local_data.get("release_date", "") or "")
    orig_lang = str(local_data.get("original_language", "") or "")
    orig_title = str(local_data.get("original_title", "") or "")

    # Use resolve_poster_url in offline mode (no API) - checks disk cache
    poster_url = resolve_poster_url(
        movie_id=movie_id, title=title, year=release_year, language=orig_lang,
        existing_poster_url=local_data.get("poster_url"),
        existing_poster_path=local_data.get("poster_path"),
        api_key=None,
    )

    cast_names: List[str] = []
    cast_list: List[Dict] = []
    local_cast = local_data.get("cast")
    if local_cast and isinstance(local_cast, str) and local_cast.strip() not in ("", "nan"):
        cast_names = [c.strip() for c in local_cast.split(",") if c.strip()][:5]
        cast_list = [{"name": c, "character": ""} for c in cast_names]
    elif isinstance(local_cast, list):
        cast_names = [str(c) for c in local_cast][:5]
        cast_list = [{"name": c, "character": ""} for c in cast_names]
    director = local_data.get("director")
    if director and str(director).strip() != "nan":
        director = str(director).strip()
    else:
        director = None
    tagline = str(local_data.get("tagline", "") or "")

    streaming_info = _get_disk_cached_streaming(movie_id, region) or {
        "available": False,
        "region": region.upper(),
        "providers": [],
        "rent": [],
        "buy": [],
        "link": None,
        "message": "Streaming availability unavailable",
    }

    return {
        "id": movie_id, "title": title, "original_title": orig_title,
        "tagline": tagline, "overview": overview,
        "release_date": release_date, "release_year": release_year,
        "genres": genres, "genre_str": ", ".join(genres) if genres else genre_val,
        "vote_average": vote_avg, "vote_count": vote_cnt,
        "poster_url": poster_url, "backdrop_url": None,
        "cast": cast_list, "cast_names": cast_names,
        "director": director, "directors": [director] if director else [],
        "writers": [], "writer_str": "",
        "runtime": None,
        "original_language": orig_lang,
        "trailer_url": None, "trailer_key": None, "trailer_name": None,
        "streaming": streaming_info,
        "is_from_api": False,
    }


# ---------------------------------------------------------------------------
# 7. MAIN PUBLIC METADATA API
# ---------------------------------------------------------------------------

def get_movie_metadata(
    movie_id: int,
    local_data: Optional[Union[Dict[str, Any], pd.Series]] = None,
    api_key: Optional[str] = None,
    region: str = "IN",
    use_cache: bool = True,
) -> Dict[str, Any]:
    """
    Return full metadata for any movie by TMDB ID.
    Includes:
      - title, release_year, genres, overview, rating, cast, director
      - poster_url (dynamically resolved)
      - streaming (Where to Watch OTT availability for target region)
    """
    movie_id = int(movie_id)
    cache_key = f"{movie_id}_{region.upper()}"

    if use_cache:
        with _CACHE_LOCK:
            if cache_key in _METADATA_CACHE:
                cached = _METADATA_CACHE[cache_key].copy()
                if local_data is not None:
                    ld = (local_data.to_dict() if isinstance(local_data, pd.Series)
                          else local_data)
                    if not cached.get("title") or cached["title"] == f"Movie #{movie_id}":
                        cached["title"] = ld.get("title", cached["title"])
                return cached

    local_dict: Dict[str, Any] = {}
    if local_data is not None:
        local_dict = (local_data.to_dict() if isinstance(local_data, pd.Series)
                      else dict(local_data))

    api_result = None
    if is_api_configured(api_key):
        if movie_id > 0:
            api_result = fetch_tmdb_movie_details(movie_id, api_key=api_key)
        if not api_result and local_dict.get("title"):
            api_result = search_tmdb_movie(
                title=str(local_dict["title"]),
                year=local_dict.get("release_year"),
                language=local_dict.get("original_language"),
                api_key=api_key,
            )

    if api_result:
        metadata = _parse_tmdb_response(api_result, movie_id, region=region)
        if not metadata["overview"] and local_dict.get("overview"):
            metadata["overview"] = str(local_dict["overview"])
        # Safety net: resolve poster if API response had no poster_path
        if not metadata["poster_url"]:
            metadata["poster_url"] = resolve_poster_url(
                movie_id=movie_id,
                title=metadata.get("title", local_dict.get("title", "")),
                year=metadata.get("release_year", local_dict.get("release_year", 0)),
                language=metadata.get("original_language",
                                      local_dict.get("original_language", "")),
                existing_poster_url=local_dict.get("poster_url"),
                existing_poster_path=local_dict.get("poster_path"),
                api_key=api_key,
            )
        elif metadata["poster_url"] and movie_id > 0:
            _persist_poster_url(movie_id, metadata["poster_url"])
    else:
        metadata = _build_fallback_metadata(movie_id, local_dict or None, region=region)
        if not metadata["poster_url"] and movie_id > 0:
            disk_poster = _get_disk_cached_poster(movie_id)
            if disk_poster:
                metadata["poster_url"] = disk_poster

    # Ensure streaming info is populated
    if "streaming" not in metadata or not metadata["streaming"].get("available"):
        metadata["streaming"] = get_streaming_providers(
            movie_id=movie_id, region=region, api_key=api_key, use_cache=use_cache
        )

    if use_cache:
        with _CACHE_LOCK:
            _METADATA_CACHE[cache_key] = metadata.copy()

    return metadata


def get_batch_movie_metadata(
    movie_list: Union[List[Dict[str, Any]], pd.DataFrame],
    api_key: Optional[str] = None,
    region: str = "IN",
) -> List[Dict[str, Any]]:
    """
    Fetch full metadata for a list or DataFrame of movies in parallel using ThreadPoolExecutor.
    """
    if isinstance(movie_list, pd.DataFrame):
        records = movie_list.to_dict(orient="records")
    else:
        records = list(movie_list)

    if not records:
        return []

    def _fetch_single(item):
        movie_id = item.get("id") or item.get("tmdb_id") or 0
        meta = get_movie_metadata(int(movie_id), local_data=item, api_key=api_key, region=region)
        if "similarity_score" in item:
            meta["similarity_score"] = item["similarity_score"]
        return meta

    max_workers = min(12, max(1, len(records)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(_fetch_single, records))

    return results


def clear_metadata_cache() -> None:
    """Clear in-memory metadata cache."""
    with _CACHE_LOCK:
        _METADATA_CACHE.clear()


def clear_poster_disk_cache() -> None:
    """Clear both in-memory and on-disk poster caches."""
    global _POSTER_DISK_CACHE
    with _POSTER_CACHE_LOCK:
        _POSTER_DISK_CACHE = {}
        try:
            if os.path.exists(_POSTER_CACHE_FILE):
                os.remove(_POSTER_CACHE_FILE)
        except Exception:
            pass


def clear_person_disk_cache() -> None:
    """Clear both in-memory and on-disk person caches."""
    global _PERSON_DISK_CACHE
    with _PERSON_CACHE_LOCK:
        _PERSON_DISK_CACHE = {}
        try:
            if os.path.exists(_PERSON_CACHE_FILE):
                os.remove(_PERSON_CACHE_FILE)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 8. ACTOR & ACTRESS PROFILES (TMDB PERSON API)
# ---------------------------------------------------------------------------

def fetch_person_details(
    person_id: int,
    api_key: Optional[str] = None,
    timeout: float = DEFAULT_TIMEOUT_SEC,
) -> Optional[Dict[str, Any]]:
    """
    Fetch comprehensive actor/director details from TMDB /person/{id}
    with known-for movie credits and caching.
    """
    pid = int(person_id) if person_id else 0
    if pid <= 0:
        return None

    # Check disk cache first
    cached = _get_disk_cached_person(pid)
    if cached:
        return cached

    key = get_api_key(api_key)
    if not key:
        return None

    url = f"{TMDB_BASE_URL}/person/{pid}"
    params, headers = _build_request_auth(key)
    params["append_to_response"] = "movie_credits"
    params["language"] = "en-US"

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            return None
        data = resp.json()

        # Parse known-for movies
        credits_data = data.get("movie_credits", {}) or {}
        raw_movies = credits_data.get("cast", [])
        if not raw_movies and data.get("known_for_department") == "Directing":
            raw_movies = credits_data.get("crew", [])

        # Deduplicate and sort by vote_count / popularity
        seen = set()
        known_for = []
        for m in sorted(raw_movies, key=lambda x: (x.get("vote_count", 0), x.get("popularity", 0)), reverse=True):
            mid = m.get("id")
            if not mid or mid in seen:
                continue
            seen.add(mid)
            p_path = m.get("poster_path")
            r_date = str(m.get("release_date") or "")
            r_year = int(r_date[:4]) if len(r_date) >= 4 and r_date[:4].isdigit() else 0
            known_for.append({
                "id": mid,
                "title": m.get("title") or m.get("original_title") or f"Movie #{mid}",
                "character": m.get("character", ""),
                "release_year": r_year,
                "vote_average": float(m.get("vote_average", 0.0)),
                "poster_url": f"{TMDB_IMAGE_BASE_URL}{p_path}" if p_path else None,
            })
            if len(known_for) >= 12:
                break

        prof_path = data.get("profile_path")
        profile_url = f"{TMDB_PROFILE_BASE_URL}{prof_path}" if prof_path else None

        info = {
            "id": pid,
            "name": data.get("name", ""),
            "also_known_as": data.get("also_known_as", []),
            "biography": data.get("biography", "") or "",
            "birthday": data.get("birthday", ""),
            "place_of_birth": data.get("place_of_birth", "") or "",
            "known_for_department": data.get("known_for_department", "Acting"),
            "profile_path": prof_path,
            "profile_url": profile_url,
            "popularity": float(data.get("popularity", 0.0)),
            "known_for": known_for,
        }

        _persist_person_info(pid, info)
        return info

    except Exception as exc:
        print(f"[movie_metadata] Error fetching person {pid}: {exc}")
        return None


def search_tmdb_person(
    name: str,
    api_key: Optional[str] = None,
    timeout: float = DEFAULT_TIMEOUT_SEC,
) -> List[Dict[str, Any]]:
    """
    Search for actors or directors by name using TMDB /search/person.
    """
    key = get_api_key(api_key)
    if not key or not name or not str(name).strip():
        return []

    url = f"{TMDB_BASE_URL}/search/person"
    params, headers = _build_request_auth(key)
    params["query"] = str(name).strip()
    params["include_adult"] = "false"
    params["language"] = "en-US"

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            return []
        results = resp.json().get("results", [])
        persons = []
        for p in results[:8]:
            p_path = p.get("profile_path")
            persons.append({
                "id": p.get("id"),
                "name": p.get("name"),
                "known_for_department": p.get("known_for_department", "Acting"),
                "profile_url": f"{TMDB_PROFILE_BASE_URL}{p_path}" if p_path else None,
            })
        return persons
    except Exception:
        return []


__all__ = [
    "discover_indian_movies",
    "save_indian_movies_cache",
    "get_movie_metadata",
    "get_batch_movie_metadata",
    "resolve_poster_url",
    "fetch_watch_providers",
    "get_streaming_providers",
    "fetch_person_details",
    "search_tmdb_person",
    "is_api_configured",
    "get_api_key",
    "clear_metadata_cache",
    "clear_poster_disk_cache",
    "clear_streaming_cache",
    "clear_person_disk_cache",
    "SUPPORTED_INDIAN_LANGUAGES",
    "TMDB_IMAGE_BASE_URL",
    "TMDB_BACKDROP_BASE_URL",
    "TMDB_LOGO_BASE_URL",
    "TMDB_PROFILE_BASE_URL",
]
