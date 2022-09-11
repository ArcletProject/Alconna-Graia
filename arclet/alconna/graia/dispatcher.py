import sys
from collections import deque
from typing import (
    Literal,
    Callable,
    Optional,
    TypedDict,
    get_args,
    Union,
    Dict,
    Any,
    Coroutine,
    ClassVar,
)
from contextlib import suppress
from arclet.alconna import (
    output_manager,
    Empty,
    Arpamar,
    AlconnaFormat,
    AlconnaString,
)
from arclet.alconna.core import Alconna, AlconnaGroup
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
from graia.ariadne.message.element import Quote
from graia.ariadne.typing import generic_issubclass, generic_isinstance, get_origin
from graia.ariadne.util import resolve_dispatchers_mixin

from .model import Query, Match, AlconnaProperty

success_record = deque(maxlen=10)
output_cache: Dict[int, set] = {}


def success_hook(event, args):
    if event in ["success_analysis"]:
        success_record.append(args[0])


sys.addaudithook(success_hook)


class AlconnaOutputDispatcher(BaseDispatcher):
    mixin = [ContextDispatcher]

    def __init__(
        self, command: Union[Alconna, AlconnaGroup], text: str, source: MessageEvent
    ):
        self.command = command
        self.output = text
        self.source_event = source

    async def catch(self, interface: "DispatcherInterface"):
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

    command: Union[Alconna, AlconnaGroup]
    """命令"""

    output: str
    """输出信息"""

    source_event: MessageEvent
    """来源事件"""


class _AlconnaLocalStorage(TypedDict):
    alconna_result: AlconnaProperty[MessageEvent]


class AlconnaDispatcher(BaseDispatcher):
    @classmethod
    def from_format(cls, command: str, args: Optional[Dict[str, Any]] = None):
        return cls(AlconnaFormat(command, args), send_flag="reply")

    @classmethod
    def from_command(cls, command: str, *options: str):
        return cls(AlconnaString(command, *options), send_flag="reply")

    default_send_handler: ClassVar[
        Callable[[str], Union[MessageChain, Coroutine[Any, Any, MessageChain]]]
    ] = lambda x: MessageChain(x)

    def __init__(
        self,
        command: Union[Alconna, AlconnaGroup],
        *,
        send_flag: Literal["reply", "post", "stay"] = "reply",
        skip_for_unmatch: bool = True,
        send_handler: Optional[
            Callable[[str], Union[MessageChain, Coroutine[Any, Any, MessageChain]]]
        ] = None,
        allow_quote: bool = False,
    ):
        """
        构造 Alconna调度器
        Args:
            command (Alconna | AlconnaGroup): Alconna实例
            send_flag ("reply", "post", "stay"): 输出信息的发送方式
            skip_for_unmatch (bool): 当指令匹配失败时是否跳过对应的事件监听器, 默认为 True
            allow_quote (bool): 是否允许引用回复消息触发对应的命令, 默认为 False
        """
        super().__init__()
        self.command = command
        self.send_flag = send_flag
        self.skip_for_unmatch = skip_for_unmatch
        self.send_handler = send_handler or self.__class__.default_send_handler
        self.allow_quote = allow_quote

    async def send_output(
        self,
        result: Arpamar,
        output_text: Optional[str] = None,
        source: Optional[MessageEvent] = None,
    ) -> AlconnaProperty[MessageEvent]:
        if not result.matched or not output_text:
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

    async def fetch_quote(self, message: MessageChain) -> bool:
        return not self.allow_quote and message.has(Quote)

    async def beforeExecution(self, interface: DispatcherInterface):
        message: MessageChain = await interface.lookup_param(
            "message", MessageChain, None
        )
        if await self.fetch_quote(message):
            raise ExecutionStop

        may_help_text = None

        def _h(string):
            nonlocal may_help_text
            may_help_text = string

        try:
            output_manager.set_action(_h, self.command.name)
            _res = self.command.parse(message)  # type: ignore
        except Exception as e:
            _res = Arpamar(
                self.command.commands[0] if self.command._group else self.command
            )
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
            may_help_text = (
                str(_res.error_info).strip("'").strip("\\n").split("\\n")[-1]
            )
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
        command: Alconna = (
            self.command.commands[0] if self.command._group else self.command
        )
        default_duplication = generate_duplication(command)
        default_duplication.set_target(res.result)
        if interface.annotation is Duplication:
            return default_duplication
        if generic_issubclass(Duplication, interface.annotation):
            return interface.annotation(command).set_target(res.result)
        if generic_issubclass(get_origin(interface.annotation), AlconnaProperty):
            return res
        if interface.annotation is ArgsStub:
            arg = ArgsStub(command.args)
            arg.set_result(res.result.main_args)
            return arg
        if interface.annotation is OptionStub:
            return default_duplication.option(interface.name)
        if interface.annotation is SubcommandStub:
            return default_duplication.subcommand(interface.name)
        if generic_issubclass(get_origin(interface.annotation), Arpamar):
            return res.result
        if interface.annotation is str and interface.name == "output":
            return res.output
        if generic_issubclass(interface.annotation, (Alconna, AlconnaGroup)):
            return self.command
        if interface.annotation is Match:
            r = res.result.all_matched_args.get(interface.name, Empty)
            return Match(r, r != Empty)
        if get_origin(interface.annotation) is Match:
            r = res.result.all_matched_args.get(interface.name, Empty)
            return Match(r, generic_isinstance(r, get_args(interface.annotation)[0]))
        if isinstance(interface.default, Query):
            return Query(interface.default.path, interface.default.result).set_result(
                res.result.query_with(
                    get_args(interface.annotation)[0], interface.default.path, Empty
                )
                if get_origin(interface.annotation) is Query
                else res.result.query(interface.default.path, Empty)
            )
        if interface.name in res.result.all_matched_args:
            if generic_isinstance(
                res.result.all_matched_args[interface.name], interface.annotation
            ):
                return res.result.all_matched_args[interface.name]
            return
