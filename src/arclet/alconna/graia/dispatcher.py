from __future__ import annotations

import sys
from collections import deque
from typing import (
    Literal,
    Callable,
    TypedDict,
    get_args,
    Any,
    Coroutine,
    ClassVar,
)
from contextlib import suppress
from arclet.alconna import output_manager, Empty, Arparma
from arclet.alconna.core import Alconna, AlconnaGroup
from arclet.alconna.tools import AlconnaString, AlconnaFormat
from arclet.alconna.components.duplication import Duplication, generate_duplication
from arclet.alconna.components.stub import ArgsStub, OptionStub, SubcommandStub
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.exceptions import ExecutionStop, PropagationCancelled
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.utilles import run_always_await
from graia.amnesia.message import MessageChain
from graia.ariadne.dispatcher import ContextDispatcher
from graia.ariadne.event.message import GroupMessage, MessageEvent
from graia.ariadne.typing import generic_issubclass, generic_isinstance, get_origin
from graia.ariadne.util import resolve_dispatchers_mixin

from .model import Query, Match, AlconnaProperty, Header

success_record = deque(maxlen=10)
output_cache: dict[int, set] = {}


def success_hook(event, args):
    if event in ["success_analysis"]:
        success_record.append(args[0])


sys.addaudithook(success_hook)


class AlconnaOutputDispatcher(BaseDispatcher):
    mixin = [ContextDispatcher]

    def __init__(
        self, command: Alconna | AlconnaGroup, text: str, source: MessageEvent
    ):
        self.command = command
        self.output = text
        self.source_event = source

    async def catch(self, interface: DispatcherInterface):
        if interface.name == "output" and interface.annotation == str:
            return self.output
        if isinstance(interface.annotation, (Alconna, AlconnaGroup)):
            return self.command
        if (
            issubclass(interface.annotation, MessageEvent)
            or interface.annotation == MessageEvent
        ):
            return self.source_event


class AlconnaOutputMessage(Dispatchable):
    """
    Alconna 信息输出事件
    如果触发的某个命令的可能输出 (帮助信息、模糊匹配、报错等), AlconnaDisptcher的send_flag为post时, 会发送该事件
    """

    command: Alconna | AlconnaGroup
    """命令"""

    output: str
    """输出信息"""

    source_event: MessageEvent
    """来源事件"""


class _AlconnaLocalStorage(TypedDict):
    alconna_result: AlconnaProperty[MessageEvent]


