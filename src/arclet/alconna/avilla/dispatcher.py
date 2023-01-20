from __future__ import annotations

from contextlib import suppress

from avilla.core.context import Context
from avilla.spec.core.message import MessageReceived
from graia.amnesia.message import MessageChain
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.utilles import run_always_await

from arclet.alconna import Arparma

from ..graia.dispatcher import (
    AlconnaDispatcher,
    AlconnaGraiaOutputHandler,
    AlconnaOutputMessage,
)
from ..graia.model import AlconnaProperty


class AvillaOutputHandler(AlconnaGraiaOutputHandler[MessageReceived]):
    async def send(
        self,
        result: Arparma[MessageChain],
        output_text: str | None = None,
        source: MessageReceived | None = None,
    ) -> AlconnaProperty[MessageReceived]:
        if not isinstance(source, MessageReceived) or (result.matched or not output_text):
            return AlconnaProperty(result, None, source)
        id_ = id(source) if source else 0
        cache = self.output_cache.setdefault(id_, set())
        if self.dispatcher.command in cache:
            return AlconnaProperty(result, None, source)
        cache.clear()
        cache.add(self.dispatcher.command)
        if self.dispatcher.send_flag == "stay":
            return AlconnaProperty(result, output_text, source)
        if self.dispatcher.send_flag == "reply":
            ctx: Context = source.context
            help_message: MessageChain = await run_always_await(self.convert, output_text)
            await ctx.scene.send_message(help_message)
        elif self.dispatcher.send_flag == "post":
            with suppress(LookupError):
                interface = DispatcherInterface.ctx.get()
                dispatchers = [self.Dispatcher(self.dispatcher.command, output_text, source), source.Dispatcher]
                for listener in interface.broadcast.default_listener_generator(AlconnaOutputMessage):
                    await interface.broadcast.Executor(listener, dispatchers)
                    listener.oplog.clear()
        return AlconnaProperty(result, None, source)


AlconnaDispatcher: type[AlconnaDispatcher[AvillaOutputHandler]] = AlconnaDispatcher.default_handler(
    AvillaOutputHandler
)
