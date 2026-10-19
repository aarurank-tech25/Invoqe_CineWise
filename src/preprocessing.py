"""
preprocessing.py - Data Loading & Cleaning for Movie Recommendation System
==========================================================================
This module handles:
  1. Loading the core 10K TMDB dataset without removing existing movies.
  2. Seamlessly integrating discovered/cached Indian movies from
     `data/tmdb_indian_movies.csv` (avoiding duplicate IDs).
  3. Handling missing values (genre → "unknown", overview → "").
  4. Extracting release year from release_date or preserving release_year.
  5. Building a combined text feature ("movie_profile") for TF-IDF:
     title + genre + overview + original_language
  6. Fitting the TF-IDF vectorizer and returning the sparse matrix.
"""

import os
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


# ---------------------------------------------------------------------------
# 1. DATA LOADING
# ---------------------------------------------------------------------------

def load_data(csv_path: str = None) -> pd.DataFrame:
    """
    Load the core TMDB movie dataset and merge discovered Indian movies
    from ``data/tmdb_indian_movies.csv`` into a unified dataset structure.

    Parameters
    ----------
    csv_path : str, optional
        Path to the primary CSV. If None, defaults to ``data/top10K-TMDB-movies.csv``.

    Returns
    -------
    pd.DataFrame
        Complete unified dataframe containing core movies plus cached Indian movies.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if csv_path is None:
        csv_path = os.path.join(base_dir, "data", "top10K-TMDB-movies.csv")

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found at: {csv_path}")

    df_base = pd.read_csv(csv_path)
    print(f"[preprocessing] Loaded {len(df_base)} core movies from {csv_path}")

    # Standardize base ID columns
    if "tmdb_id" not in df_base.columns and "id" in df_base.columns:
        df_base["tmdb_id"] = df_base["id"]

    # Seamlessly merge Indian movies cache if present
    indian_csv_path = os.path.join(base_dir, "data", "tmdb_indian_movies.csv")
    if os.path.exists(indian_csv_path):
        try:
            df_indian = pd.read_csv(indian_csv_path)
            # Normalize ID column
            if "tmdb_id" in df_indian.columns:
                if "id" not in df_indian.columns or df_indian["id"].isnull().any():
                    df_indian["id"] = df_indian["tmdb_id"]
            elif "id" in df_indian.columns:
                df_indian["tmdb_id"] = df_indian["id"]

            # Filter out movies that already exist in the base dataset by TMDB ID
            existing_ids = set(df_base["id"].dropna().astype(int))
            new_indian = df_indian[~df_indian["id"].astype(int).isin(existing_ids)].copy()

            if not new_indian.empty:
                # Combine both datasets
                df_combined = pd.concat([df_base, new_indian], ignore_index=True)
                df_combined = df_combined.drop_duplicates(subset=["id"], keep="first")
                print(f"[preprocessing] Integrated {len(new_indian)} Indian movies into dataset (Total: {len(df_combined)})")
                return df_combined
        except Exception as e:
            print(f"[preprocessing] Note: Could not merge Indian movies cache: {e}")

    return df_base


# ---------------------------------------------------------------------------
# 2. DATA CLEANING & SCHEMA UNIFICATION
# ---------------------------------------------------------------------------

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardize the dataframe schema:
      - id, tmdb_id: integer
      - genre: filled with "unknown"
      - overview: filled with ""
      - original_language: string (lowercase)
      - release_year: integer extracted from release_date or existing column
      - poster_url: constructed from poster_path when available
    """
    df = df.copy()

    # Ensure id and tmdb_id
    if "id" in df.columns and "tmdb_id" not in df.columns:
        df["tmdb_id"] = df["id"]
    elif "tmdb_id" in df.columns and "id" not in df.columns:
        df["id"] = df["tmdb_id"]

    df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
    df["tmdb_id"] = pd.to_numeric(df["tmdb_id"], errors="coerce").fillna(df["id"]).astype(int)

    # Handle missing genre values
    df["genre"] = df["genre"].fillna("unknown").astype(str)

    # Handle missing overview values
    df["overview"] = df["overview"].fillna("").astype(str)

    # Handle original_language
    df["original_language"] = df["original_language"].fillna("en").astype(str).str.lower().str.strip()

    # Extract or cast release_year
    if "release_year" in df.columns:
        parsed_year = pd.to_datetime(df["release_date"], errors="coerce").dt.year.fillna(0).astype(int)
        df["release_year"] = pd.to_numeric(df["release_year"], errors="coerce").fillna(parsed_year).astype(int)
    else:
        df["release_year"] = pd.to_datetime(
            df["release_date"], errors="coerce"
        ).dt.year.fillna(0).astype(int)

    # Construct poster_url from poster_path (vectorized — fast)
    if "poster_url" not in df.columns:
        df["poster_url"] = pd.NA

    if "poster_path" in df.columns:
        # Normalize poster_url: treat empty/nan/None as missing
        url_series = df["poster_url"].astype(str).str.strip()
        url_missing = url_series.isin(["", "nan", "None", "<NA>", "NaT"])

        path_series = df["poster_path"].astype(str).str.strip()
        path_valid = ~path_series.isin(["", "nan", "None", "<NA>", "NaT"])

        # Rows where URL is missing but poster_path exists
        needs_url = url_missing & path_valid

        if needs_url.any():
            paths = path_series[needs_url]
            constructed = np.where(
                paths.str.startswith("http://") | paths.str.startswith("https://"),
                paths,
                np.where(
                    paths.str.startswith("/"),
                    "https://image.tmdb.org/t/p/w500" + paths,
                    "https://image.tmdb.org/t/p/w500/" + paths,
                )
            )
            df.loc[needs_url, "poster_url"] = constructed

    # Final cleanup: replace string 'nan'/'None' with actual None
    df["poster_url"] = df["poster_url"].where(
        ~df["poster_url"].astype(str).str.strip().isin(["", "nan", "None", "<NA>", "NaT"]),
        other=None
    )

    print(f"[preprocessing] Cleaned dataset: {len(df)} movies ready")
    return df


