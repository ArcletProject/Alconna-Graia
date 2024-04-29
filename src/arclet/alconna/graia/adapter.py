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

from arclet.alconna.tools.construct import FuncMounter

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

    @abstractmethod
    def is_tome(self, message: MessageChain, account: Any) -> bool:
        ...

    @classmethod
    def instance(cls):
        return adapter_context.get()

    @abstractmethod
    def completion_waiter(self, source: TSource, handler: Callable[[MessageChain], Any], priority: int = 15) -> Waiter:
        ...

    @abstractmethod
    async def lookup_source(
        self,
        interface: DispatcherInterface[TSource],
        need_tome: bool = True,
        remove_tome: bool = True
    ) -> MessageChain:
        ...

    @abstractmethod
    async def send(
        self,
        converter: TConvert,
        output_type: str,
        output_text: str | None,
        source: TSource | None,
    ) -> None:
        ...

    @abstractmethod
    def source_id(self, source: TSource | None = None) -> str:
        ...

    @abstractmethod
    def fetch_name(self, path: str) -> Depend:
        ...

    @abstractmethod
    def handle_listen(
        self,
        func: Callable,
        buffer: dict[str, Any],
        dispatcher: BaseDispatcher | None,
        guild: bool,
        private: bool,
        patterns: list[str] | None = None,
    ) -> None:
        ...

    @abstractmethod
    def handle_command(self, alc: FuncMounter[Any, Any]) -> Callable:
        ...


class DefaultAdapter(AlconnaGraiaAdapter[TSource]):

    def is_tome(self, message: MessageChain, account: Any) -> bool:
        return False

    def completion_waiter(self, source: TSource, handler, priority: int = 15) -> Waiter:
        @Waiter.create_using_function(
            [source.__class__],
            block_propagation=True,
            priority=priority,
        )
        async def waiter(m: MessageChain):
            return await handler(m)

        return waiter  # type: ignore

    async def lookup_source(
        self,
        interface: DispatcherInterface[TSource],
        need_tome: bool = True,
        remove_tome: bool = True
    ) -> MessageChain:
        return await interface.lookup_param("__message_chain__", MessageChain, None)

    def handle_listen(
        self,
        func: Callable,
        buffer: dict[str, Any],
        dispatcher: BaseDispatcher | None,
        *args,
        **kwargs,
    ) -> None:
        _dispatchers = buffer.setdefault("dispatchers", [])
        if dispatcher:
            _dispatchers.append(dispatcher)

    def fetch_name(self, path: str) -> Depend:
        async def wrapper(result: CommandResult):
            return result.result.all_matched_args.get(path)

        return Depend(wrapper)

    async def send(
        self,
        converter: TConvert,
        output_type: str,
        output_text: str | None,
        source: TSource | None,
    ) -> None:
        print(output_text)
        return

    def source_id(self, source: TSource | None = None) -> str:
        return f"{id(source)}"

    def handle_command(self, alc: FuncMounter[Any, Any]) -> Callable:
        async def wrapper(interface: DispatcherInterface):
            msg = await self.lookup_source(interface)
            try:
                arp = alc.parse(msg)
            except Exception as e:
                print(e)
                return
            if arp.matched:
                print(list(alc.exec_result)[0])
        return wrapper


DefaultAdapter()
