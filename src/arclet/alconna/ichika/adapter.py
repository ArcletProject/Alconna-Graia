from __future__ import annotations

from contextlib import suppress
from typing import Any, Callable, Iterable

from graia.amnesia.message import MessageChain
from graia.broadcast.builtin.decorators import Depend
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.interrupt import Waiter
from graia.broadcast.utilles import (
    T_Dispatcher,
    dispatcher_mixin_handler,
    run_always_await,
)
from ichika.client import Client
from ichika.core import Friend
from ichika.graia import CLIENT_INSTANCE, IchikaClientDispatcher
from ichika.graia.event import FriendMessage, GroupMessage, MessageEvent
from ichika.message.elements import At, Text

from arclet.alconna import Arparma
from arclet.alconna.exceptions import SpecialOptionTriggered

from ..graia import AlconnaProperty, AlconnaSchema
from ..graia.adapter import AlconnaGraiaAdapter
from ..graia.dispatcher import AlconnaDispatcher, AlconnaOutputMessage
from ..graia.utils import listen

AlconnaDispatcher.default_send_handler = lambda _, x: MessageChain([Text(x)])


def resolve_dispatchers_mixin(dispatchers: Iterable[T_Dispatcher]) -> list[T_Dispatcher]:
    """解析 dispatcher list 的 mixin

    Args:
        dispatchers (Iterable[T_Dispatcher]): dispatcher 列表

    Returns:
        List[T_Dispatcher]: 解析后的 dispatcher 列表
    """
    result = []
    for dispatcher in dispatchers:
        result.extend(dispatcher_mixin_handler(dispatcher))
    return result


class AlconnaIchikaAdapter(AlconnaGraiaAdapter[MessageEvent]):
    def completion_waiter(self, source: MessageEvent, priority: int = 15) -> Waiter:
        @Waiter.create_using_function(
            [source.__class__],
            block_propagation=True,
            priority=priority,
        )
        async def waiter(m: MessageChain):
            return m

        return waiter  # type: ignore

    async def lookup_source(self, interface: DispatcherInterface[MessageEvent]) -> MessageChain:
        return await interface.lookup_param("__message_chain__", MessageChain, MessageChain([Text("Unknown")]))

    def source_id(self, source: MessageEvent | None = None) -> str:
        return str(source.source.id) if source else "_"

    async def property(
        self,
        dispatcher: AlconnaDispatcher,
        result: Arparma[MessageChain],
        output_text: str | None = None,
        source: MessageEvent | None = None,
    ) -> AlconnaProperty[MessageEvent]:
        if not isinstance(source, MessageEvent) or (result.matched or not output_text):
            return AlconnaProperty(result, None, source)
        if dispatcher.send_flag == "stay":
            return AlconnaProperty(result, output_text, source)
        if dispatcher.send_flag == "reply":
            await self.send(dispatcher, result, output_text, source)
        elif dispatcher.send_flag == "post":
            with suppress(LookupError):
                interface = DispatcherInterface.ctx.get()
                dispatchers = resolve_dispatchers_mixin([source.Dispatcher, IchikaClientDispatcher]) + [
                    self.Dispatcher(dispatcher.command, output_text, source)
                ]
                for listener in interface.broadcast.default_listener_generator(AlconnaOutputMessage):
                    await interface.broadcast.Executor(listener, dispatchers)
                    listener.oplog.clear()
        return AlconnaProperty(result, None, source)

    async def send(
        self,
        dispatcher: AlconnaDispatcher,
        result: Arparma[MessageChain],
        output_text: str | None = None,
        source: MessageEvent | None = None,
    ) -> None:
        client: Client = CLIENT_INSTANCE.get()
        help_message: MessageChain = await run_always_await(
            dispatcher.converter,
            str(result.error_info) if isinstance(result.error_info, SpecialOptionTriggered) else "help",
            output_text,
        )
        if isinstance(source, GroupMessage):
            source: GroupMessage
            await client.send_group_message(source.group.uin, help_message)
        else:
            await client.send_friend_message(source.sender.uin, help_message)  # type: ignore

    def fetch_name(self, path: str) -> Depend:
        async def __wrapper__(result: AlconnaProperty):
            event = result.source
            arp = result.result
            if t := arp.all_matched_args.get(path, None):
                return t.display or "Unknown" if isinstance(t, At) else t
            elif isinstance(event.sender, Friend):
                return event.sender.nickname
            else:
                return event.sender.name

        return Depend(__wrapper__)

    def check_account(self, path: str) -> Depend:
        async def __wrapper__(client: Client, arp: Arparma):
            match: At | str | bytes = arp.query(path, b"\0")
            if isinstance(match, bytes):
                return True
            if isinstance(match, str):
                bot_name = (await client.get_account_info()).nickname
                if bot_name == match:
                    return True
            if isinstance(match, At) and match.target == client.uin:
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
