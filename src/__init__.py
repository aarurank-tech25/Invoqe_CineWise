"""
src package initialization.
"""

from src.movie_metadata import (
    discover_indian_movies,
    get_movie_metadata,
    get_batch_movie_metadata,
    is_api_configured,
    get_api_key,
    SUPPORTED_INDIAN_LANGUAGES,
)
from src.recommender import MovieRecommender
from src.preprocessing import preprocess_pipeline, load_data, clean_data
from src.database import init_db

__all__ = [
    "discover_indian_movies",
    "get_movie_metadata",
    "get_batch_movie_metadata",
    "is_api_configured",
    "get_api_key",
    "SUPPORTED_INDIAN_LANGUAGES",
    "MovieRecommender",
    "preprocess_pipeline",
    "load_data",
    "clean_data",
    "init_db",
]
