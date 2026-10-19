"""
CineWise - Curated Movie Discovery & Recommendation Platform
============================================================
A refined, cinema-focused web application delivering content-based movie
recommendations powered by TF-IDF Vectorization and Cosine Similarity, with
live TMDB metadata, real movie photography, and Where to Watch (OTT) availability.

Design Philosophy:
  - Human-designed editorial cinema aesthetic (clean typography, subtle borders, natural hierarchy)
  - Authentic movie presentation with real TMDB posters & graceful fallback
  - Streaming availability (Where to Watch) via TMDB Watch Providers
  - Clear, grounded AI communication without futuristic neon or sci-fi gimmicks
"""

import os
import sys
from typing import Optional, List, Dict, Any

# Ensure project root is always first in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import streamlit as st
import pandas as pd

from src.recommender import MovieRecommender
from src.movie_metadata import (
    get_movie_metadata,
    get_batch_movie_metadata,
    get_streaming_providers,
    is_api_configured,
    get_api_key,
    discover_indian_movies,
    save_indian_movies_cache,
    clear_metadata_cache,
    clear_poster_disk_cache,
    clear_streaming_cache,
    SUPPORTED_INDIAN_LANGUAGES,
    TMDB_IMAGE_BASE_URL,
)
from src.database import (
    init_db,
    register_user,
    login_user,
    add_favorite,
    remove_favorite,
    get_favorites,
    get_favorite_count,
)


# ═══════════════════════════════════════════════════════════════════════════
# 1. PAGE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="CineWise — Movie Discovery & Recommendations",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ═══════════════════════════════════════════════════════════════════════════
# 2. DESIGN SYSTEM & HUMAN-CRAFTED CINEMA CSS
# ═══════════════════════════════════════════════════════════════════════════

def inject_custom_css():
    """Inject a human-designed, refined dark cinema aesthetic."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Base App Typography & Dark Canvas ── */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    .stApp {
        background-color: #0d0f14;
        color: #e2e8f0;
    }

    /* ── Remove unnecessary Streamlit chrome ── */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ── Editorial Header / Masthead ── */
    .cinewise-masthead {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 20px;
        background: #13171f;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        margin-bottom: 24px;
    }
    .masthead-brand {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .masthead-icon {
        font-size: 1.6em;
        line-height: 1;
    }
    .masthead-title {
        font-size: 1.35em;
        font-weight: 700;
        color: #f8fafc;
        margin: 0;
        letter-spacing: -0.3px;
    }
    .masthead-subtitle {
        font-size: 0.78em;
        color: #94a3b8;
        margin: 2px 0 0 0;
        font-weight: 400;
        letter-spacing: 0.3px;
    }

    /* ── Editorial Intro Hero ── */
    .hero-intro {
        padding: 24px 20px;
        background: #13171f;
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        margin-bottom: 20px;
    }
    .hero-heading {
        font-size: 1.85em;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: -0.5px;
        margin: 0 0 8px 0;
    }
    .hero-description {
        font-size: 0.95em;
        color: #94a3b8;
        line-height: 1.6;
        margin: 0;
        max-width: 760px;
    }

    /* ── Clean Restrained Badges ── */
    .badge {
        display: inline-flex;
        align-items: center;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75em;
        font-weight: 500;
        margin-right: 6px;
        margin-bottom: 6px;
        background: #1c212c;
        color: #cbd5e1;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .badge-match {
        background: #1e2638;
        color: #93c5fd;
        border: 1px solid #3b82f6;
        font-weight: 600;
    }
    .badge-rating {
        background: rgba(245, 158, 11, 0.1);
        color: #f59e0b;
        border: 1px solid rgba(245, 158, 11, 0.25);
    }
    .badge-lang {
        background: #1a2233;
        color: #60a5fa;
        border: 1px solid rgba(96, 165, 250, 0.25);
        text-transform: uppercase;
        font-weight: 600;
    }
    .badge-ott {
        background: #18202f;
        color: #e2e8f0;
        border: 1px solid rgba(255, 255, 255, 0.12);
        padding: 4px 9px;
        font-size: 0.75em;
        font-weight: 500;
        border-radius: 6px;
        margin-right: 6px;
        margin-bottom: 6px;
    }

    /* ── Movie Poster Styling ── */
    .poster-wrap {
        width: 100%;
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.4);
    }
    .poster-placeholder-large {
        width: 100%;
        min-height: 380px;
        background: #13171f;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: #64748b;
        padding: 20px;
        text-align: center;
    }
    .poster-placeholder-thumb {
        width: 100%;
        min-height: 220px;
        background: #13171f;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: #64748b;
        padding: 12px;
        text-align: center;
    }

    /* ── Where to Watch Section ── */
    .ott-container {
        margin: 14px 0 10px 0;
        padding: 10px 14px;
        background: #11141b;
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 8px;
    }
    .ott-label {
        font-size: 0.75em;
        font-weight: 600;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }

    /* ── AI Recommendation Reason ── */
    .ai-reason-box {
        font-size: 0.82em;
        color: #94a3b8;
        background: #11141c;
        border-left: 3px solid #3b82f6;
        padding: 7px 12px;
        border-radius: 0 6px 6px 0;
        margin: 8px 0 10px 0;
    }

    /* ── Section Title ── */
    .section-title {
        font-size: 1.35em;
        font-weight: 700;
        color: #ffffff;
        margin: 22px 0 12px 0;
        letter-spacing: -0.3px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* ── Empty State ── */
    .empty-state {
        text-align: center;
        padding: 40px 20px;
        background: #13171f;
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        margin: 20px 0;
    }

    /* ── Footer ── */
    .cinewise-footer {
        text-align: center;
        color: #64748b;
        font-size: 0.82em;
        padding: 32px 0 16px 0;
        border-top: 1px solid rgba(255, 255, 255, 0.06);
        margin-top: 48px;
    }
    </style>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# 3. ENGINE INITIALIZATION & PERSISTENT SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner="Loading movie recommendation index...")
def load_engine():
    """Load and cache the movie recommendation engine."""
    return MovieRecommender()


def init_session_state():
    """Initialize persistent session state variables."""
    defaults = {
        "logged_in": False,
        "user": None,
        "page": "home",
        "api_key_override": "",
        "active_selected_movie": "",
        "active_language_filter": "All Languages",
        "streaming_region": "IN",
        "explore_genre_filter": "All",
        "explore_lang_filter": "All",
        "explore_search_query": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ═══════════════════════════════════════════════════════════════════════════
# 4. AI FEATURE EXTRACTION & SUBTLE INSIGHTS
# ═══════════════════════════════════════════════════════════════════════════

def extract_ai_match_insights(selected_meta: dict, rec_meta: dict) -> Dict[str, Any]:
    """
    Dynamically extract why the AI recommended this movie based on shared
    content features (genres, language, and key thematic overview tokens).
    Does NOT use hardcoded rules or fake explanations.
    """
    sel_genres = set([g.lower().strip() for g in selected_meta.get("genres", []) if g])
    rec_genres = set([g.lower().strip() for g in rec_meta.get("genres", []) if g])
    shared_genres = [g.title() for g in (sel_genres & rec_genres)]

    sel_lang = str(selected_meta.get("original_language", "")).lower().strip()
    rec_lang = str(rec_meta.get("original_language", "")).lower().strip()
    same_lang = (sel_lang == rec_lang) and bool(sel_lang)

    stopwords = {
        "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "with",
        "by", "from", "of", "about", "into", "through", "during", "after",
        "before", "is", "are", "was", "were", "be", "been", "being", "have",
        "has", "had", "do", "does", "did", "this", "that", "these", "those",
        "it", "its", "he", "him", "his", "she", "her", "they", "them", "their",
        "who", "which", "what", "when", "where", "why", "how", "all", "any",
        "both", "each", "few", "more", "most", "other", "some", "such", "no",
        "not", "only", "own", "same", "so", "than", "too", "very", "can",
        "will", "just", "should", "now", "movie", "film", "story", "life",
        "one", "two", "new", "man", "woman", "time", "world", "young", "find",
        "must", "take", "make", "get", "see", "come", "go", "also", "back"
    }

    def tokenize(text: str) -> set:
        clean = "".join([c.lower() if c.isalnum() else " " for c in text])
        return {w for w in clean.split() if len(w) > 3 and w not in stopwords}

    sel_tokens = tokenize(selected_meta.get("overview", ""))
    rec_tokens = tokenize(rec_meta.get("overview", ""))
    shared_themes = sorted(list(sel_tokens & rec_tokens))[:3]

    return {
        "shared_genres": shared_genres,
        "same_language": same_lang,
        "shared_themes": shared_themes,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 5. UI COMPONENTS: POSTERS & STREAMING AVAILABILITY
# ═══════════════════════════════════════════════════════════════════════════

def render_movie_poster(poster_url: Optional[str], title: str, is_large: bool = False, year: int = 0):
    """
    Render movie poster with natural, human-designed proportions:
      - Valid image URL -> rendered cleanly with st.image
      - Missing or broken poster -> understated professional placeholder card
    """
    if poster_url and isinstance(poster_url, str):
        url = poster_url.strip()
        if url and url not in ("nan", "None") and url.startswith(("http://", "https://")):
            try:
                st.image(url, use_container_width=True)
                return
            except Exception:
                pass

    css_class = "poster-placeholder-large" if is_large else "poster-placeholder-thumb"
    year_str = f"({year})" if year > 0 else ""
    st.markdown(f"""
    <div class="{css_class}">
        <div style="font-size:1.8em; margin-bottom:8px;">🎬</div>
        <div style="font-size:0.88em; font-weight:600; color:#cbd5e1; margin-bottom:4px; line-height:1.2;">
            {title}
        </div>
        <div style="font-size:0.75em; color:#64748b; margin-bottom:8px;">{year_str}</div>
        <span class="badge" style="background:#1a202c; color:#94a3b8; font-size:0.7em;">
            Poster unavailable
        </span>
    </div>
    """, unsafe_allow_html=True)


def render_where_to_watch_section(streaming_info: dict, region_code: str):
    """Render Where to Watch (OTT) section in selected movie hero."""
    providers = streaming_info.get("providers", []) if streaming_info else []
    link = streaming_info.get("link") if streaming_info else None
    available = bool(streaming_info and streaming_info.get("available") and providers)

    st.markdown(f"""
    <div class="ott-container">
        <div class="ott-label">Where to Watch ({region_code.upper()}):</div>
    """, unsafe_allow_html=True)

    if available:
        badges_html = "".join([f'<span class="badge-ott">📺 {p}</span>' for p in providers[:5]])
        link_html = f'<a href="{link}" target="_blank" style="color:#60a5fa; font-size:0.78em; margin-left:8px; text-decoration:none;">View Options on JustWatch ↗</a>' if link else ""
        st.markdown(f"<div>{badges_html}{link_html}</div></div>", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="color:#64748b; font-size:0.82em;">
            Streaming availability unavailable
        </div>
        </div>
        """, unsafe_allow_html=True)


