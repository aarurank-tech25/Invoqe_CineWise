"""
database.py - SQLite Database for User Login & Favorites
=========================================================
This module provides:
  1. Database initialization (creates tables if they don't exist)
  2. User registration with password hashing
  3. User login with password verification
  4. Add / remove / list favorite movies per user

Security:
  - Passwords are hashed using SHA-256 with a random salt
  - Plain-text passwords are NEVER stored
  - Each user's favorites are isolated by user_id

Tables:
  users     — id, name, email, password_hash, salt, created_at
  favorites — id, user_id, movie_id, created_at
"""

import os
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta, timezone


# ---------------------------------------------------------------------------
# DATABASE PATH
# ---------------------------------------------------------------------------

def _get_db_path() -> str:
    """Return the path to the SQLite database file."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "data", "movie_app.db")


# ---------------------------------------------------------------------------
# CONNECTION HELPER
# ---------------------------------------------------------------------------

def get_connection() -> sqlite3.Connection:
    """
    Open a connection to the SQLite database.
    Returns a connection with row_factory set to sqlite3.Row
    so results can be accessed like dictionaries.
    """
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row  # allows row["column_name"] access
    return conn


# ---------------------------------------------------------------------------
# 1. DATABASE INITIALIZATION
# ---------------------------------------------------------------------------

def init_db():
    """
    Create the 'users' and 'favorites' tables if they don't already exist.
    Call this once when the application starts.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # --- Users table ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            salt          TEXT    NOT NULL,
            created_at    TEXT    NOT NULL
        )
    """)

    # --- Favorites table ---
    # user_id references users(id), movie_id is the TMDB movie id
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            movie_id   INTEGER NOT NULL,
            created_at TEXT    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, movie_id)
        )
    """)

    # --- Password resets table ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            token_hash TEXT    NOT NULL UNIQUE,
            expires_at TEXT    NOT NULL,
            used       INTEGER NOT NULL DEFAULT 0,
            created_at TEXT    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # --- Watched history table ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS watched_history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            movie_id   INTEGER NOT NULL,
            rating     REAL    DEFAULT NULL,
            watched_at TEXT    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, movie_id)
        )
    """)

    # --- User preferences table ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id             INTEGER NOT NULL UNIQUE,
            preferred_languages TEXT    DEFAULT '[]',
            preferred_genres    TEXT    DEFAULT '[]',
            updated_at          TEXT    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# 2. PASSWORD HASHING
# ---------------------------------------------------------------------------

def _hash_password(password: str, salt: str = None) -> tuple:
    """
    Hash a password using SHA-256 with a random salt.

    Parameters
    ----------
    password : str
        The plain-text password to hash.
    salt : str, optional
        If provided, use this salt (for login verification).
        If None, generate a new random salt (for registration).

    Returns
    -------
    (password_hash, salt) : tuple of str
        The hex-encoded hash and the salt used.
    """
    if salt is None:
        # Generate a random 32-character hex salt
        salt = secrets.token_hex(16)

    # Combine salt + password and hash with SHA-256
    salted = salt + password
    password_hash = hashlib.sha256(salted.encode("utf-8")).hexdigest()

    return password_hash, salt


# ---------------------------------------------------------------------------
# 3. USER REGISTRATION
# ---------------------------------------------------------------------------

def register_user(name: str, email: str, password: str) -> dict:
    """
    Register a new user.

    Parameters
    ----------
    name : str
        User's display name.
    email : str
        User's email (must be unique).
    password : str
        Plain-text password (will be hashed before storage).

    Returns
    -------
    dict
        {"success": True, "message": "..."} on success.
        {"success": False, "message": "..."} on failure (e.g. duplicate email).
    """
    # Hash the password
    password_hash, salt = _hash_password(password)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO users (name, email, password_hash, salt, created_at) VALUES (?, ?, ?, ?, ?)",
            (name.strip(), email.strip().lower(), password_hash, salt, created_at),
        )
        conn.commit()
        return {"success": True, "message": "Registration successful! You can now log in."}
    except sqlite3.IntegrityError:
        # UNIQUE constraint on email failed → duplicate email
        return {"success": False, "message": "An account with this email already exists."}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 4. USER LOGIN
# ---------------------------------------------------------------------------

def login_user(email: str, password: str) -> dict:
    """
    Authenticate a user by email and password.

    Parameters
    ----------
    email : str
        User's email.
    password : str
        Plain-text password to verify.

    Returns
    -------
    dict
        On success: {"success": True, "user": {"id": ..., "name": ..., "email": ..., "created_at": ...}}
        On failure: {"success": False, "message": "..."}
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE email = ?",
        (email.strip().lower(),),
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return {"success": False, "message": "No account found with this email."}

    # Verify password: hash the input with the stored salt
    password_hash, _ = _hash_password(password, salt=row["salt"])

    if password_hash != row["password_hash"]:
        return {"success": False, "message": "Incorrect password."}

    # Login successful — return user info (never return the hash!)
    return {
        "success": True,
        "user": {
            "id": row["id"],
            "name": row["name"],
            "email": row["email"],
            "created_at": row["created_at"],
        },
    }

