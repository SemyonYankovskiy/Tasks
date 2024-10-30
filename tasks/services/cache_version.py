from django.core.cache import cache


class CacheVersion:
    def __init__(self, cache_key):
        self.cache_key = cache_key

    def get_cache_version(self):
        # Получаем версию из кеша; если её нет, устанавливаем в 1
        version = cache.get(self.cache_key)
        if version is None:
            version = 1
            cache.set(self.cache_key, version)
        return version

    def increment_cache_version(self):
        # Увеличиваем версию кеша и обновляем её в кеше
        version = self.get_cache_version() + 1
        cache.set(self.cache_key, version)
        return version
