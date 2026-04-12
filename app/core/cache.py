from cachetools import TTLCache

# Cache for WSAA token and sign. AFIP tokens are valid for 12 hours.
# We set TTL to 11.5 hours (41400 seconds) to be safe and refresh slightly before expiration.
wsaa_cache = TTLCache(maxsize=1, ttl=41400)

def set_wsaa_credentials(token: str, sign: str):
    wsaa_cache['credentials'] = {'token': token, 'sign': sign}

def get_wsaa_credentials() -> dict | None:
    return wsaa_cache.get('credentials')