# ---------------------------------------------------------------------------
# 3. FEATURE ENGINEERING — Movie Profile Representation
# ---------------------------------------------------------------------------

def build_movie_profiles(df: pd.DataFrame) -> pd.Series:
    """
    Build compatible text profile for every movie using:
    title + genre + overview + original_language

    This ensures both original 10K movies and TMDB-discovered Indian movies
    participate fairly in the same content-based recommendation system.
    """
    genre_clean = df["genre"].astype(str).str.replace(",", " ", regex=False)
    title_clean = df["title"].fillna("").astype(str).str.lower()
    overview_clean = df["overview"].fillna("").astype(str).str.lower()
    lang_clean = df["original_language"].fillna("en").astype(str).str.lower()

    profiles = (
        title_clean + " " +
        overview_clean + " " +
        genre_clean.str.lower() + " " +
        lang_clean
    )

    print(f"[preprocessing] Built movie profiles for {len(profiles)} movies")
    return profiles


# ---------------------------------------------------------------------------
# 4. TF-IDF VECTORIZATION
# ---------------------------------------------------------------------------

def build_tfidf_matrix(profiles: pd.Series):
    """
    Fit a TF-IDF vectorizer on the movie profiles and return the
    sparse TF-IDF matrix along with the fitted vectorizer.
    """
    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=12000,
        ngram_range=(1, 2),
    )

    tfidf_matrix = vectorizer.fit_transform(profiles)

    print(
        f"[preprocessing] TF-IDF matrix shape: {tfidf_matrix.shape} "
        f"(movies × features), sparse format"
    )
    return tfidf_matrix, vectorizer


# ---------------------------------------------------------------------------
# 5. PIPELINE RUNNER
# ---------------------------------------------------------------------------

def preprocess_pipeline(csv_path: str = None):
    """Run data loading, cleaning, profiling, and TF-IDF matrix creation."""
    df = load_data(csv_path)
    df = clean_data(df)
    profiles = build_movie_profiles(df)
    tfidf_matrix, vectorizer = build_tfidf_matrix(profiles)
    return df, tfidf_matrix, vectorizer


if __name__ == "__main__":
    df, tfidf_matrix, vectorizer = preprocess_pipeline()
    print("\n--- Pipeline Check ---")
    print(f"Total Movies: {len(df)}")
    print(f"Indian Movies sample (ta): {len(df[df['original_language'] == 'ta'])}")
    print(f"Sample titles: {df[df['original_language'] == 'ta']['title'].head().tolist()}")
