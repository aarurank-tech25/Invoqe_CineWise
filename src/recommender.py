"""
recommender.py - Content-Based Movie Recommendation Engine
===========================================================
This module provides the core recommendation logic:
  1. Build an index mapping movie titles → dataframe row indices.
  2. For a given movie, compute cosine similarity against ALL other
     movies using sklearn's linear_kernel (fast, memory-efficient).
  3. Support language filtering and genre filtering.
  4. Return the top-k most similar movies ranked by similarity score.

Key design decisions:
  - We do NOT pre-compute a full 10 000 × 10 000 similarity matrix.
    Instead we compute similarity only for the selected movie on-the-fly.
  - Duplicate titles are handled by using internal movie IDs;
    in the UI we show (title + release_year) to disambiguate.
  - All recommendations come strictly from TF-IDF cosine similarity computation.
"""

from typing import List, Optional
import pandas as pd
from sklearn.metrics.pairwise import linear_kernel

from src.preprocessing import preprocess_pipeline


class MovieRecommender:
    """Content-Based Movie Recommendation Engine."""

    def __init__(self, csv_path: str = None):
        """
        Initialize the recommender:
          - Run the full preprocessing pipeline
          - Build a title → index lookup for fast search
        """
        self.csv_path = csv_path
        self._load_and_index()

    def _load_and_index(self):
        """Run preprocessing pipeline and rebuild lookup indices."""
        self.df, self.tfidf_matrix, self.vectorizer = preprocess_pipeline(self.csv_path)

        # Build lookup: lowercase title -> list of indices
        self._title_to_indices = {}
        for idx, title in enumerate(self.df["title"]):
            key = str(title).strip().lower()
            if key not in self._title_to_indices:
                self._title_to_indices[key] = []
            self._title_to_indices[key].append(idx)

        print(f"[recommender] Engine ready — {len(self.df)} movies indexed")

    def reload(self):
        """Reload the dataset and recompute TF-IDF matrix (e.g. after new discoveries)."""
        self._load_and_index()

    def get_all_titles(self, language_filter: Optional[str] = None) -> List[str]:
        """
        Return a list of movie titles (with release year for display).
        Optionally filtered by original language code.
        """
        if language_filter and language_filter != "All":
            filtered_df = self.df[self.df["original_language"] == language_filter]
        else:
            filtered_df = self.df

        titles = []
        for _, row in filtered_df.iterrows():
            year = row.get("release_year", 0)
            try:
                year = int(year)
            except Exception:
                year = 0
            label = f"{row['title']} ({year})" if year > 0 else str(row["title"])
            titles.append(label)
        return titles

    def get_languages(self) -> List[str]:
        """Return sorted list of unique original_language codes."""
        return sorted(self.df["original_language"].dropna().unique().tolist())

    def get_movies_by_language(self, language_code: Optional[str] = None, limit: int = 50) -> pd.DataFrame:
        """Get top popular movies for a specific language."""
        if language_code and language_code != "All":
            sub_df = self.df[self.df["original_language"] == language_code]
        else:
            sub_df = self.df
        return sub_df.sort_values(by=["vote_average", "popularity"], ascending=False).head(limit)

    def search_titles(self, query: str, limit: int = 20) -> pd.DataFrame:
        """Search for movies whose title contains the query string."""
        mask = self.df["title"].astype(str).str.contains(query, case=False, na=False)
        return self.df[mask].head(limit)

    def recommend(
        self,
        movie_title: str = None,
        movie_index: int = None,
        top_k: int = 10,
        language_filter: str = None,
    ) -> pd.DataFrame:
        """
        Recommend top-k similar movies for a given movie using TF-IDF cosine similarity.
        """
        if movie_index is not None:
            idx = movie_index
        elif movie_title is not None:
            key = str(movie_title).strip().lower()
            # If formatted like "Vikram (2022)"
            if "(" in key and key.endswith(")"):
                base_title = key[:key.rfind("(")].strip()
                if base_title in self._title_to_indices:
                    idx = self._title_to_indices[base_title][0]
                elif key in self._title_to_indices:
                    idx = self._title_to_indices[key][0]
                else:
                    raise ValueError(f"Movie '{movie_title}' not found in dataset.")
            elif key in self._title_to_indices:
                idx = self._title_to_indices[key][0]
            else:
                raise ValueError(f"Movie '{movie_title}' not found in dataset.")
        else:
            raise ValueError("Provide either 'movie_title' or 'movie_index'.")

        # Cosine similarity via linear_kernel
        similarity_scores = linear_kernel(
            self.tfidf_matrix[idx],
            self.tfidf_matrix
        ).flatten()

        similar_indices = similarity_scores.argsort()[::-1]

        results = []
        for sim_idx in similar_indices:
            if sim_idx == idx:
                continue

            row = self.df.iloc[sim_idx]

            # Apply language filter if specified
            if language_filter and language_filter != "All" and row["original_language"] != language_filter:
                continue

            results.append({
                "id": int(row["id"]),
                "tmdb_id": int(row.get("tmdb_id", row["id"])),
                "title": str(row["title"]),
                "release_year": int(row.get("release_year", 0)),
                "genre": str(row.get("genre", "Unknown")),
                "original_language": str(row.get("original_language", "en")),
                "overview": str(row.get("overview", "")),
                "popularity": float(row.get("popularity", 0.0)),
                "vote_average": float(row.get("vote_average", 0.0)),
                "vote_count": int(row.get("vote_count", 0)),
                "poster_path": row.get("poster_path", None),
                "poster_url": row.get("poster_url", None),
                "cast": row.get("cast", None),
                "director": row.get("director", None),
                "similarity_score": round(float(similarity_scores[sim_idx]), 4),
            })

            if len(results) >= top_k:
                break

        return pd.DataFrame(results)

    def recommend_external(
        self,
        movie_data: dict,
        top_k: int = 10,
        language_filter: Optional[str] = None,
        genre_filter: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Recommend similar movies for an external/uncataloged TMDB movie using TF-IDF cosine similarity.
        Projects the external movie's content features (title, overview, genre, language)
        into the existing TF-IDF vector space, and computes cosine similarity against all catalog movies.
        """
        title = str(movie_data.get("title", "")).strip()
        overview = str(movie_data.get("overview", "")).strip()
        genre = str(movie_data.get("genre", movie_data.get("genre_str", "unknown"))).replace(",", " ")
        lang = str(movie_data.get("original_language", "en")).strip().lower()

        profile = f"{title.lower()} {overview.lower()} {genre.lower()} {lang}"
        query_vec = self.vectorizer.transform([profile])

        similarity_scores = linear_kernel(query_vec, self.tfidf_matrix).flatten()
        similar_indices = similarity_scores.argsort()[::-1]

        external_id = int(movie_data.get("id") or movie_data.get("tmdb_id") or 0)
        results = []
        for sim_idx in similar_indices:
            row = self.df.iloc[sim_idx]
            if external_id > 0 and int(row["id"]) == external_id:
                continue

            if language_filter and language_filter != "All" and row["original_language"] != language_filter:
                continue

            if genre_filter and genre_filter != "All" and genre_filter.lower() not in str(row.get("genre", "")).lower():
                continue

            results.append({
                "id": int(row["id"]),
                "tmdb_id": int(row.get("tmdb_id", row["id"])),
                "title": str(row["title"]),
                "release_year": int(row.get("release_year", 0)),
                "genre": str(row.get("genre", "Unknown")),
                "original_language": str(row.get("original_language", "en")),
                "overview": str(row.get("overview", "")),
                "popularity": float(row.get("popularity", 0.0)),
                "vote_average": float(row.get("vote_average", 0.0)),
                "vote_count": int(row.get("vote_count", 0)),
                "poster_path": row.get("poster_path", None),
                "poster_url": row.get("poster_url", None),
                "cast": row.get("cast", None),
                "director": row.get("director", None),
                "similarity_score": round(float(similarity_scores[sim_idx]), 4),
            })

            if len(results) >= top_k:
                break

        return pd.DataFrame(results)

    def recommend_by_id(
        self, movie_id: int, top_k: int = 10, language_filter: str = None, genre_filter: str = None
    ) -> pd.DataFrame:
        """Recommend similar movies using the TMDB movie id, seamlessly supporting uncataloged movies."""
        matches = self.df[self.df["id"] == movie_id]
        if not matches.empty:
            row_index = matches.index[0]
            return self.recommend(movie_index=row_index, top_k=top_k, language_filter=language_filter)

        # Uncataloged movie: fetch metadata from TMDB and use content-based recommend_external
        from src.movie_metadata import get_movie_metadata
        meta = get_movie_metadata(movie_id)
        if meta and (meta.get("title") or meta.get("overview")):
            return self.recommend_external(
                meta, top_k=top_k, language_filter=language_filter, genre_filter=genre_filter
            )

        raise ValueError(f"Movie id {movie_id} not found in the dataset or TMDB.")


if __name__ == "__main__":
    engine = MovieRecommender()
    print("Testing recommend for Vikram:")
    recs = engine.recommend("Vikram", top_k=5)
    print(recs[["title", "genre", "similarity_score"]])
