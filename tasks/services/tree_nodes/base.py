from abc import ABC, abstractmethod
from typing import TypedDict, NotRequired

from django.core.cache import cache


class Node(TypedDict):
    id: int | str
    label: str
    children: NotRequired[list["Node"]]


class Tree(ABC):

    def __init__(self, context) -> None:
        self._context = context

    @abstractmethod
    def get_nodes(self) -> list[Node]:
        pass


class CachedTree(Tree, ABC):

    def __init__(self, context: dict, timeout: int = 60) -> None:
        super().__init__(context)
        self._timeout = timeout

    @property
    @abstractmethod
    def unique_cache_part(self) -> str:
        pass

    @property
    def base_cache_key(self) -> str:
        return self.__class__.__name__

    @property
    def cache_key(self) -> str:
        return self.base_cache_key + ":" + self.unique_cache_part

    def get_cache(self) -> list[Node] | None:
        print("Getting nodes from cache", self.cache_key)
        return cache.get(self.cache_key, default=None, version=self.get_global_version())

    def set_cache(self, nodes: list[Node], timeout: int | None = None) -> None:
        print("Setting nodes to cache", self.cache_key)
        cache.set(self.cache_key, nodes, timeout=timeout, version=self.get_global_version())

    def clear_cache(self) -> None:
        cache.delete(self.cache_key)

    def get_cached_nodes(self) -> list[Node]:
        data = self.get_cache()

        if data is None:
            data = self.get_nodes()
            self.set_cache(data, timeout=self._timeout)  # 10min

        print("Getting cached nodes", data)
        return data

    def get_global_version(self) -> int:
        print("Getting global version")
        return cache.get(self.base_cache_key + ":version", 1)

    def increment_global_version(self) -> None:
        print("Incrementing global version")
        try:
            cache.incr(self.base_cache_key + ":version")
        except ValueError:
            cache.set(self.base_cache_key + ":version", 2)