def render_selected_movie_hero(meta: dict, is_fav: bool, user_id: Optional[int], region_code: str = "IN"):
    """Render refined, editorial presentation of the selected movie."""
    st.markdown('<div class="section-title">Selected Movie</div>', unsafe_allow_html=True)

    with st.container(border=True):
        col_poster, col_info = st.columns([1.1, 2.9])

        with col_poster:
            render_movie_poster(
                meta.get("poster_url"),
                meta["title"],
                is_large=True,
                year=meta.get("release_year", 0)
            )

        with col_info:
            year_val = f"({meta['release_year']})" if meta.get("release_year", 0) > 0 else ""
            orig_title_part = (
                f'<span style="color:#64748b; font-size:0.8em; font-weight:400; margin-left:6px;">'
                f'[{meta["original_title"]}]</span>'
                if meta.get("original_title") and meta["original_title"] != meta["title"] else ""
            )

            st.markdown(f"""
            <h2 style="margin:0 0 4px 0; font-size:1.75em; font-weight:700; color:#fff;">
                {meta['title']} <span style="color:#94a3b8; font-size:0.8em; font-weight:400;">{year_val}</span>
                {orig_title_part}
            </h2>
            """, unsafe_allow_html=True)

            if meta.get("tagline"):
                st.markdown(f"""
                <p style="color:#94a3b8; font-style:italic; font-size:0.88em; margin:0 0 10px 0;">
                    "{meta['tagline']}"
                </p>
                """, unsafe_allow_html=True)

            # Badges Row: Rating, Language, Genres
            genre_badges = "".join([f'<span class="badge">{g}</span>' for g in meta.get("genres", [])])
            if not genre_badges:
                genre_badges = f'<span class="badge">{meta.get("genre_str", "Unknown")}</span>'

            raw_lang = str(meta.get("original_language", "")).lower()
            lang_display = SUPPORTED_INDIAN_LANGUAGES.get(raw_lang, raw_lang.upper())
            lang_badge = f'<span class="badge badge-lang">{lang_display}</span>' if raw_lang else ""
            rating_badge = f'<span class="badge badge-rating">⭐ {meta.get("vote_average", 0.0):.1f} / 10 ({meta.get("vote_count", 0):,} votes)</span>'

            st.markdown(f"""
            <div style="margin: 6px 0 12px 0;">
                {rating_badge}
                {lang_badge}
                {genre_badges}
            </div>
            """, unsafe_allow_html=True)

            # Director & Cast
            if meta.get("director"):
                st.markdown(f"""
                <p style="margin: 4px 0; color:#cbd5e1; font-size:0.88em;">
                    <strong style="color:#94a3b8;">Director:</strong> {meta['director']}
                </p>
                """, unsafe_allow_html=True)

            if meta.get("cast_names"):
                cast_str = " • ".join(meta["cast_names"][:5])
                st.markdown(f"""
                <p style="margin: 4px 0 10px 0; color:#cbd5e1; font-size:0.88em;">
                    <strong style="color:#94a3b8;">Cast:</strong> {cast_str}
                </p>
                """, unsafe_allow_html=True)

            # Synopsis
            overview_text = meta.get("overview") or "No synopsis available for this title."
            st.markdown(f"""
            <p style="color:#cbd5e1; line-height:1.55; font-size:0.92em; margin-bottom:12px;">
                {overview_text}
            </p>
            """, unsafe_allow_html=True)

            # Where to Watch (OTT)
            render_where_to_watch_section(meta.get("streaming", {}), region_code=region_code)

            # Action Buttons Row
            if user_id:
                col_btn, _ = st.columns([1.6, 2.4])
                with col_btn:
                    if is_fav:
                        if st.button("💔 Remove Favorite", key=f"hero_fav_del_{meta['id']}", use_container_width=True):
                            remove_favorite(user_id, meta["id"])
                            st.rerun()
                    else:
                        if st.button("♡ Save to Favorites", key=f"hero_fav_add_{meta['id']}", type="primary", use_container_width=True):
                            add_favorite(user_id, meta["id"])
                            st.rerun()
            else:
                st.caption("Sign in to save this title to your favorites.")


