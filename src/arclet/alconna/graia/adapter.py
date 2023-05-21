from __future__ import annotations

from abc import ABCMeta, abstractmethod
from contextlib import suppress
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Generic
from weakref import finalize

from graia.amnesia.message import MessageChain
from graia.broadcast.builtin.decorators import Depend
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.interrupt.waiter import Waiter

from arclet.alconna import Alconna, Arparma

from .model import AlconnaProperty, TSource
from .utils import listen

if TYPE_CHECKING:
    from .dispatcher import AlconnaDispatcher
    from .saya import AlconnaSchema


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
    async def property(
        self,
        dispatcher: AlconnaDispatcher,
        result: Arparma[MessageChain],
        output_text: str | None = None,
        source: TSource | None = None,
    ) -> AlconnaProperty[TSource]:
        ...

    @abstractmethod
    async def send(
        self,
        dispatcher: AlconnaDispatcher,
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
    def alcommand(
        self,
        dispatcher: AlconnaDispatcher,
        guild: bool,
        private: bool,
        private_name: str,
        guild_name: str,
    ) -> Callable[[Callable, dict[str, Any]], AlconnaSchema]:
        ...

    class Dispatcher(BaseDispatcher):
        def __init__(self, command: Alconna, text: str, source: TSource):
            self.command = command
            self.output = text
            self.source_event = source

        async def catch(self, interface: DispatcherInterface[TSource]):
            if interface.name == "output" and interface.annotation == str:
                return self.output
            if isinstance(interface.annotation, Alconna):
                return self.command
            if issubclass(interface.annotation, type(self.source_event)) or isinstance(
                self.source_event, interface.annotation
            ):
                return self.source_event


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
        return getattr(interface.event, "message_chain", interface.event.message.content)

    def alcommand(
        self,
        dispatcher: AlconnaDispatcher,
        guild: bool = True,
        private: bool = True,
        private_name: str = "private",
        guild_name: str = "guild",
    ) -> Callable[[Callable, dict[str, Any]], AlconnaSchema]:
        from .saya import AlconnaSchema

        def wrapper(func: Callable, buffer: dict[str, Any]):
            _dispatchers = buffer.setdefault("dispatchers", [])
            _dispatchers.append(dispatcher)
            listen()(func)  # noqa
            return AlconnaSchema(dispatcher.command)

        return wrapper

    def fetch_name(self, path: str) -> Depend:
        async def wrapper(result: AlconnaProperty):
            return result.result.all_matched_args.get(path)

        return Depend(wrapper)

    def check_account(self, path: str) -> Depend:
        return Depend(lambda: True)

    async def property(
        self,
        dispatcher: AlconnaDispatcher,
        result: Arparma[MessageChain],
        output_text: str | None = None,
        source: TSource | None = None,
    ):
        return AlconnaProperty(result, None, source)

    async def send(
        self,
        dispatcher: AlconnaDispatcher,
        result: Arparma[MessageChain],
        output_text: str | None = None,
        source: TSource | None = None,
    ) -> None:
        return

    def source_id(self, source: TSource | None = None) -> str:
        return f"{id(source)}"


DefaultAdapter()
