from __future__ import annotations

from typing import Any, Callable, Iterable, Union

from graia.amnesia.message import MessageChain
from graia.broadcast import BaseDispatcher
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
from ichika.core import Friend, Member, Group
from ichika.graia import CLIENT_INSTANCE
from ichika.graia.event import FriendMessage, GroupMessage, MessageEvent
from ichika.message.elements import At, Text

from arclet.alconna import Arparma
from arclet.alconna.exceptions import SpecialOptionTriggered
from arclet.alconna.tools.construct import FuncMounter
from tarina import is_awaitable

from ..graia.model import CommandResult, TConvert
from ..graia.adapter import AlconnaGraiaAdapter
from ..graia.dispatcher import AlconnaDispatcher
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
        async def waiter(m: MessageChain, sender: Friend | Member):
            if isinstance(sender, source.sender.__class__) and source.sender.uin == sender.uid:
                return m

        return waiter  # type: ignore

    async def lookup_source(self, interface: DispatcherInterface[MessageEvent]) -> MessageChain:
        return await interface.lookup_param("__message_chain__", MessageChain, MessageChain([Text("Unknown")]))

    def source_id(self, source: MessageEvent | None = None) -> str:
        return str(source.source.id) if source else "_"

    async def send(
        self,
        converter: TConvert,
        result: Arparma[MessageChain],
        output_text: str | None = None,
        source: MessageEvent | None = None,
    ) -> None:
        client: Client = CLIENT_INSTANCE.get()
        help_message: MessageChain = await run_always_await(
            converter,
            str(result.error_info) if isinstance(result.error_info, SpecialOptionTriggered) else "help",
            output_text,
        )
        if isinstance(source, GroupMessage):
            source: GroupMessage
            await client.send_group_message(source.group.uin, help_message)
        else:
            await client.send_friend_message(source.sender.uin, help_message)  # type: ignore

    def fetch_name(self, path: str) -> Depend:
        async def __wrapper__(result: CommandResult):
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

    def handle_listen(
        self,
        func: Callable,
        buffer: dict[str, Any],
        dispatcher: BaseDispatcher | None,
        guild: bool,
        private: bool,
        **kwargs
    ) -> None:
        events = []
        if guild:
            events.append(GroupMessage)
        if private:
            events.append(FriendMessage)
        buffer.setdefault("dispatchers", [])
        if dispatcher:
            buffer["dispatchers"].append(dispatcher)
        listen(*events)(func)


    def handle_command(self, alc: FuncMounter[Any, MessageChain]) -> Callable:
        async def wrapper(client: Client, sender: Union[Group, Friend], message: MessageChain):
            try:
                arp = alc.parse(message)
            except Exception as e:
                if isinstance(sender, Group):
                    await client.send_group_message(sender, str(e))
                else:
                    await client.send_friend_message(sender, str(e))
                return
            res = list(alc.exec_result.values())[0]
            if arp.matched:
                if is_awaitable(res):
                    res = await res
                if isinstance(res, (str, MessageChain)):
                    if isinstance(sender, Group):
                        await client.send_group_message(sender, res)
                    else:
                        await client.send_friend_message(sender, res)
        return wrapper