def render_recommendation_card(
    rec_meta: dict,
    selected_meta: dict,
    rank: int,
    is_fav: bool,
    user_id: Optional[int],
    region_code: str = "IN",
):
    """Render a clean, human-designed movie recommendation card with Where to Watch."""
    with st.container(border=True):
        col_img, col_details = st.columns([1, 3.2])

        with col_img:
            render_movie_poster(
                rec_meta.get("poster_url"),
                rec_meta["title"],
                is_large=False,
                year=rec_meta.get("release_year", 0)
            )

        with col_details:
            sim_pct = rec_meta.get("similarity_score", 0.0) * 100
            year_val = f"({rec_meta['release_year']})" if rec_meta.get("release_year", 0) > 0 else ""

            col_title, col_score = st.columns([3, 1.2])
            with col_title:
                st.markdown(f"""
                <h3 style="margin:0; font-size:1.25em; color:#ffffff; font-weight:700;">
                    <span style="color:#60a5fa; font-weight:500;">#{rank}</span> {rec_meta['title']}
                    <span style="color:#94a3b8; font-size:0.8em; font-weight:400;">{year_val}</span>
                </h3>
                """, unsafe_allow_html=True)
            with col_score:
                st.markdown(f"""
                <div style="text-align:right;">
                    <span class="badge badge-match">Match {sim_pct:.0f}%</span>
                </div>
                """, unsafe_allow_html=True)

            # Badges Row
            genre_badges = "".join([f'<span class="badge">{g}</span>' for g in rec_meta.get("genres", [])])
            if not genre_badges:
                genre_badges = f'<span class="badge">{rec_meta.get("genre_str", "Unknown")}</span>'

            rating_badge = f'<span class="badge badge-rating">⭐ {rec_meta.get("vote_average", 0.0):.1f}</span>'
            raw_lang = str(rec_meta.get("original_language", "")).lower()
            lang_display = SUPPORTED_INDIAN_LANGUAGES.get(raw_lang, raw_lang.upper())
            lang_badge = f'<span class="badge badge-lang">{lang_display}</span>' if raw_lang else ""

            st.markdown(f"""
            <div style="margin: 4px 0 8px 0;">
                {rating_badge}
                {lang_badge}
                {genre_badges}
            </div>
            """, unsafe_allow_html=True)

            # Where to Watch snippet
            streaming = rec_meta.get("streaming", {})
            providers = streaming.get("providers", []) if streaming else []
            if providers:
                prov_str = " • ".join(providers[:3])
                ott_line = f"<div style='font-size:0.82em; color:#cbd5e1; margin-bottom:6px;'>📺 <strong>Available on:</strong> {prov_str}</div>"
            else:
                ott_line = "<div style='font-size:0.82em; color:#64748b; margin-bottom:6px;'>📺 Streaming availability unavailable</div>"
            st.markdown(ott_line, unsafe_allow_html=True)

            # Subtle AI Explanation
            insights = extract_ai_match_insights(selected_meta, rec_meta)
            why_parts = []
            if insights["shared_genres"]:
                why_parts.append(f"similar genres ({', '.join(insights['shared_genres'][:2])})")
            if insights["shared_themes"]:
                why_parts.append(f"shared themes ({', '.join(insights['shared_themes'][:2])})")
            if insights["same_language"]:
                why_parts.append(f"same language ({lang_display})")
            
            why_desc = ", and ".join(why_parts) if why_parts else "content and narrative alignment"
            st.markdown(f"""
            <div class="ai-reason-box">
                Recommended because it shares {why_desc} with {selected_meta['title']}.
            </div>
            """, unsafe_allow_html=True)

            # Synopsis preview
            overview = rec_meta.get("overview") or "No synopsis available."
            if len(overview) > 190:
                overview = overview[:188] + "..."
            st.markdown(f"""
            <p style="color:#94a3b8; font-size:0.86em; line-height:1.5; margin:0 0 10px 0;">
                {overview}
            </p>
            """, unsafe_allow_html=True)

            # Action Buttons Row
            col_b1, col_b2, _ = st.columns([1.5, 2.0, 2.5])
            with col_b1:
                if user_id:
                    if is_fav:
                        if st.button("💔 Saved", key=f"rec_unfav_{rec_meta['id']}_{rank}", use_container_width=True):
                            remove_favorite(user_id, rec_meta["id"])
                            st.rerun()
                    else:
                        if st.button("♡ Favorite", key=f"rec_fav_{rec_meta['id']}_{rank}", use_container_width=True):
                            add_favorite(user_id, rec_meta["id"])
                            st.rerun()
            with col_b2:
                pivot_label = f"{rec_meta['title']} ({rec_meta['release_year']})" if rec_meta.get("release_year", 0) > 0 else rec_meta['title']
                if st.button("✨ Recommend From This", key=f"rec_pivot_{rec_meta['id']}_{rank}", use_container_width=True):
                    st.session_state["active_selected_movie"] = pivot_label
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# 6. TOP NAVIGATION & SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════

