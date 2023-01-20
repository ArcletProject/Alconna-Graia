from __future__ import annotations

from pathlib import Path
from typing import Literal, Set, Type

from launart import ExportInterface, Launart, Service

from arclet.alconna import command_manager


class AlconnaManagerInterface(ExportInterface["AlconnaManagerService"]):

    def __init__(self, service: AlconnaManagerService):
        self.service = service

    def save(self):
        self.manager.dump_cache()

    manager = command_manager


class AlconnaManagerService(Service):
    def __init__(self, enable_cache: bool = False, cache_path: str | None = None):
        self.enable_cache = enable_cache
        _path = Path(cache_path) / "manager_cache.db"
        _path.parent.mkdir(exist_ok=True, parents=True)
        command_manager.cache_path = str(_path.absolute())

    def get_interface(self, interface_type: Type[AlconnaManagerInterface]) -> AlconnaManagerInterface:
        return AlconnaManagerInterface(self)

    @property
    def required(self):
        return {}

    @property
    def stages(self) -> Set[Literal["preparing", "blocking", "cleanup"]]:
        return {"preparing", "cleanup"}

    async def launch(self, manager: Launart):
        async with self.stage("preparing"):
            if self.enable_cache:
                command_manager.load_cache()

        async with self.stage("cleanup"):
            if self.enable_cache:
                command_manager.dump_cache()