class AlconnaDispatcher(BaseDispatcher):
    @classmethod
    def from_format(cls, command: str, args: dict[str, Any] | None = None):
        return cls(AlconnaFormat(command, args), send_flag="reply")

    @classmethod
    def from_command(cls, command: str, *options: str):
        return cls(AlconnaString(command, *options), send_flag="reply")

    default_send_handler: ClassVar[
        Callable[[str], MessageChain | Coroutine[Any, Any, MessageChain]]
    ] = lambda x: MessageChain(x)

    def __init__(
        self,
        command: Alconna | AlconnaGroup,
        *,
        send_flag: Literal["reply", "post", "stay"] = "reply",
        skip_for_unmatch: bool = True,
        send_handler: Callable[[str], MessageChain | Coroutine[Any, Any, MessageChain]]
        | None = None,
    ):
        """
        构造 Alconna调度器
        Args:
            command (Alconna | AlconnaGroup): Alconna实例
            send_flag ("reply", "post", "stay"): 输出信息的发送方式
            skip_for_unmatch (bool): 当指令匹配失败时是否跳过对应的事件监听器, 默认为 True
        """
        super().__init__()
        self.command = command
        self.send_flag = send_flag
        self.skip_for_unmatch = skip_for_unmatch
        self.send_handler = send_handler or self.__class__.default_send_handler

    async def send_output(
        self,
        result: Arparma,
        output_text: str | None = None,
        source: MessageEvent | None = None,
    ) -> AlconnaProperty[MessageEvent]:
        if not isinstance(source, MessageEvent) or (result.matched or not output_text):
            return AlconnaProperty(result, None, source)
        id_ = id(source) if source else 0
        cache = output_cache.setdefault(id_, set())
        if self.command in cache:
            return AlconnaProperty(result, None, source)
        cache.clear()
        cache.add(self.command)
        if self.send_flag == "stay":
            return AlconnaProperty(result, output_text, source)
        if self.send_flag == "reply":
            from graia.ariadne.app import Ariadne

            app: Ariadne = Ariadne.current()
            help_message: MessageChain = await run_always_await(
                self.send_handler, output_text
            )
            if isinstance(source, GroupMessage):
                await app.send_group_message(source.sender.group, help_message)
            else:
                await app.send_message(source.sender, help_message)  # type: ignore
        elif self.send_flag == "post":
            with suppress(LookupError):
                interface = DispatcherInterface.ctx.get()
                dispatchers = resolve_dispatchers_mixin([source.Dispatcher]) + [
                    AlconnaOutputDispatcher(self.command, output_text, source)
                ]
                for listener in interface.broadcast.default_listener_generator(
                    AlconnaOutputMessage
                ):
                    await interface.broadcast.Executor(listener, dispatchers)
                    listener.oplog.clear()
        return AlconnaProperty(result, None, source)

    async def beforeExecution(self, interface: DispatcherInterface):
        message: MessageChain = await interface.lookup_param(
            "message", MessageChain, None
        )

        may_help_text = None

        def _h(string):
            nonlocal may_help_text
            may_help_text = string

        try:
            output_manager.set_action(_h, self.command.name)
            _res = self.command.parse(message)  # type: ignore
        except Exception as e:
            _res = Arparma(self.command.path, message)
            _res.head_matched = False
            _res.matched = False
            _res.error_info = repr(e)
            _res.error_data = []
        if (
            not may_help_text
            and not _res.matched
            and ((not _res.head_matched) or self.skip_for_unmatch)
        ):
            raise ExecutionStop
        if not may_help_text and _res.error_info:
            may_help_text = _res.error_info.strip("'").strip("\\n").split("\\n")[-1]
        if not may_help_text and _res.matched:
            output_cache.clear()
            sys.audit("success_analysis", self.command)
        try:
            _property = await self.send_output(_res, may_help_text, interface.event)
        except LookupError:
            _property = await self.send_output(_res, may_help_text, None)
        local_storage: _AlconnaLocalStorage = interface.local_storage  # type: ignore
        if not _res.matched and not _property.output:
            raise PropagationCancelled
        local_storage["alconna_result"] = _property
        return

    async def catch(self, interface: DispatcherInterface):
        local_storage: _AlconnaLocalStorage = interface.local_storage  # type: ignore
        res = local_storage["alconna_result"]
        default_duplication = generate_duplication(self.command)
        default_duplication.set_target(res.result)
        if interface.annotation is Duplication:
            return default_duplication
        if generic_issubclass(Duplication, interface.annotation):
            return interface.annotation(self.command).set_target(res.result)
        if generic_issubclass(get_origin(interface.annotation), AlconnaProperty):
            return res
        if interface.annotation is ArgsStub:
            arg = ArgsStub(self.command.args)
            arg.set_result(res.result.main_args)
            return arg
        if interface.annotation is OptionStub:
            return default_duplication.option(interface.name)
        if interface.annotation is SubcommandStub:
            return default_duplication.subcommand(interface.name)
        if generic_issubclass(get_origin(interface.annotation), Arparma):
            return res.result
        if interface.annotation is str and interface.name == "output":
            return res.output
        if generic_issubclass(interface.annotation, (Alconna, AlconnaGroup)):
            return self.command
        if interface.annotation is Header:
            return Header(res.result.header, bool(res.result.header))
        if interface.annotation is Match:
            r = res.result.all_matched_args.get(interface.name, Empty)
            return Match(r, r != Empty)
        if get_origin(interface.annotation) is Match:
            r = res.result.all_matched_args.get(interface.name, Empty)
            return Match(r, generic_isinstance(r, get_args(interface.annotation)[0]))
        if isinstance(interface.default, Query):
            q = Query(interface.default.path, interface.default.result)
            q.result = res.result.query(q.path, Empty)
            if get_origin(interface.annotation) is Query:
                q.available = generic_isinstance(
                    q.result, get_args(interface.annotation)[0]
                )
            else:
                q.available = q.result is Empty
            return q
        if interface.name in res.result.all_matched_args:
            if generic_isinstance(
                res.result.all_matched_args[interface.name], interface.annotation
            ):
                return res.result.all_matched_args[interface.name]
            return
