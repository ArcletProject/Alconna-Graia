from __future__ import annotations

from typing import Any, Callable, Union

from avilla.core.selector import Selector
from avilla.core.context import Context
from avilla.core.elements import Notice
from avilla.core.tools.filter import Filter
from avilla.standard.core.message import MessageEdited, MessageReceived
from avilla.standard.core.profile import Nick
from graia.amnesia.message import MessageChain
from graia.amnesia.message.element import Text
from graia.broadcast import BaseDispatcher
from graia.broadcast.builtin.decorators import Depend
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.interrupt import Waiter
from graia.broadcast.utilles import run_always_await

from arclet.alconna.tools.construct import FuncMounter
from tarina import is_awaitable

from ..graia.model import CommandResult, TConvert
from ..graia.adapter import AlconnaGraiaAdapter
from ..graia.dispatcher import AlconnaDispatcher
from ..graia.utils import listen

AlconnaDispatcher.default_send_handler = lambda _, x: MessageChain([Text(x)])

AvillaMessageEvent = Union[MessageEdited, MessageReceived]


class AlconnaAvillaAdapter(AlconnaGraiaAdapter[AvillaMessageEvent]):

    def is_tome(self, message: MessageChain, account: Selector):
        if message.content and isinstance(message[0], Notice):
            notice: Notice = message.get_first(Notice)
            if notice.target.last_value == account.last_value:
                return True
        return False

    def remove_tome(self, message: MessageChain, account: Selector):
        if self.is_tome(message, account):
            message = MessageChain(message.content.copy())
            message.content.remove(message.get_first(Notice))
            if message.content and isinstance(message.content[0], Text):
                text = message.content[0].text.lstrip()  # type: ignore
                if not text:
                    message.content.pop(0)
                else:
                    message.content[0] = Text(text)
            return message
        return message

    def completion_waiter(self, source: AvillaMessageEvent, handle, priority: int = 15) -> Waiter:
        @Waiter.create_using_function(
            [MessageReceived],
            block_propagation=True,
            priority=priority,
        )
        async def waiter(event: MessageReceived):
            if event.context.client == source.context.client:
                return await handle(self.remove_tome(event.message.content, event.context.self))

        return waiter  # type: ignore

    async def lookup_source(
        self,
        interface: DispatcherInterface[AvillaMessageEvent],
        need_tome: bool = True,
        remove_tome: bool = True
    ) -> MessageChain:
        message = interface.event.message.content
        if need_tome and not self.is_tome(message, interface.event.context.self):
            raise ExecutionStop
        if remove_tome:
            return self.remove_tome(message, interface.event.context.self)
        return message

    def source_id(self, source: AvillaMessageEvent | None = None) -> str:
        return f"{source.message.id}@{source.context.account}" if source else "_"

    async def send(
        self,
        converter: TConvert,
        output_type: str,
        output_text: str | None = None,
        source: AvillaMessageEvent | None = None,
    ) -> None:
        ctx: Context = source.context
        help_message: MessageChain = await run_always_await(
            converter,
            output_type,
            output_text,
        )
        await ctx.scene.send_message(help_message)

    def fetch_name(self, path: str) -> Depend:
        async def __wrapper__(ctx: Context, result: CommandResult[MessageReceived]):
            arp = result.result
            if t := arp.query[Union[str, Notice]](path):
                if isinstance(t, Notice):
                    if t.display:
                        return t.display
                    nick = await ctx.client.pull(Nick)
                    return nick.nickname or nick.name
                return t
            else:
                nick = await ctx.client.pull(Nick)
                return nick.nickname or nick.name

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
                arp = alc.parse(self.remove_tome(message, ctx.self))
            except Exception as e:
                await ctx.scene.send_message(str(e))
                return
            if arp.matched:
                res = list(alc.exec_result.values())[0]
                if is_awaitable(res):
                    res = await res
                if isinstance(res, (str, MessageChain)):
                    await ctx.scene.send_message(res)

        return wrapper