def get_user_by_email(email: str) -> dict | None:
    """Return user dict (id, name, email, created_at) if exists, else None."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, created_at FROM users WHERE email = ?", (email.strip().lower(),))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row["id"], "name": row["name"], "email": row["email"], "created_at": row["created_at"]}
    return None


# ---------------------------------------------------------------------------
# 5. FAVORITES — Add
# ---------------------------------------------------------------------------

def add_favorite(user_id: int, movie_id: int) -> dict:
    """
    Add a movie to the user's favorites.

    Parameters
    ----------
    user_id : int
        The logged-in user's id.
    movie_id : int
        The TMDB movie id to favorite.

    Returns
    -------
    dict
        {"success": True/False, "message": "..."}
    """
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO favorites (user_id, movie_id, created_at) VALUES (?, ?, ?)",
            (user_id, movie_id, created_at),
        )
        conn.commit()
        return {"success": True, "message": "Movie added to favorites!"}
    except sqlite3.IntegrityError:
        # UNIQUE(user_id, movie_id) constraint → already favorited
        return {"success": False, "message": "This movie is already in your favorites."}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 6. FAVORITES — Remove
# ---------------------------------------------------------------------------

def remove_favorite(user_id: int, movie_id: int) -> dict:
    """
    Remove a movie from the user's favorites.

    Parameters
    ----------
    user_id : int
        The logged-in user's id.
    movie_id : int
        The TMDB movie id to remove.

    Returns
    -------
    dict
        {"success": True/False, "message": "..."}
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM favorites WHERE user_id = ? AND movie_id = ?",
        (user_id, movie_id),
    )
    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    if deleted > 0:
        return {"success": True, "message": "Movie removed from favorites."}
    else:
        return {"success": False, "message": "Movie was not in your favorites."}


# ---------------------------------------------------------------------------
# 7. FAVORITES — List
# ---------------------------------------------------------------------------

def get_favorites(user_id: int) -> list:
    """
    Get all favorite movie ids for a user.

    Parameters
    ----------
    user_id : int
        The logged-in user's id.

    Returns
    -------
    list of int
        List of TMDB movie ids that the user has favorited.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT movie_id FROM favorites WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    return [row["movie_id"] for row in rows]


# ---------------------------------------------------------------------------
# 8. FAVORITES — Count
# ---------------------------------------------------------------------------

def get_favorite_count(user_id: int) -> int:
    """Return the total number of favorites for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM favorites WHERE user_id = ?",
        (user_id,),
    )
    count = cursor.fetchone()["cnt"]
    conn.close()
    return count


# ---------------------------------------------------------------------------
# 9. PASSWORD RESET & RECOVERY
# ---------------------------------------------------------------------------

