from __future__ import annotations

import importlib
from contextvars import ContextVar
from contextlib import suppress
from pathlib import Path
from typing import Generic, Literal, TypeVar
from launart import Launart, Service
from arclet.alconna import command_manager

from .i18n import lang as lang  # type: ignore
from .adapter import AlconnaGraiaAdapter

TAdapter = TypeVar("TAdapter", bound=AlconnaGraiaAdapter)


CtxService: ContextVar[AlconnaGraiaService] = ContextVar("alconna_graia_service")


class AlconnaGraiaService(Service, Generic[TAdapter]):
    adapter: TAdapter
    id = "alconna.graia.service"

    def __init__(
        self,
        adapter_type: type[TAdapter] | str | None = None,
        enable_cache: bool = False,
        cache_dir: str | None = None,
        global_need_tome: bool = False,
        global_remove_tome: bool = False,
    ):
        """
        Args:
            adapter_type (TAdapter | str | None): 选择的 Adapter 类型, 不传入时使用默认类型; 传入 str 时会尝试导入对应包
            enable_cache (bool): 是否保存命令动态添加的 shortcuts
            cache_dir (str | None): 保存的路径
            global_need_tome (bool): 是否全局需要 tome
            global_remove_tome (bool): 是否全局移除 tome
        """
        if isinstance(adapter_type, type):
            self.adapter = adapter_type()
        else:
            if isinstance(adapter_type, str):
                with suppress(Exception):
                    importlib.import_module(f"arclet.alconna.{adapter_type}")
            self.adapter = AlconnaGraiaAdapter.__adapter_class__()  # type: ignore
        self.enable_cache = enable_cache
        self.global_need_tome = global_need_tome
        self.global_remove_tome = global_remove_tome
        root = Path(cache_dir) if cache_dir else Path(__file__).parent.parent
        _path = root / "manager_cache.db"
        _path.parent.mkdir(exist_ok=True, parents=True)
        command_manager.cache_path = str(_path.absolute())
        super().__init__()
        CtxService.set(self)

    @classmethod
    def current(cls) -> AlconnaGraiaService:
        return CtxService.get()

    def get_adapter(self) -> TAdapter:
        return self.adapter

    @property
    def required(self):
        return set()

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

    supported_interface_types = set()

    def get_interface(self, *args, **kwargs):
        return None
