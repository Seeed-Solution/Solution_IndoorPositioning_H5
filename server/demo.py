from cachetools import TTLCache

cache = TTLCache(maxsize=999999, ttl=30)

cache["aaa"] = '111'

print(cache.get("aaa"))