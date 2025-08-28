from cachetools import TTLCache

cache = TTLCache(maxsize=999999, ttl=30)


class UplinkCollector:

    @classmethod
    def get(self, dev_eui, measurement_id: str, default_value=None):
        return cache.get(f'{dev_eui}:{measurement_id}', default_value)

    @classmethod
    def set(self, dev_eui, measurement_id: str, value):
        cache[f'{dev_eui}:{measurement_id}'] = value
