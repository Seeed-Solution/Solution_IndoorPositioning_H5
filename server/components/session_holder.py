from cachetools import TTLCache

ONE_DAY = 86400


class SessionHolder:

    cache: TTLCache = None

    def __int__(self, ttl_in_day: int = 1):
        self.cache = TTLCache(maxsize=999999, ttl=ONE_DAY * ttl_in_day)

    def get(self, dev_eui, measurement_id: str, default_value=None):
        return self.cache.get(f'{dev_eui}:{measurement_id}', default_value)

    def set(self, dev_eui, measurement_id: str, value):
        self.cache[f'{dev_eui}:{measurement_id}'] = value


session_holder = SessionHolder()
