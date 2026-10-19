import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')

with open('.env') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        k = k.strip()
        v = v.strip()
        if v.startswith('"') and v.endswith('"'):
            v = v[1:-1]
        elif v.startswith("'") and v.endswith("'"):
            v = v[1:-1]
        if k and not os.environ.get(k):
            os.environ[k] = v

from src.recommender import MovieRecommender
from src.movie_metadata import get_movie_metadata, get_api_key

engine = MovieRecommender()
key = get_api_key()
print('TMDB Key configured:', bool(key))
print()

passed = 0
failed = 0
for title in ['Vikram', 'Leo', 'Jailer', 'Inception', 'The Dark Knight']:
    matches = engine.df[engine.df['title'].str.lower() == title.lower()]
    if matches.empty:
        print('FAIL', title, '- not in dataset')
        failed += 1
        continue
    row = matches.iloc[0]
    meta = get_movie_metadata(int(row['id']), local_data=row, api_key=key)
    url = meta.get('poster_url') or ''
    ok = url.startswith('http') and 'None' not in url
    tag = 'PASS' if ok else 'FAIL'
    if ok:
        passed += 1
    else:
        failed += 1
    print(tag, title, '->', url[:80] if url else 'None')

print()
print(f'Results: {passed} passed, {failed} failed')
