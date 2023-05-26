from __future__ import annotations

from abc import ABCMeta, abstractmethod
from contextlib import suppress
from contextvars import ContextVar
from typing import Any, ClassVar, Generic, Callable
from weakref import finalize

from graia.amnesia.message import MessageChain
from graia.broadcast.builtin.decorators import Depend
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.interrupt.waiter import Waiter

from arclet.alconna import Arparma

from .model import CommandResult, TConvert, TSource


__all__ = ["adapter_context", "AlconnaGraiaAdapter"]


adapter_context: ContextVar["AlconnaGraiaAdapter"] = ContextVar("alconna_graia_adapter")


class AlconnaGraiaAdapter(Generic[TSource], metaclass=ABCMeta):
    __adapter_class__: ClassVar[type[AlconnaGraiaAdapter]] = None  # type: ignore

    def __init__(self):
        token = adapter_context.set(self)

        def clr(tkn):
            with suppress(Exception):
                adapter_context.reset(tkn)

        finalize(self, clr, token)

    @classmethod
    def __init_subclass__(cls, **kwargs):
        AlconnaGraiaAdapter.__adapter_class__ = cls
        super().__init_subclass__()

    @classmethod
    def instance(cls):
        return adapter_context.get()

    @abstractmethod
    def completion_waiter(self, source: TSource, priority: int = 15) -> Waiter:
        ...

    @abstractmethod
    async def lookup_source(self, interface: DispatcherInterface[TSource]) -> MessageChain:
        ...

    @abstractmethod
    async def send(
        self,
        converter: TConvert,
        result: Arparma[MessageChain],
        output_text: str | None = None,
        source: TSource | None = None,
    ) -> None:
        ...

    @abstractmethod
    def source_id(self, source: TSource | None = None) -> str:
        ...

    @abstractmethod
    def fetch_name(self, path: str) -> Depend:
        ...

    @abstractmethod
    def check_account(self, path: str) -> Depend:
        ...

    @abstractmethod
    def handle_listen(
        self,
        func: Callable,
        buffer: dict[str, Any],
        dispatcher: BaseDispatcher,
        guild: bool,
        private: bool,
        private_name: str,
        guild_name: str,
    ) -> None:
        ...


class DefaultAdapter(AlconnaGraiaAdapter[TSource]):
    def completion_waiter(self, source: TSource, priority: int = 15) -> Waiter:
        @Waiter.create_using_function(
            [source.__class__],
            block_propagation=True,
            priority=priority,
        )
        async def waiter(m: MessageChain):
            return m

        return waiter  # type: ignore

    async def lookup_source(self, interface: DispatcherInterface[TSource]) -> MessageChain:
        return await interface.lookup_param("__message_chain__", MessageChain, None)

    def handle_listen(
        self,
        func: Callable,
        buffer: dict[str, Any],
        dispatcher: BaseDispatcher,
        guild: bool = True,
        private: bool = True,
        private_name: str = "private",
        guild_name: str = "guild",
    ) -> None:
        _dispatchers = buffer.setdefault("dispatchers", [])
        _dispatchers.append(dispatcher)

    def fetch_name(self, path: str) -> Depend:
        async def wrapper(result: CommandResult):
            return result.result.all_matched_args.get(path)

        return Depend(wrapper)

    def check_account(self, path: str) -> Depend:
        return Depend(lambda: True)

    async def send(
        self,
        converter: TConvert,
        result: Arparma[MessageChain],
        output_text: str | None = None,
        source: TSource | None = None,
    ) -> None:
        print(output_text)
        return

    def source_id(self, source: TSource | None = None) -> str:
        return f"{id(source)}"


DefaultAdapter()