STREAMING_REGIONS = {
    "India (IN)": "IN",
    "United States (US)": "US",
    "United Kingdom (GB)": "GB",
    "Canada (CA)": "CA",
    "Australia (AU)": "AU",
}

def render_top_navbar():
    """Render top editorial navigation bar with active route indicators."""
    current_page = st.session_state.page
    
    st.markdown("""
    <div class="cinewise-masthead">
        <div class="masthead-brand">
            <span class="masthead-icon">🎬</span>
            <div>
                <p class="masthead-title">CineWise</p>
                <p class="masthead-subtitle">Curated Movie Discovery & AI Recommendations</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_nav1, col_nav2, col_nav3, col_nav4, col_nav5, col_user = st.columns([1.1, 1.1, 1.2, 1.4, 1.1, 2.1])
    
    with col_nav1:
        if st.button("Home", type="primary" if current_page == "home" else "secondary", use_container_width=True, key="top_nav_home"):
            st.session_state.page = "home"
            st.rerun()
    with col_nav2:
        if st.button("Explore", type="primary" if current_page == "explore" else "secondary", use_container_width=True, key="top_nav_explore"):
            st.session_state.page = "explore"
            st.rerun()
    with col_nav3:
        if st.button("Favorites", type="primary" if current_page == "favorites" else "secondary", use_container_width=True, key="top_nav_fav"):
            st.session_state.page = "favorites"
            st.rerun()
    with col_nav4:
        if st.button("How AI Works", type="primary" if current_page == "how_ai_works" else "secondary", use_container_width=True, key="top_nav_how"):
            st.session_state.page = "how_ai_works"
            st.rerun()
    with col_nav5:
        if st.button("Profile", type="primary" if current_page == "profile" else "secondary", use_container_width=True, key="top_nav_profile"):
            st.session_state.page = "profile"
            st.rerun()
    with col_user:
        if st.session_state.logged_in:
            user = st.session_state.user
            st.markdown(f"""
            <div style="text-align:right; padding-top:6px;">
                <span style="color:#94a3b8; font-size:0.82em;">Account: </span>
                <strong style="color:#fff;">{user['name']}</strong>
            </div>
            """, unsafe_allow_html=True)
        else:
            col_l, col_r = st.columns(2)
            with col_l:
                if st.button("Sign In", use_container_width=True, key="top_nav_signin"):
                    st.session_state.page = "login"
                    st.rerun()
            with col_r:
                if st.button("Register", use_container_width=True, key="top_nav_signup"):
                    st.session_state.page = "register"
                    st.rerun()


def render_sidebar(engine: MovieRecommender):
    """Render sidebar navigation, TMDB API status, and discovery tools."""
    with st.sidebar:
        st.markdown("""
        <div style="padding: 6px 0 12px 0;">
            <h3 style="margin:0; font-size:1.3em; color:#fff; font-weight:700;">
                🎬 CineWise
            </h3>
            <p style="color:#7881a5; font-size:0.8em; margin-top:2px;">
                Content-Based Recommendation Platform
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Streaming Region Selector
        st.markdown("<p style='color:#cbd5e1; font-size:0.85em; font-weight:600; margin-bottom:4px;'>Streaming Region (OTT):</p>", unsafe_allow_html=True)
        region_labels = list(STREAMING_REGIONS.keys())
        current_region_code = st.session_state.get("streaming_region", "IN")
        current_idx = [v for v in STREAMING_REGIONS.values()].index(current_region_code) if current_region_code in STREAMING_REGIONS.values() else 0
        selected_region_label = st.selectbox(
            "Region",
            options=region_labels,
            index=current_idx,
            label_visibility="collapsed",
            key="sb_region_select"
        )
        st.session_state["streaming_region"] = STREAMING_REGIONS[selected_region_label]

        st.markdown("---")

        # User Status & Quick Navigation
        if st.session_state.logged_in:
            user = st.session_state.user
            fav_count = get_favorite_count(user["id"])
            st.markdown(f"""
            <div style="background: #141720; border: 1px solid rgba(255,255,255,0.08); border-radius:8px; padding:12px; margin-bottom:12px;">
                <p style="margin:0; color:#7d85aa; font-size:0.75em; text-transform:uppercase; letter-spacing:0.5px;">Logged In</p>
                <p style="margin:2px 0 0 0; color:#fff; font-weight:600; font-size:0.95em;">{user['name']}</p>
                <p style="margin:4px 0 0 0; color:#94a3b8; font-size:0.78em;">⭐ {fav_count} Favorites</p>
            </div>
            """, unsafe_allow_html=True)

            if st.button("Log Out", use_container_width=True, key="side_nav_logout"):
                st.session_state.logged_in = False
                st.session_state.user = None
                st.session_state.page = "home"
                st.rerun()
        else:
            st.markdown("""
            <div style="background:#141720; border:1px solid rgba(255,255,255,0.06); border-radius:8px; padding:10px; margin-bottom:12px;">
                <p style="margin:0; color:#94a3b8; font-size:0.82em;">Sign in to save favorites and track watched movies.</p>
            </div>
            """, unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Login", use_container_width=True, key="side_nav_login"):
                    st.session_state.page = "login"
                    st.rerun()
            with col2:
                if st.button("Register", use_container_width=True, key="side_nav_register"):
                    st.session_state.page = "register"
                    st.rerun()

        st.markdown("---")

        # TMDB API Metadata Status & Settings
        effective_key = get_api_key(st.session_state.get("api_key_override"))
        api_active = bool(effective_key)

        if api_active:
            st.markdown("""
            <div style="background:rgba(16, 185, 129, 0.1); border:1px solid #059669; border-radius:6px; padding:8px 10px; margin-bottom:10px;">
                <p style="margin:0; color:#34d399; font-size:0.78em; font-weight:600;">
                    🟢 TMDB API Connected
                </p>
                <p style="margin:2px 0 0 0; color:#a0a8cc; font-size:0.7em;">
                    Live Posters, Credits & OTT Providers active
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:rgba(245, 158, 11, 0.1); border:1px solid #d97706; border-radius:6px; padding:8px 10px; margin-bottom:10px;">
                <p style="margin:0; color:#fbbf24; font-size:0.78em; font-weight:600;">
                    🟡 Local Dataset Mode
                </p>
                <p style="margin:2px 0 0 0; color:#a0a8cc; font-size:0.7em;">
                    10K movies active. Add key below for live posters & OTT.
                </p>
            </div>
            """, unsafe_allow_html=True)

        with st.expander("API & Cache Settings", expanded=False):
            st.caption("Provide a TMDB API key to enable live poster lookup & OTT streaming availability.")
            input_key = st.text_input(
                "TMDB API Key",
                value=st.session_state.get("api_key_override", ""),
                type="password",
                placeholder="Paste 32-character key",
                help="You can also set TMDB_API_KEY as an environment variable or in .streamlit/secrets.toml.",
            )
            if input_key != st.session_state.get("api_key_override", ""):
                st.session_state["api_key_override"] = input_key
                clear_metadata_cache()
                st.rerun()

            if api_active:
                if st.button("🔄 Sync Indian Movies from TMDB", use_container_width=True, key="btn_sync_tmdb"):
                    with st.spinner("Discovering Indian movies across Tamil, Malayalam, Telugu, Kannada, Hindi..."):
                        all_discovered = []
                        for lang_code in ["ta", "ml", "te", "kn", "hi"]:
                            movies = discover_indian_movies(lang_code, api_key=effective_key, max_pages=3)
                            all_discovered.extend(movies)
                        if all_discovered:
                            total = save_indian_movies_cache(all_discovered)
                            clear_metadata_cache()
                            engine.reload()
                            st.success(f"Discovered & cached {len(all_discovered)} movies (Total in cache: {total})!")
                            st.rerun()
                        else:
                            st.warning("No new movies returned by TMDB API.")

            if st.button("Clear Metadata Cache", use_container_width=True, key="btn_clear_cache"):
                clear_metadata_cache()
                clear_streaming_cache()
                st.success("Caches refreshed!")

        # Dataset Engine Summary
        st.markdown("---")
        st.markdown(f"""
        <div style="color:#64748b; font-size:0.78em; line-height:1.5;">
            <strong>Indexed Movies:</strong> {len(engine.df):,}<br/>
            <strong>Vector Dimensions:</strong> 12,000 N-Grams<br/>
            <strong>Algorithm:</strong> Cosine Similarity
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# 7. PAGE: HOME (DISCOVERY & RECOMMENDATIONS)
# ═══════════════════════════════════════════════════════════════════════════

LANGUAGE_CATEGORY_MAP = {
    "All Languages": "All",
    "Tamil": "ta",
    "Malayalam": "ml",
    "Telugu": "te",
    "Kannada": "kn",
    "Hindi": "hi",
    "English": "en",
}

def page_home(engine: MovieRecommender):
    """Render CineWise primary search, showcase, and recommendation pipeline."""
    st.markdown("""
    <div class="hero-intro">
        <h1 class="hero-heading">Discover your next favorite movie.</h1>
        <p class="hero-description">
            Select a film to explore kindred stories, themes, and narrative styles.
            Our content-based recommendation model analyzes full synopsis profiles,
            genres, and language to find authentic cinematic matches.
        </p>
    </div>
    """, unsafe_allow_html=True)

    df = engine.df
    all_genres_set = set()
    for g in df["genre"].dropna():
        for genre in g.split(","):
            genre = genre.strip()
            if genre and genre != "unknown":
                all_genres_set.add(genre)
    all_genres = ["All"] + sorted(all_genres_set)

    lang_display_options = list(LANGUAGE_CATEGORY_MAP.keys())
    region_code = st.session_state.get("streaming_region", "IN")

    # ── Search & Filter Controls ──
    with st.container(border=True):
        col_lang, col_search, col_genre, col_k = st.columns([1.2, 2.6, 1.2, 0.8])

        with col_lang:
            selected_lang_display = st.selectbox(
                "Language Filter",
                options=lang_display_options,
                index=lang_display_options.index(st.session_state.get("active_language_filter", "All Languages")),
                key="lang_filter_select",
            )
            st.session_state["active_language_filter"] = selected_lang_display
            selected_lang_code = LANGUAGE_CATEGORY_MAP.get(selected_lang_display, "All")

        title_lang_filter = None if selected_lang_code == "All" else selected_lang_code
        available_titles = engine.get_all_titles(language_filter=title_lang_filter)
        search_options = [""] + available_titles

        with col_search:
            current_active = st.session_state.get("active_selected_movie", "")
            current_index = search_options.index(current_active) if current_active in search_options else 0
            selected_title = st.selectbox(
                "Search & Select Movie",
                options=search_options,
                index=current_index,
                key="movie_search_select",
                help="Type to search any movie from our catalog.",
            )
            if selected_title != st.session_state.get("active_selected_movie", ""):
                st.session_state["active_selected_movie"] = selected_title

        with col_genre:
            selected_genre = st.selectbox("Genre Filter", options=all_genres, index=0, key="home_genre_filter")

        with col_k:
            top_k = st.selectbox("Results", options=[5, 10, 15], index=1, key="home_top_k")

        recommend_clicked = st.button("Find Recommendations", use_container_width=True, type="primary", key="btn_run_rec")

    # API key and user context
    api_key = get_api_key(st.session_state.get("api_key_override"))
    user_id = st.session_state.user["id"] if st.session_state.logged_in else None
    user_favs = get_favorites(user_id) if user_id else []

    # ── EMPTY STATE / SHOWCASE WHEN NO MOVIE SELECTED ──
    if not selected_title:
        st.markdown('<div class="section-title">Featured Cinema</div>', unsafe_allow_html=True)
        st.caption("Select any featured movie below or search above to generate recommendations.")

        showcase_lang = selected_lang_code if selected_lang_code != "All" else None
        showcase_movies = engine.get_movies_by_language(showcase_lang, limit=8)

        if not showcase_movies.empty:
            cols = st.columns(4)
            for idx, (_, row) in enumerate(showcase_movies.iterrows()):
                col = cols[idx % 4]
                meta = get_movie_metadata(int(row["id"]), local_data=row, api_key=api_key, region=region_code)
                with col:
                    with st.container(border=True):
                        render_movie_poster(
                            meta.get("poster_url"),
                            meta["title"],
                            is_large=False,
                            year=meta.get("release_year", 0)
                        )
                        st.markdown(f"**{meta['title']}** ({meta['release_year']})")
                        st.markdown(
                            f"<span class='badge badge-rating'>⭐ {meta['vote_average']:.1f}</span> "
                            f"<span class='badge'>{meta['genre_str'].split(',')[0]}</span>",
                            unsafe_allow_html=True
                        )
                        label_match = f"{meta['title']} ({meta['release_year']})" if meta['release_year'] > 0 else meta['title']
                        if st.button("Select Movie", key=f"showcase_pick_{meta['id']}", use_container_width=True):
                            st.session_state["active_selected_movie"] = label_match
                            st.rerun()

    # ── ACTIVE RECOMMENDATION PIPELINE ──
    if selected_title and selected_title != "":
        # Resolve selected movie row
        if "(" in selected_title and selected_title.endswith(")"):
            title_part = selected_title[:selected_title.rfind("(")].strip()
            year_part = selected_title[selected_title.rfind("(") + 1:-1].strip()
            try:
                year_int = int(year_part)
                matched_rows = df[(df["title"].str.lower() == title_part.lower()) & (df["release_year"] == year_int)]
            except Exception:
                matched_rows = df[df["title"].str.lower() == title_part.lower()]
        else:
            matched_rows = df[df["title"].str.lower() == selected_title.lower()]

        if matched_rows.empty:
            matched_rows = df[df["title"].str.contains(selected_title, case=False, na=False)]

        if not matched_rows.empty:
            movie_row = matched_rows.iloc[0]
            selected_idx = matched_rows.index[0]
            selected_movie_id = int(movie_row["id"])

            with st.spinner("Finding movie details..."):
                selected_meta = get_movie_metadata(
                    selected_movie_id, local_data=movie_row, api_key=api_key, region=region_code
                )

            # 1. Selected Movie Hero Card
            is_hero_fav = selected_movie_id in user_favs
            render_selected_movie_hero(
                selected_meta, is_fav=is_hero_fav, user_id=user_id, region_code=region_code
            )

            # 2. Compute Content-Based Recommendations
            with st.spinner("Building your recommendations..."):
                lang_filter = None if selected_lang_code == "All" else selected_lang_code
                extra_k = top_k * 4 if selected_genre != "All" else top_k
                recs_df = engine.recommend(movie_index=selected_idx, top_k=extra_k, language_filter=lang_filter)

                if selected_genre != "All" and not recs_df.empty:
                    recs_df = recs_df[recs_df["genre"].str.contains(selected_genre, case=False, na=False)]
                    recs_df = recs_df.head(top_k)

            # 3. Render Recommendation Results
            st.markdown(f'<div class="section-title">Similar Movies</div>', unsafe_allow_html=True)
            st.caption(f"Recommendations based on story content and themes similar to {selected_meta['title']}.")

            if recs_df.empty:
                st.warning("No recommendations matched your active filters. Try setting genre filter to 'All'.")
            else:
                with st.spinner("Fetching cinematic metadata & streaming availability..."):
                    rec_records = recs_df.to_dict(orient="records")
                    recs_meta_list = get_batch_movie_metadata(rec_records, api_key=api_key, region=region_code)

                for rank, rec_meta in enumerate(recs_meta_list, start=1):
                    is_fav = rec_meta["id"] in user_favs
                    render_recommendation_card(
                        rec_meta=rec_meta,
                        selected_meta=selected_meta,
                        rank=rank,
                        is_fav=is_fav,
                        user_id=user_id,
                        region_code=region_code,
                    )
        else:
            st.error(f"Could not load details for movie '{selected_title}'. Please try another search term.")

    elif recommend_clicked:
        st.info("Please select a movie from the search box above to begin discovery.")


# ═══════════════════════════════════════════════════════════════════════════
# 8. PAGE: EXPLORE (CATALOG DISCOVERY)
# ═══════════════════════════════════════════════════════════════════════════

def page_explore(engine: MovieRecommender):
    """Render catalog exploration interface allowing browsing by language, genre, and year."""
    st.markdown('<div class="section-title" style="font-size:1.6em;">Explore Catalog</div>', unsafe_allow_html=True)
    st.markdown('<p style="color:#94a3b8; font-size:0.92em;">Browse over 10,000 films across international and Indian cinemas. Select any title to view details and recommendations.</p>', unsafe_allow_html=True)

    df = engine.df
    api_key = get_api_key(st.session_state.get("api_key_override"))
    region_code = st.session_state.get("streaming_region", "IN")

    all_genres_set = set()
    for g in df["genre"].dropna():
        for genre in g.split(","):
            genre = genre.strip()
            if genre and genre != "unknown":
                all_genres_set.add(genre)
    all_genres = ["All"] + sorted(all_genres_set)

    with st.container(border=True):
        col_q, col_l, col_g, col_sort = st.columns([2.5, 1.2, 1.2, 1.3])

        with col_q:
            search_query = st.text_input("Search Title", value=st.session_state.get("explore_search_query", ""), placeholder="e.g. Vikram, Inception, Interstellar")
            st.session_state["explore_search_query"] = search_query

        with col_l:
            lang_options = list(LANGUAGE_CATEGORY_MAP.keys())
            explore_lang_disp = st.selectbox("Language", options=lang_options, index=0)
            explore_lang_code = LANGUAGE_CATEGORY_MAP.get(explore_lang_disp, "All")

        with col_g:
            explore_genre = st.selectbox("Genre", options=all_genres, index=0)

        with col_sort:
            sort_by = st.selectbox("Sort By", options=["Popularity", "Highest Rated", "Newest", "Oldest"], index=0)

    filtered = df.copy()
    if search_query.strip():
        filtered = filtered[filtered["title"].astype(str).str.contains(search_query.strip(), case=False, na=False)]

    if explore_lang_code != "All":
        filtered = filtered[filtered["original_language"] == explore_lang_code]

    if explore_genre != "All":
        filtered = filtered[filtered["genre"].str.contains(explore_genre, case=False, na=False)]

    if sort_by == "Popularity":
        filtered = filtered.sort_values(by="popularity", ascending=False)
    elif sort_by == "Highest Rated":
        filtered = filtered.sort_values(by=["vote_average", "vote_count"], ascending=[False, False])
    elif sort_by == "Newest":
        filtered = filtered.sort_values(by="release_year", ascending=False)
    elif sort_by == "Oldest":
        filtered = filtered.sort_values(by="release_year", ascending=True)

    st.markdown(f"<p style='color:#94a3b8; font-size:0.85em; margin:12px 0 8px 0;'>Showing <strong>{min(len(filtered), 24)}</strong> of <strong>{len(filtered):,}</strong> titles</p>", unsafe_allow_html=True)

    if filtered.empty:
        st.markdown("""
        <div class="empty-state">
            <h3 style="color:#fff; margin-bottom:4px;">No movies found</h3>
            <p style="color:#94a3b8; margin:0;">Try adjusting your search query or relaxing your genre and language filters.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    display_subset = filtered.head(24)
    cols = st.columns(4)

    for idx, (_, row) in enumerate(display_subset.iterrows()):
        col = cols[idx % 4]
        meta = get_movie_metadata(int(row["id"]), local_data=row, api_key=api_key, region=region_code)
        with col:
            with st.container(border=True):
                render_movie_poster(
                    meta.get("poster_url"),
                    meta["title"],
                    is_large=False,
                    year=meta.get("release_year", 0)
                )
                st.markdown(f"**{meta['title']}** ({meta['release_year']})")
                
                raw_lang = str(meta.get("original_language", "")).lower()
                lang_disp = SUPPORTED_INDIAN_LANGUAGES.get(raw_lang, raw_lang.upper())
                genre_chip = meta['genre_str'].split(',')[0]
                st.markdown(
                    f"<span class='badge badge-rating'>⭐ {meta['vote_average']:.1f}</span> "
                    f"<span class='badge badge-lang'>{lang_disp}</span> "
                    f"<span class='badge'>{genre_chip}</span>",
                    unsafe_allow_html=True
                )
                
                label_match = f"{meta['title']} ({meta['release_year']})" if meta['release_year'] > 0 else meta['title']
                if st.button("Select & Recommend", key=f"explore_btn_{meta['id']}", use_container_width=True):
                    st.session_state["active_selected_movie"] = label_match
                    st.session_state.page = "home"
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# 9. PAGE: HOW AI WORKS
# ═══════════════════════════════════════════════════════════════════════════

def page_how_it_works():
    """Render technical architecture documentation with clean engineering styling."""
    st.markdown('<div class="section-title" style="font-size:1.8em;">How the Recommendation System Works</div>', unsafe_allow_html=True)
    st.markdown("""
    <p style="color:#94a3b8; font-size:0.95em; max-width:780px; margin-bottom:20px; line-height:1.6;">
        CineWise is a content-based recommendation system that compares textual movie features
        rather than relying on popularity rankings or user clickstream data.
    </p>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.markdown("""
            <h4 style="color:#f8fafc; margin-top:0;">1. Movie Selection</h4>
            <p style="color:#94a3b8; font-size:0.88em; line-height:1.6;">
                The user selects a movie of interest. This film serves as the query profile against which the entire catalog is evaluated.
            </p>
            """, unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("""
            <h4 style="color:#f8fafc; margin-top:0;">2. Feature Extraction</h4>
            <p style="color:#94a3b8; font-size:0.88em; line-height:1.6;">
                A composite text document is created for each movie:
                <br/><code style="color:#cbd5e1;">Profile = Title + Genre + Synopsis Overview + Language</code>
            </p>
            """, unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("""
            <h4 style="color:#f8fafc; margin-top:0;">3. TF-IDF Vectorization</h4>
            <p style="color:#94a3b8; font-size:0.88em; line-height:1.6;">
                The text is converted into a 12,000-dimensional numerical feature space using scikit-learn's TF-IDF vectorizer with unigram and bigram tokenization.
            </p>
            """, unsafe_allow_html=True)

    with col2:
        with st.container(border=True):
            st.markdown("""
            <h4 style="color:#f8fafc; margin-top:0;">4. Cosine Similarity</h4>
            <p style="color:#94a3b8; font-size:0.88em; line-height:1.6;">
                Cosine similarity measures the angle between the query movie's vector and every candidate movie vector:
                <br/><code style="color:#cbd5e1;">Cosine Similarity(A, B) = (A &bull; B) / (||A|| &times; ||B||)</code>
            </p>
            """, unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("""
            <h4 style="color:#f8fafc; margin-top:0;">5. Ranking by Similarity</h4>
            <p style="color:#94a3b8; font-size:0.88em; line-height:1.6;">
                Candidate movies are ranked strictly by descending similarity score. Vote counts, ratings, and popularity metrics are metadata and do not alter recommendation rank.
            </p>
            """, unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("""
            <h4 style="color:#f8fafc; margin-top:0;">6. Decoupled TMDB Metadata & OTT</h4>
            <p style="color:#94a3b8; font-size:0.88em; line-height:1.6;">
                External APIs (TMDB & Watch Providers) enrich results with posters, credits, and streaming availability. If external services fail, recommendations continue seamlessly.
            </p>
            """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# 10. PAGE: FAVORITES
# ═══════════════════════════════════════════════════════════════════════════

def page_favorites(engine: MovieRecommender):
    """Render user-specific saved favorites with remove and recommendation triggers."""
    user = st.session_state.user
    user_id = user["id"]
    fav_ids = get_favorites(user_id)
    region_code = st.session_state.get("streaming_region", "IN")

    st.markdown('<div class="section-title" style="font-size:1.6em;">Saved Favorites</div>', unsafe_allow_html=True)

    if not fav_ids:
        st.markdown("""
        <div class="empty-state">
            <h3 style="color:#fff; margin-bottom:4px;">No favorites saved yet</h3>
            <p style="color:#94a3b8; margin:0 0 16px 0;">
                Browse movies in Explore or search on Home and click 'Favorite' to build your personal list.
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Explore Movies", type="primary", key="btn_fav_empty_goto_explore"):
            st.session_state.page = "explore"
            st.rerun()
        return

    st.markdown(f'<p style="color:#94a3b8; font-size:0.88em;">You have saved <strong>{len(fav_ids)}</strong> movie(s).</p>', unsafe_allow_html=True)

    api_key = get_api_key(st.session_state.get("api_key_override"))
    df = engine.df

    for fav_movie_id in fav_ids:
        match = df[df["id"] == fav_movie_id]
        local_row = match.iloc[0] if not match.empty else {"id": fav_movie_id, "title": f"Movie #{fav_movie_id}"}
        meta = get_movie_metadata(fav_movie_id, local_data=local_row, api_key=api_key, region=region_code)

        with st.container(border=True):
            col_img, col_info, col_actions = st.columns([1, 3.2, 1.2])

            with col_img:
                render_movie_poster(
                    meta.get("poster_url"),
                    meta["title"],
                    is_large=False,
                    year=meta.get("release_year", 0)
                )

            with col_info:
                year_val = f"({meta['release_year']})" if meta.get("release_year", 0) > 0 else ""
                st.markdown(f"""
                <h3 style="margin:0; color:#fff; font-weight:700; font-size:1.2em;">
                    {meta['title']} <span style="color:#94a3b8; font-size:0.8em; font-weight:400;">{year_val}</span>
                </h3>
                """, unsafe_allow_html=True)

                genre_badges = "".join([f'<span class="badge">{g}</span>' for g in meta.get("genres", [])])
                if not genre_badges:
                    genre_badges = f'<span class="badge">{meta.get("genre_str", "Unknown")}</span>'

                rating_badge = f'<span class="badge badge-rating">⭐ {meta.get("vote_average", 0.0):.1f}</span>'
                raw_lang = str(meta.get("original_language", "")).lower()
                lang_display = SUPPORTED_INDIAN_LANGUAGES.get(raw_lang, raw_lang.upper())
                lang_badge = f'<span class="badge badge-lang">{lang_display}</span>' if raw_lang else ""

                st.markdown(f"""
                <div style="margin:4px 0 8px 0;">
                    {rating_badge}
                    {lang_badge}
                    {genre_badges}
                </div>
                """, unsafe_allow_html=True)

                # Streaming preview
                streaming = meta.get("streaming", {})
                providers = streaming.get("providers", []) if streaming else []
                if providers:
                    st.markdown(f"<p style='color:#cbd5e1; font-size:0.82em; margin:2px 0;'>📺 <strong>Available on:</strong> {', '.join(providers[:3])}</p>", unsafe_allow_html=True)

                overview = meta.get("overview") or ""
                if len(overview) > 170:
                    overview = overview[:168] + "..."
                st.markdown(f'<p style="color:#94a3b8; font-size:0.85em; margin:4px 0 0 0;">{overview}</p>', unsafe_allow_html=True)

            with col_actions:
                st.markdown("<br/>", unsafe_allow_html=True)
                label_match = f"{meta['title']} ({meta['release_year']})" if meta['release_year'] > 0 else meta['title']
                if st.button("Recommend", key=f"fav_rec_{fav_movie_id}", use_container_width=True, type="primary"):
                    st.session_state["active_selected_movie"] = label_match
                    st.session_state.page = "home"
                    st.rerun()

                if st.button("Remove", key=f"fav_del_{fav_movie_id}", use_container_width=True):
                    remove_favorite(user_id, fav_movie_id)
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# 11. PAGE: PROFILE
# ═══════════════════════════════════════════════════════════════════════════

def page_profile():
    """Render user profile and account statistics."""
    user = st.session_state.user
    fav_count = get_favorite_count(user["id"])

    st.markdown('<div class="section-title" style="font-size:1.6em;">User Profile</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.caption("Name")
            st.subheader(user['name'])
    with col2:
        with st.container(border=True):
            st.caption("Saved Favorites")
            st.subheader(f"{fav_count} titles")
    with col3:
        with st.container(border=True):
            st.caption("Member Since")
            st.subheader(user['created_at'][:10])

    st.markdown("<br/>", unsafe_allow_html=True)
    with st.container(border=True):
        st.subheader("Account Details")
        st.markdown(f"**Email:** `{user['email']}`")
        st.markdown(f"**Registration Date:** `{user['created_at']}`")
        st.markdown(f"**Target Region:** `{st.session_state.get('streaming_region', 'IN')}`")

        col_p1, col_p2, _ = st.columns([1.5, 1.5, 3])
        with col_p1:
            if st.button("View Favorites", use_container_width=True, type="primary"):
                st.session_state.page = "favorites"
                st.rerun()
        with col_p2:
            if st.button("Log Out", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.user = None
                st.session_state.page = "home"
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# 12. AUTHENTICATION PAGES: LOGIN & REGISTER
# ═══════════════════════════════════════════════════════════════════════════

def page_login():
    """Render user login interface."""
    st.markdown('<div class="section-title" style="justify-content:center; font-size:1.8em;">Sign In to CineWise</div>', unsafe_allow_html=True)
    st.markdown('<p style="text-align:center; color:#8892b0; margin-bottom:20px;">Access your personalized recommendations and saved favorites.</p>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        with st.container(border=True):
            st.subheader("Login")
            email = st.text_input("Email", key="login_email", placeholder="you@example.com")
            password = st.text_input("Password", type="password", key="login_password", placeholder="Enter your password")

            if st.button("Sign In", use_container_width=True, type="primary", key="btn_login"):
                if not email or not password:
                    st.error("Please provide both email and password.")
                else:
                    result = login_user(email, password)
                    if result["success"]:
                        st.session_state.logged_in = True
                        st.session_state.user = result["user"]
                        st.session_state.page = "home"
                        st.rerun()
                    else:
                        st.error(result["message"])

            st.markdown("---")
            st.caption("Don't have an account?")
            if st.button("Create an Account", use_container_width=True, key="btn_goto_register"):
                st.session_state.page = "register"
                st.rerun()


def page_register():
    """Render user registration interface."""
    st.markdown('<div class="section-title" style="justify-content:center; font-size:1.8em;">Create CineWise Account</div>', unsafe_allow_html=True)
    st.markdown('<p style="text-align:center; color:#8892b0; margin-bottom:20px;">Join to build your personal library of saved movie recommendations.</p>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        with st.container(border=True):
            st.subheader("Register")
            name = st.text_input("Full Name", key="reg_name", placeholder="Alex Smith")
            email = st.text_input("Email", key="reg_email", placeholder="alex@example.com")
            password = st.text_input("Password", type="password", key="reg_password", placeholder="Min 6 characters")
            password2 = st.text_input("Confirm Password", type="password", key="reg_password2", placeholder="Confirm password")

            if st.button("Create Account", use_container_width=True, type="primary", key="btn_register"):
                if not name or not email or not password or not password2:
                    st.error("Please fill in all fields.")
                elif "@" not in email or "." not in email:
                    st.error("Please enter a valid email address.")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters long.")
                elif password != password2:
                    st.error("Passwords do not match.")
                else:
                    result = register_user(name, email, password)
                    if result["success"]:
                        st.success(result["message"])
                        st.session_state.page = "login"
                        st.rerun()
                    else:
                        st.error(result["message"])

            st.markdown("---")
            st.caption("Already registered?")
            if st.button("Back to Login", use_container_width=True, key="btn_goto_login"):
                st.session_state.page = "login"
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# 13. MAIN APPLICATION ROUTER
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Application entry point and routing coordinator."""
    inject_custom_css()
    init_db()
    init_session_state()

    engine = load_engine()
    render_sidebar(engine)
    render_top_navbar()

    page = st.session_state.page

    if page in ("login", "register") and st.session_state.logged_in:
        st.session_state.page = "home"
        page = "home"

    if page == "login":
        page_login()
    elif page == "register":
        page_register()
    elif page == "home":
        page_home(engine)
    elif page == "explore":
        page_explore(engine)
    elif page == "how_ai_works":
        page_how_it_works()
    elif page == "favorites":
        if not st.session_state.logged_in:
            st.session_state.page = "login"
            st.rerun()
        page_favorites(engine)
    elif page == "profile":
        if not st.session_state.logged_in:
            st.session_state.page = "login"
            st.rerun()
        page_profile()
    else:
        st.session_state.page = "home"
        page_home(engine)

    st.markdown("""
    <div class="cinewise-footer">
        <p style="margin:0 0 4px 0;"><strong>CineWise</strong> &bull; Movie Discovery & Recommendation Platform</p>
        <p style="margin:0; font-size:0.88em;">
            Content-Based TF-IDF & Cosine Similarity Engine &bull; Decoupled TMDB Metadata &bull; JustWatch Streaming Availability
        </p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