def create_password_reset_token(email: str, expiry_minutes: int = 15) -> dict:
    """
    Generate a secure single-use password reset token for the given email.
    
    Security:
      - Validates user existence without leaking existence to callers.
      - Enforces rate limiting (max 3 requests per 15 minutes).
      - Stores ONLY the SHA-256 hash of the token in the database.
      - Sets an expiration timestamp.
    """
    clean_email = email.strip().lower()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email FROM users WHERE email = ?", (clean_email,))
    user = cursor.fetchone()

    # Generic response returned to protect user privacy (prevent account enumeration)
    generic_msg = "If an account exists for this email, password reset instructions have been sent."

    if not user:
        conn.close()
        return {
            "success": True,
            "user_found": False,
            "message": generic_msg,
            "raw_token": None,
            "user_name": None,
        }

    user_id = user["id"]
    user_name = user["name"]
    now_utc = datetime.now(timezone.utc)
    fifteen_min_ago = (now_utc - timedelta(minutes=15)).isoformat()

    # Rate limiting: max 3 requests in the last 15 minutes
    cursor.execute(
        "SELECT COUNT(*) as count FROM password_resets WHERE user_id = ? AND created_at >= ?",
        (user_id, fifteen_min_ago)
    )
    req_count = cursor.fetchone()["count"]
    if req_count >= 3:
        conn.close()
        return {
            "success": False,
            "rate_limited": True,
            "message": "Too many password reset requests. Please wait 15 minutes before trying again.",
            "raw_token": None,
            "user_name": None,
        }

    # Generate a cryptographically secure 32-byte urlsafe token
    raw_token = secrets.token_urlsafe(32)
    # Store ONLY SHA-256 hash of token
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    expires_at = (now_utc + timedelta(minutes=expiry_minutes)).isoformat()
    created_at = now_utc.isoformat()

    cursor.execute(
        """
        INSERT INTO password_resets (user_id, token_hash, expires_at, used, created_at)
        VALUES (?, ?, ?, 0, ?)
        """,
        (user_id, token_hash, expires_at, created_at),
    )
    conn.commit()
    conn.close()

    return {
        "success": True,
        "user_found": True,
        "user_name": user_name,
        "user_email": clean_email,
        "raw_token": raw_token,
        "message": generic_msg,
    }


def verify_password_reset_token(raw_token: str) -> dict:
    """
    Validate a password reset token without consuming it.
    Checks existence, single-use status, and expiration.
    """
    if not raw_token or not raw_token.strip():
        return {"valid": False, "message": "Invalid or missing reset token."}

    token_hash = hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT r.id, r.user_id, r.expires_at, r.used, u.email, u.name
        FROM password_resets r
        JOIN users u ON r.user_id = u.id
        WHERE r.token_hash = ?
        """,
        (token_hash,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"valid": False, "message": "This password reset link is invalid."}

    if row["used"] == 1:
        return {"valid": False, "message": "This password reset link has already been used."}

    try:
        expires_at = datetime.fromisoformat(row["expires_at"])
        # Support timezone-aware or naive comparison
        now_utc = datetime.now(timezone.utc)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if now_utc > expires_at:
            return {"valid": False, "message": "This password reset link has expired. Please request a new one."}
    except Exception:
        return {"valid": False, "message": "Invalid expiration timestamp on reset token."}

    return {
        "valid": True,
        "user_id": row["user_id"],
        "email": row["email"],
        "name": row["name"],
        "reset_id": row["id"],
    }


def reset_password_with_token(raw_token: str, new_password: str) -> dict:
    """
    Verify reset token, securely update password hash and salt,
    and invalidate token.
    """
    if not new_password or len(new_password) < 6:
        return {"success": False, "message": "Password must be at least 6 characters long."}

    token_check = verify_password_reset_token(raw_token)
    if not token_check["valid"]:
        return {"success": False, "message": token_check["message"]}

    user_id = token_check["user_id"]
    new_hash, new_salt = _hash_password(new_password)

    conn = get_connection()
    cursor = conn.cursor()

    # Update user's password and salt
    cursor.execute(
        "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
        (new_hash, new_salt, user_id),
    )

    # Invalidate all tokens for this user
    cursor.execute(
        "UPDATE password_resets SET used = 1 WHERE user_id = ?",
        (user_id,),
    )
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "Your password has been reset successfully. You can now sign in with your new password.",
    }


# ---------------------------------------------------------------------------
# 5. WATCHED HISTORY (PERSONALIZED VIEWING HISTORY)
# ---------------------------------------------------------------------------

def add_watched(user_id: int, movie_id: int, rating: float = None) -> dict:
    """
    Mark a movie as watched by the user with optional rating (1-10).
    """
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    try:
        cursor.execute(
            """
            INSERT INTO watched_history (user_id, movie_id, rating, watched_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, movie_id) DO UPDATE SET
                rating = COALESCE(excluded.rating, watched_history.rating),
                watched_at = excluded.watched_at
            """,
            (user_id, movie_id, rating, now),
        )
        conn.commit()
        return {"success": True, "message": "Marked as watched."}
    except Exception as exc:
        return {"success": False, "message": f"Error saving watched movie: {exc}"}
    finally:
        conn.close()


def remove_watched(user_id: int, movie_id: int) -> dict:
    """
    Remove a movie from the user's watched history.
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "DELETE FROM watched_history WHERE user_id = ? AND movie_id = ?",
            (user_id, movie_id),
        )
        conn.commit()
        if cursor.rowcount > 0:
            return {"success": True, "message": "Removed from watched history."}
        return {"success": False, "message": "Movie not found in watched history."}
    except Exception as exc:
        return {"success": False, "message": f"Database error: {exc}"}
    finally:
        conn.close()


