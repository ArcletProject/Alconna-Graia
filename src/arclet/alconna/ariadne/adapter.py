from __future__ import annotations

from typing import Any, Callable, Union

from arclet.alconna.exceptions import SpecialOptionTriggered
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import FriendMessage, GroupMessage, MessageEvent
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Plain, Source, File, Quote
from graia.ariadne.model import Friend, Member, Client, Stranger
from graia.ariadne.util.interrupt import FunctionWaiter
from graia.broadcast import BaseDispatcher
from graia.broadcast.builtin.decorators import Depend
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.interrupt import Waiter
from graia.broadcast.utilles import run_always_await

from arclet.alconna import Arparma, argv_config, set_default_argv_type

from ..graia.model import CommandResult, TConvert
from ..graia.adapter import AlconnaGraiaAdapter
from ..graia.argv import BaseMessageChainArgv
from ..graia.dispatcher import AlconnaDispatcher
from ..graia.utils import listen

AlconnaDispatcher.default_send_handler = lambda _, x: MessageChain([Plain(x)])
Sender = Union[Friend, Member, Stranger, Client]


class AlconnaAriadneAdapter(AlconnaGraiaAdapter[MessageEvent]):
    def completion_waiter(self, source: MessageEvent, priority: int = 15) -> Waiter:
        async def waiter(m: MessageChain, sender: Sender):
            if sender.id == source.sender.id:
                return m

        return FunctionWaiter(waiter, [source.__class__], block_propagation=True, priority=priority)

    async def lookup_source(self, interface: DispatcherInterface[MessageEvent]) -> MessageChain:
        return await interface.lookup_param("__message_chain__", MessageChain, MessageChain("Unknown"))

    def source_id(self, source: MessageEvent | None = None) -> str:
        return str(source.source.id) if source else "_"

    async def send(
        self,
        converter: TConvert,
        result: Arparma[MessageChain],
        output_text: str | None = None,
        source: MessageEvent | None = None,
    ) -> None:
        app: Ariadne = Ariadne.current()
        help_message: MessageChain = await run_always_await(
            converter,
            str(result.error_info) if isinstance(result.error_info, SpecialOptionTriggered) else "help",
            output_text,
        )
        if isinstance(source, GroupMessage):
            await app.send_group_message(source.sender.group, help_message)
        else:
            await app.send_message(source.sender, help_message)  # type: ignore

    def fetch_name(self, path: str) -> Depend:
        async def __wrapper__(app: Ariadne, result: CommandResult):
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

    def handle_listen(
        self,
        func: Callable,
        buffer: dict[str, Any],
        dispatcher: BaseDispatcher,
        guild: bool,
        private: bool,
        private_name: str,
        guild_name: str
    ) -> None:
        events = []
        if guild:
            events.append(GroupMessage)
        if private:
            events.append(FriendMessage)
        buffer.setdefault("dispatchers", []).append(dispatcher)
        listen(*events)(func)


class AriadneMessageChainArgv(BaseMessageChainArgv):
    ...


set_default_argv_type(AriadneMessageChainArgv)
argv_config(
    target=AriadneMessageChainArgv,
    filter_out=[Source, File, Quote],
    checker=lambda x: isinstance(x, MessageChain),
    to_text=lambda x: x.text if x.__class__ is Plain else None,
    converter=lambda x: MessageChain(x),
)
