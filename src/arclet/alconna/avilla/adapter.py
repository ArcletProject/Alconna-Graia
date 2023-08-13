from __future__ import annotations

from typing import Any, Callable, Union

from avilla.core.context import Context
from avilla.core.elements import Notice
from avilla.core.tools.filter import Filter
from avilla.standard.core.message import MessageEdited, MessageReceived
from avilla.standard.core.profile import Summary
from graia.amnesia.message import MessageChain
from graia.amnesia.message.element import Text
from graia.broadcast import BaseDispatcher
from graia.broadcast.builtin.decorators import Depend
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.interrupt import Waiter
from graia.broadcast.utilles import run_always_await

from arclet.alconna import Arparma
from arclet.alconna.exceptions import SpecialOptionTriggered
from arclet.alconna.tools.construct import FuncMounter
from tarina import is_awaitable

from ..graia.model import CommandResult, TConvert
from ..graia.adapter import AlconnaGraiaAdapter
from ..graia.dispatcher import AlconnaDispatcher
from ..graia.utils import listen

AlconnaDispatcher.default_send_handler = lambda _, x: MessageChain([Text(x)])

AvillaMessageEvent = Union[MessageEdited, MessageReceived]


class AlconnaAvillaAdapter(AlconnaGraiaAdapter[AvillaMessageEvent]):
    def completion_waiter(self, source: AvillaMessageEvent, priority: int = 15) -> Waiter:
        @Waiter.create_using_function(
            [MessageReceived],
            block_propagation=True,
            priority=priority,
        )
        async def waiter(event: MessageReceived):
            if event.context.client == source.context.client:
                return event.message.content

        return waiter  # type: ignore

    async def lookup_source(self, interface: DispatcherInterface[AvillaMessageEvent]) -> MessageChain:
        return interface.event.message.content

    def source_id(self, source: AvillaMessageEvent | None = None) -> str:
        return source.message.id if source else "_"

    async def send(
        self,
        converter: TConvert,
        result: Arparma[MessageChain],
        output_text: str | None = None,
        source: AvillaMessageEvent | None = None,
    ) -> None:
        ctx: Context = source.context
        help_message: MessageChain = await run_always_await(
            converter,
            str(result.error_info) if isinstance(result.error_info, SpecialOptionTriggered) else "help",
            output_text,
        )
        await ctx.scene.send_message(help_message)

    def fetch_name(self, path: str) -> Depend:
        async def __wrapper__(ctx: Context, result: CommandResult[MessageReceived]):
            arp = result.result
            if t := arp.all_matched_args.get(path, None):
                return (
                    t.target.pattern.get("display")
                    or (await ctx.pull(Summary, target=result.source.context.client)).name
                    if isinstance(t, Notice)
                    else t
                )
            else:
                return (await ctx.pull(Summary, target=result.source.context.client)).name

        return Depend(__wrapper__)

    def check_account(self, path: str) -> Depend:
        async def __wrapper__(ctx: Context, arp: Arparma):
            match: Notice | str | bytes = arp.query(path, b"\0")
            if isinstance(match, bytes):
                return True
            if isinstance(match, str):
                bot_name = (await ctx.pull(Summary, target=ctx.self)).name
                if bot_name == match:
                    return True
            if isinstance(match, Notice) and match.target == ctx.self:
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
        patterns: list[str] | None = None,
    ) -> None:
        _filter = Filter().cx.client
        _dispatchers = buffer.setdefault("dispatchers", [])
        if patterns:
            _dispatchers.append(_filter.follows(*patterns))
        if dispatcher:
            _dispatchers.append(dispatcher)
        listen(MessageReceived, MessageEdited)(func)


    def handle_command(self, alc: FuncMounter[Any, MessageChain]) -> Callable:
        async def wrapper(ctx: Context, message: MessageChain):
            try:
                arp = alc.parse(message)
            except Exception as e:
                await ctx.scene.send_message(str(e))
                return
            res = list(alc.exec_result.values())[0]
            if arp.matched:
                if is_awaitable(res):
                    res = await res
                if isinstance(res, (str, MessageChain)):
                    await ctx.scene.send_message(res)
        return wrapper