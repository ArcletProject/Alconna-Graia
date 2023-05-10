from __future__ import annotations

from contextlib import suppress
from typing import Any, Callable

from arclet.alconna.exceptions import SpecialOptionTriggered
from graia.ariadne.app import Ariadne
from graia.ariadne.dispatcher import ContextDispatcher
from graia.ariadne.event.message import FriendMessage, GroupMessage, MessageEvent
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Plain
from graia.ariadne.model import Friend
from graia.ariadne.util import resolve_dispatchers_mixin
from graia.ariadne.util.interrupt import AnnotationWaiter
from graia.broadcast.builtin.decorators import Depend
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.interrupt import Waiter
from graia.broadcast.utilles import run_always_await

from arclet.alconna import Arparma, argv_config

from ..graia import AlconnaProperty, AlconnaSchema
from ..graia.adapter import AlconnaGraiaAdapter
from ..graia.argv import MessageChainArgv
from ..graia.dispatcher import AlconnaDispatcher, AlconnaOutputMessage
from ..graia.model import TSource
from ..graia.utils import listen

AlconnaDispatcher.default_send_handler = lambda x: MessageChain([Plain(x)])


class AlconnaAriadneAdapter(AlconnaGraiaAdapter[MessageEvent]):
    def completion_waiter(self, interface: DispatcherInterface[TSource], priority: int = 15) -> Waiter:
        return AnnotationWaiter(MessageChain, [interface.event.__class__], block_propagation=True, priority=priority)

    async def lookup_source(self, interface: DispatcherInterface[MessageEvent]) -> MessageChain:
        return await interface.lookup_param("__message_chain__", MessageChain, MessageChain("Unknown"))

    async def send(
        self,
        dispatcher: AlconnaDispatcher,
        result: Arparma[MessageChain],
        output_text: str | None = None,
        source: MessageEvent | None = None,
        exclude: bool = True,
    ) -> AlconnaProperty[MessageEvent]:
        if not isinstance(source, MessageEvent) or (result.matched or not output_text):
            return AlconnaProperty(result, None, source)
        if exclude:
            id_ = str(source.source.id) if source else '_'
            cache = self.output_cache.setdefault(id_, set())
            if dispatcher.command in cache:
                return AlconnaProperty(result, None, source)
            cache.clear()
            cache.add(dispatcher.command)
        if dispatcher.send_flag == "stay":
            return AlconnaProperty(result, output_text, source)
        if dispatcher.send_flag == "reply":
            app: Ariadne = Ariadne.current()
            help_message: MessageChain = await run_always_await(
                dispatcher.converter,
                str(result.error_info) if isinstance(result.error_info, SpecialOptionTriggered) else "help",
                output_text
            )
            if isinstance(source, GroupMessage):
                await app.send_group_message(source.sender.group, help_message)
            else:
                await app.send_message(source.sender, help_message)  # type: ignore
        elif dispatcher.send_flag == "post":
            with suppress(LookupError):
                interface = DispatcherInterface.ctx.get()
                dispatchers = resolve_dispatchers_mixin([source.Dispatcher, ContextDispatcher]) + [
                    self.Dispatcher(dispatcher.command, output_text, source)
                ]
                for listener in interface.broadcast.default_listener_generator(AlconnaOutputMessage):
                    await interface.broadcast.Executor(listener, dispatchers)
                    listener.oplog.clear()
        return AlconnaProperty(result, None, source)

    def fetch_name(self, path: str) -> Depend:
        async def __wrapper__(app: Ariadne, result: AlconnaProperty):
            event = result.source
            arp = result.result
            if t := arp.all_matched_args.get(path, None):
                return t.representation or (await app.get_user_profile(t.target)).nickname if isinstance(t, At) else t
            elif isinstance(event.sender, Friend):
                return event.sender.nickname
            else:
                return event.sender.name

        return Depend(__wrapper__)

    def check_account(self, path: str) -> Depend:
        async def __wrapper__(app: Ariadne, arp: Arparma):
            match: At | str | bytes = arp.query(path, b"\0")
            if isinstance(match, bytes):
                return True
            if isinstance(match, str):
                bot_name = (await app.get_bot_profile()).nickname
                if bot_name == match:
                    return True
            if isinstance(match, At) and match.target == app.account:
                return True
            raise ExecutionStop

        return Depend(__wrapper__)

    def alcommand(
        self, dispatcher: AlconnaDispatcher, guild: bool, private: bool, private_name: str, guild_name: str
    ) -> Callable[[Callable, dict[str, Any]], AlconnaSchema]:
        def wrapper(func: Callable, buffer: dict[str, Any]):
            events = []
            if guild:
                events.append(GroupMessage)
            if private:
                events.append(FriendMessage)
            buffer.setdefault("dispatchers", []).append(dispatcher)
            listen(*events)(func)  # noqa
            return AlconnaSchema(dispatcher.command)

        return wrapper


argv_config(
    target=MessageChainArgv,
    filter_out=["Source", "File", "Quote"],
    checker=lambda x: isinstance(x, MessageChain),
    to_text=lambda x: x.text if x.__class__ is Plain else None,
    converter=lambda x: MessageChain(x)
)
