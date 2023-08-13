from __future__ import annotations

import importlib
from contextlib import suppress
from pathlib import Path
from typing import Generic, Literal, TypeVar
from tarina import lang
from launart import Launart, Service
from arclet.alconna import command_manager

from .adapter import AlconnaGraiaAdapter

TAdapter = TypeVar("TAdapter", bound=AlconnaGraiaAdapter)
lang.load(Path(__file__).parent / "i18n")



class AlconnaGraiaService(Service, Generic[TAdapter]):
    adapter: TAdapter
    id = "alconna.graia.service"

    def __init__(
        self,
        adapter_type: type[TAdapter] | str | None = None,
        enable_cache: bool = False,
        cache_dir: str | None = None
    ):
        """
        Args:
            adapter_type (TAdapter | str | None): 选择的 Adapter 类型, 不传入时使用默认类型; 传入 str 时会尝试导入对应包
            enable_cache (bool): 是否保存命令动态添加的 shortcuts
            cache_dir (str | None): 保存的路径
        """
        if isinstance(adapter_type, type):
            self.adapter = adapter_type()
        else:
            if isinstance(adapter_type, str):
                with suppress(Exception):
                    importlib.import_module(f"arclet.alconna.{adapter_type}")
            self.adapter = AlconnaGraiaAdapter.__adapter_class__()
        self.enable_cache = enable_cache
        root = Path(cache_dir) if cache_dir else Path(__file__).parent.parent
        _path = root / "manager_cache.db"
        _path.parent.mkdir(exist_ok=True, parents=True)
        command_manager.cache_path = str(_path.absolute())
        super().__init__()

    def get_adapter(self) -> TAdapter:
        return self.adapter

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