def get_watched(user_id: int) -> list:
    """
    Return all watched movies for a given user, newest first.
    Returns list of dicts: [{'movie_id': int, 'rating': float, 'watched_at': str}]
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT movie_id, rating, watched_at
        FROM watched_history
        WHERE user_id = ?
        ORDER BY watched_at DESC
        """,
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "movie_id": row["movie_id"],
            "rating": row["rating"],
            "watched_at": row["watched_at"],
        }
        for row in rows
    ]


def get_watched_ids(user_id: int) -> list:
    """Return list of movie IDs watched by the user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT movie_id FROM watched_history WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [row["movie_id"] for row in rows]


def is_watched(user_id: int, movie_id: int) -> bool:
    """Return True if the user has marked this movie as watched."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM watched_history WHERE user_id = ? AND movie_id = ?",
        (user_id, movie_id),
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None


def get_watched_count(user_id: int) -> int:
    """Return the total number of watched movies for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS total FROM watched_history WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row["total"] if row else 0


# ---------------------------------------------------------------------------
# 6. USER PREFERENCES (GENRES & LANGUAGES)
# ---------------------------------------------------------------------------

def get_user_preferences(user_id: int) -> dict:
    """
    Get user's preferred languages and genres.
    """
    import json
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT preferred_languages, preferred_genres FROM user_preferences WHERE user_id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {
            "user_id": user_id,
            "preferred_languages": ["en", "hi", "ta"],
            "preferred_genres": ["Action", "Sci-Fi", "Drama"],
        }

    try:
        langs = json.loads(row["preferred_languages"]) if row["preferred_languages"] else []
    except Exception:
        langs = []
    try:
        genres = json.loads(row["preferred_genres"]) if row["preferred_genres"] else []
    except Exception:
        genres = []

    return {
        "user_id": user_id,
        "preferred_languages": langs,
        "preferred_genres": genres,
    }


def save_user_preferences(user_id: int, languages: list, genres: list) -> dict:
    """
    Update or insert user preferences.
    """
    import json
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    langs_json = json.dumps(list(set(languages or [])))
    genres_json = json.dumps(list(set(genres or [])))

    try:
        cursor.execute(
            """
            INSERT INTO user_preferences (user_id, preferred_languages, preferred_genres, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                preferred_languages = excluded.preferred_languages,
                preferred_genres = excluded.preferred_genres,
                updated_at = excluded.updated_at
            """,
            (user_id, langs_json, genres_json, now),
        )
        conn.commit()
        return {"success": True, "message": "Preferences saved successfully."}
    except Exception as exc:
        return {"success": False, "message": f"Error saving preferences: {exc}"}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    print("[database] Tables created successfully.")
    print(f"[database] Database location: {_get_db_path()}")

    # Test registration
    result = register_user("Test User", "test@example.com", "password123")
    print(f"[database] Register: {result}")

    # Test login
    result = login_user("test@example.com", "password123")
    print(f"[database] Login: {result}")

    # Test wrong password
    result = login_user("test@example.com", "wrongpassword")
    print(f"[database] Wrong password: {result}")
