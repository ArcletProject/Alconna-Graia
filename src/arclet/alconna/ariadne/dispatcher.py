from __future__ import annotations

from contextlib import suppress

from graia.ariadne.dispatcher import ContextDispatcher
from graia.ariadne.event.message import GroupMessage, MessageEvent
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.util import resolve_dispatchers_mixin
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.utilles import run_always_await

from arclet.alconna import Arparma

from ..graia.dispatcher import (
    AlconnaDispatcher,
    AlconnaGraiaOutputHandler,
    AlconnaOutputMessage,
)
from ..graia.model import AlconnaProperty


class AriadneOutputHandler(AlconnaGraiaOutputHandler[MessageEvent]):
    async def send(
        self,
        result: Arparma[MessageChain],
        output_text: str | None = None,
        source: MessageEvent | None = None,
    ) -> AlconnaProperty[MessageEvent]:
        if not isinstance(source, MessageEvent) or (result.matched or not output_text):
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
            from graia.ariadne.app import Ariadne

            app: Ariadne = Ariadne.current()
            help_message: MessageChain = await run_always_await(self.convert, output_text)
            if isinstance(source, GroupMessage):
                await app.send_group_message(source.sender.group, help_message)
            else:
                await app.send_message(source.sender, help_message)  # type: ignore
        elif self.dispatcher.send_flag == "post":
            with suppress(LookupError):
                interface = DispatcherInterface.ctx.get()
                dispatchers = resolve_dispatchers_mixin([source.Dispatcher, ContextDispatcher]) + [
                    self.Dispatcher(self.dispatcher.command, output_text, source)
                ]
                for listener in interface.broadcast.default_listener_generator(AlconnaOutputMessage):
                    await interface.broadcast.Executor(listener, dispatchers)
                    listener.oplog.clear()
        return AlconnaProperty(result, None, source)


AlconnaDispatcher: type[AlconnaDispatcher[AriadneOutputHandler]] = AlconnaDispatcher.default_handler(
    AriadneOutputHandler
)
