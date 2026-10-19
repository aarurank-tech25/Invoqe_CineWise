# 🎬 AI-Powered Movie Recommendation System

An intelligent, content-based movie recommendation system built using Python, Scikit-learn (TF-IDF Vectorization & Cosine Similarity), Streamlit, and SQLite on the TMDB Top 10,000 Movies dataset with rich metadata integration (posters, cast, taglines) and offline fallback mode.

---

## 🌟 Key Features

- **Content-Based Filtering**: Recommends movies using combined features: `title`, `genre`, `overview`, and `original_language`.
- **TF-IDF & Cosine Similarity Engine**: Computes high-dimensional feature vectors with sublinear TF scaling, English stopword filtering, and sparse linear kernel calculations on-the-fly for high performance and low memory footprint.
- **Rich Metadata Integration Layer (`src/movie_metadata.py`)**:
  - Fetches real-time HD posters, main cast actors, directors, taglines, and ratings via TMDB API.
  - In-memory thread-safe caching to minimize network latency and prevent duplicate requests.
  - **Graceful Fallback Mode**: If no API key is provided or the network is unavailable, the application seamlessly falls back to the local Kaggle dataset metadata without inventing placeholder data or breaking image links.
- **Modern Cinema Web UI (Streamlit)**:
  - **Hero Spotlight Card**: Prominent display for the selected movie with large poster, genre pills, cast list, vote rating, and one-click favorite button.
  - **Recommendation Cards**: Ranked cards showing match percentage (`✨ 92.4% Match`), release year, rating, top cast, concise synopsis, and favorite toggles.
  - **Dynamic Search & Autocomplete**: Search by movie title with release year disambiguation.
  - **Filters**: Filter recommendations by language (e.g., English, Japanese, French) and genre (e.g., Action, Animation, Sci-Fi).
- **User Authentication & Personalization (SQLite)**:
  - User registration & login with secure SHA-256 + unique per-user random salt hashing.
  - Isolated favorites collection for each user.
  - Profile page with user statistics and registration details.

---

## 🏗️ Project Architecture

```
AI-Movie-Recommendation/
├── .streamlit/
│   └── secrets.toml.example        # Template for TMDB API key configuration
├── data/
│   ├── top10K-TMDB-movies.csv      # TMDB dataset (10,000 movies)
│   └── movie_app.db                # SQLite database (auto-generated)
├── src/
│   ├── __init__.py
│   ├── preprocessing.py            # Data loading, cleaning, metadata tag creation & TF-IDF
│   ├── recommender.py              # Recommendation engine using linear kernel cosine similarity
│   ├── movie_metadata.py           # TMDB API metadata layer, caching & fallback handler
│   └── database.py                 # SQLite database helper (auth & favorites)
├── app.py                          # Full-featured Streamlit UI application
├── requirements.txt                # Python package dependencies
└── README.md                       # Documentation
```

---

## 🔑 TMDB API Key Setup (Optional for Live Posters & Cast)

The application works completely out-of-the-box in **Fallback Mode** without an API key. To enable live HD posters and top cast details:

1. Create a free account at [themoviedb.org](https://www.themoviedb.org/).
2. Navigate to **Settings -> API** and generate a free API Key.
3. Configure the key using any of these methods:
   - **Method A (Streamlit Secrets - Recommended)**: Create `.streamlit/secrets.toml` and add:
     ```toml
     TMDB_API_KEY = "your_tmdb_api_key_here"
     ```
   - **Method B (Environment Variable)**:
     ```bash
     export TMDB_API_KEY="your_tmdb_api_key_here"  # Linux / macOS
     set TMDB_API_KEY="your_tmdb_api_key_here"     # Windows CMD
     $env:TMDB_API_KEY="your_tmdb_api_key_here"    # Windows PowerShell
     ```
   - **Method C (In-App Sidebar)**: Open the sidebar expander **⚙️ TMDB API Settings** and paste your API key.

---

## 🚀 Getting Started

### 1. Prerequisites & Installation

Ensure you have Python 3.8+ installed. Install dependencies:

```bash
pip install -r requirements.txt
```

### 2. Run the Application

Launch the Streamlit web app:

```bash
streamlit run app.py
```

The app will open automatically in your browser at `http://localhost:8501`.

---

## 🧠 How the Recommendation Algorithm Works

1. **Feature Engineering**: A combined `tags` feature is created by merging:
   - Cleaned movie title
   - Genre list (missing values imputed as `'unknown'`)
   - Overview text (missing values imputed as `''`)
   - Original language code
2. **TF-IDF Vectorization**: `TfidfVectorizer` transforms text tags into a sparse matrix ($10,000 \times 10,000$ features) with sublinear TF scaling and English stopword removal.
3. **Similarity Calculation**: When a user selects a movie, `linear_kernel` computes the cosine similarity between the selected movie's TF-IDF vector and all other movies in the dataset on-the-fly.
4. **Ranking & Filtering**: Movies are sorted by similarity score (excluding the query movie itself), filtered optionally by language and genre, and returned as the top-$N$ most relevant titles.

---

## 🗄️ Database Schema

SQLite is used for local data persistence (`data/movie_app.db`):
- **`users`**: `id`, `name`, `email` (unique), `password_hash`, `salt`, `created_at`
- **`favorites`**: `id`, `user_id` (foreign key), `movie_id` (TMDB ID), `created_at`
- **`password_resets`**: `id`, `user_id` (foreign key), `token_hash` (SHA-256), `expires_at`, `used`, `created_at`

---

## ✉️ Email & Password Recovery Configuration

CineWise features an end-to-end, cryptographically secure password recovery flow:
- Single-use, time-limited reset tokens (stored only as SHA-256 hashes).
- Generic privacy responses to prevent user email enumeration.
- Rate-limiting (max 3 requests per 15 minutes).

### Environment Variables (.env)
```env
# TMDB API Key
TMDB_API_KEY=your_tmdb_api_key_here

# SMTP Configuration (Optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
SMTP_FROM=CineWise <noreply@cinewise.app>

# Frontend App URL
APP_URL=http://localhost:5173
```
*Note: If SMTP credentials are not configured, CineWise operates in **Development Testing Mode**, generating secure tokens and presenting the test reset link directly in testing endpoints for verification without requiring a live mail server.*

---

## 📦 Tech Stack

- **Core**: Python 3.8+
- **Data Processing**: Pandas, NumPy
- **Machine Learning**: Scikit-Learn (TF-IDF Vectorizer, Cosine Similarity)
- **Web App**: Streamlit
- **HTTP Client**: Requests
- **Database**: SQLite3


