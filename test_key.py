import os, sys
sys.path.insert(0, '.')

env_path = '.env'
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and not os.environ.get(k):
                os.environ[k] = v

from src.movie_metadata import get_api_key
key = get_api_key()
print('Key loaded:', bool(key), '| First 8 chars:', (key or '')[:8])
