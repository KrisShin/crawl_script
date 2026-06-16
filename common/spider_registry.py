from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class SpiderEntry:
    name: str
    handler: Callable
    help: str = ""


_registry: Dict[str, SpiderEntry] = {}


def register_spider(name: str, help: str = ""):
    def decorator(func: Callable) -> Callable:
        _registry[name] = SpiderEntry(name=name, handler=func, help=help)
        return func
    return decorator


def get_spider(name: str) -> Optional[SpiderEntry]:
    return _registry.get(name)


def get_spider_names() -> List[str]:
    return sorted(_registry.keys())


def list_spiders() -> Dict[str, SpiderEntry]:
    return dict(_registry)
