from typing import Any, Dict, List, Optional, Tuple, Type

from tortoise.models import Model


class BaseRepository:
    def __init__(self, model_class: Type[Model]):
        self._model = model_class

    async def get_or_create(self, defaults: Optional[Dict[str, Any]] = None, **lookup) -> Tuple[Any, bool]:
        return await self._model.get_or_create(defaults=defaults or {}, **lookup)

    async def exists(self, **lookup) -> bool:
        return await self._model.filter(**lookup).exists()

    async def save(self, instance: Any) -> None:
        await instance.save()

    async def bulk_save(self, instances: List[Any]) -> None:
        await self._model.bulk_create(instances)

    async def get_or_none(self, **lookup) -> Optional[Any]:
        return await self._model.get_or_none(**lookup)

    @property
    def model(self) -> Type[Model]:
        return self._model
