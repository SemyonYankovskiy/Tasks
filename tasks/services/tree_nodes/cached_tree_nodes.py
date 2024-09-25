from .base import CachedTree
from .tree_nodes import ObjectsTree


class CachedObjectsTree(CachedTree, ObjectsTree):

    @property
    def unique_cache_part(self) -> str:
        return f"user:{self._context.get('user', 'none')}"


def objects_signal_callback(**kwargs):
    print("objects_signal_callback", kwargs)

    CachedObjectsTree(context=kwargs).increment_global_version()
