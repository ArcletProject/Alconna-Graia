from __future__ import annotations

from pathlib import Path
from typing import Literal, TypeVar, Generic

from launart import ExportInterface, Launart, Service

from arclet.alconna import command_manager
from .adapter import AlconnaGraiaAdapter


TAdapter = TypeVar("TAdapter", bound=AlconnaGraiaAdapter)


class AlconnaGraiaInterface(ExportInterface["AlconnaGraiaService"], Generic[TAdapter]):

    def __init__(self, service: AlconnaGraiaService):
        self.service = service

    @property
    def adapter(self) -> TAdapter:
        return self.service.adapter

    def save(self):
        self.manager.dump_cache()

    manager = command_manager


class AlconnaGraiaService(Service, Generic[TAdapter]):
    adapter: TAdapter
    id = "alconna.graia.service"
    supported_interface_types = {AlconnaGraiaInterface}

    def __init__(
        self,
        adapter_type: type[TAdapter] | None = None,
        enable_cache: bool = False,
        cache_path: str | None = None
    ):
        self.adapter = (adapter_type or AlconnaGraiaAdapter.__adapter_class__)()
        self.enable_cache = enable_cache
        _path = Path(cache_path) / "manager_cache.db"
        _path.parent.mkdir(exist_ok=True, parents=True)
        command_manager.cache_path = str(_path.absolute())

    def get_interface(self, interface_type: type[AlconnaGraiaInterface]) -> AlconnaGraiaInterface[TAdapter]:
        return AlconnaGraiaInterface(self)

    @property
    def required(self):
        return {}

    @property
    def stages(self) -> set[Literal["preparing", "blocking", "cleanup"]]:
        return {"preparing", "cleanup"}

    async def launch(self, manager: Launart):
        async with self.stage("preparing"):
            if self.enable_cache:
                command_manager.load_cache()
        async with self.stage("cleanup"):
            if self.enable_cache:
                command_manager.dump_cache()
