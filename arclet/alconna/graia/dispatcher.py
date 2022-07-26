import sys
from collections import deque
from dataclasses import dataclass, field
from typing import Literal, Callable, Optional, TypedDict, TypeVar, Generic, get_origin, get_args
from arclet.alconna import Alconna, output_manager, Empty
from arclet.alconna.arpamar import Arpamar
from arclet.alconna.util import generic_isinstance
from arclet.alconna.components.duplication import Duplication, generate_duplication
from arclet.alconna.components.stub import ArgsStub, OptionStub, SubcommandStub
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.utilles import run_always_await
from graia.broadcast.entities.signatures import Force

from graia.ariadne.dispatcher import ContextDispatcher
from graia.ariadne.event.message import GroupMessage, MessageEvent
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Quote
from graia.ariadne.typing import generic_issubclass
from graia.ariadne.util import resolve_dispatchers_mixin

T_Source = TypeVar('T_Source')
T = TypeVar("T")

success_record = deque(maxlen=10)


def success_hook(event, args):
    if event in ['success_analysis']:
        success_record.append(args[0])


sys.addaudithook(success_hook)


class Query(Generic[T]):
    result: T
    available: bool
    path: str

    def __init__(self, path: str, default: Optional[T] = None):
        self.path = path
        self.result = default
        self.available = False

    def set_result(self, obj: T):
        if obj != Empty:
            self.available = True
            self.result = obj
        return self

    def __repr__(self):
        return f"query<{self.available}>['{self.path}' >> {self.result}]"


@dataclass
class Match(Generic[T]):
    result: T
    available: bool


@dataclass
class AlconnaProperty(Generic[T_Source]):
    """对解析结果的封装"""
    result: Arpamar
    output_text: Optional[str] = field(default=None)
    source: T_Source = field(default=None)


class AlconnaOutputDispatcher(BaseDispatcher):
    mixin = [ContextDispatcher]

    def __init__(self, alconna: "Alconna", text: str, source: MessageEvent):
        self.command = alconna
        self.output = text
        self.source_event = source

    async def catch(self, interface: "DispatcherInterface"):
        if interface.name == "output" and interface.annotation == str:
            return self.output
        if isinstance(interface.annotation, Alconna):
            return self.command
        if issubclass(interface.annotation, MessageEvent) or interface.annotation == MessageEvent:
            return self.source_event


class AlconnaOutputMessage(Dispatchable):
    """
    Alconna 信息输出事件
    如果触发的某个命令的可能输出 (帮助信息、模糊匹配、报错等), AlconnaDisptcher的send_flag为post时, 会发送该事件
    """

    command: "Alconna"
    """命令"""

    output: str
    """输出信息"""

    source_event: MessageEvent
    """来源事件"""


class _AlconnaLocalStorage(TypedDict):
    alconna_result: AlconnaProperty[MessageEvent]


class AlconnaDispatcher(BaseDispatcher):
    def __init__(
            self,
            alconna: "Alconna",
            *,
            send_flag: Literal["reply", "post", "stay"] = "stay",
            skip_for_unmatch: bool = True,
            send_handler: Optional[Callable[[str], MessageChain]] = None,
            allow_quote: bool = False
    ):
        """
        构造 Alconna调度器
        Args:
            alconna (Alconna): Alconna实例
            send_flag ("reply", "post", "stay"): 输出信息的发送方式
            skip_for_unmatch (bool): 当指令匹配失败时是否跳过对应的事件监听器, 默认为 True
            allow_quote (bool): 是否允许引用回复消息触发对应的命令, 默认为 False
        """
        super().__init__()
        self.command = alconna
        self.send_flag = send_flag
        self.skip_for_unmatch = skip_for_unmatch
        self.send_handler = send_handler or (lambda x: MessageChain(x))
        self.allow_quote = allow_quote

    async def beforeExecution(self, interface: DispatcherInterface):
        async def send_output(
                result: Arpamar,
                output_text: Optional[str] = None,
                source: Optional[MessageEvent] = None,
        ) -> AlconnaProperty[MessageEvent]:
            from graia.ariadne.app import Ariadne
            app: Ariadne = Ariadne.current()
            if result.matched is False and output_text and source:
                if self.send_flag == "reply":
                    help_message: MessageChain = await run_always_await(self.send_handler, output_text)
                    if isinstance(source, GroupMessage):
                        await app.send_group_message(source.sender.group, help_message)
                    else:
                        await app.send_message(source.sender, help_message)  # type: ignore
                    return AlconnaProperty(result, None, source)
                if self.send_flag == "post":
                    dispatchers = resolve_dispatchers_mixin(
                        [source.Dispatcher]) + [AlconnaOutputDispatcher(self.command, output_text, source)]
                    for listener in interface.broadcast.default_listener_generator(AlconnaOutputMessage):
                        await interface.broadcast.Executor(listener, dispatchers=dispatchers)
                        listener.oplog.clear()
                    return AlconnaProperty(result, None, source)
            return AlconnaProperty(result, output_text, source)

        message: MessageChain = await interface.lookup_param("message", MessageChain, None)
        if not self.allow_quote and message.has(Quote):
            raise ExecutionStop

        may_help_text = None

        def _h(string):
            nonlocal may_help_text
            may_help_text = string

        try:
            output_manager.set_action(_h, self.command.name)
            _res = self.command.parse(message)
        except Exception as e:
            _res = Arpamar(self.command)
            _res.head_matched = False
            _res.matched = False
            _res.error_info = repr(e)
            _res.error_data = []
        if not may_help_text and not _res.matched and ((not _res.head_matched) or self.skip_for_unmatch):
            raise ExecutionStop
        if not may_help_text and _res.error_info:
            may_help_text = str(_res.error_info).strip('\'').strip('\\n').split('\\n')[-1]
        if not may_help_text and _res.matched:
            sys.audit("success_analysis", self.command.command)
        try:
            _property = await send_output(_res, may_help_text, interface.event)
        except LookupError:
            _property = await send_output(_res, may_help_text, None)
        local_storage: _AlconnaLocalStorage = interface.local_storage  # type: ignore
        if not _res.matched and not _property.output_text:
            raise ExecutionStop
        local_storage['alconna_result'] = _property
        return

    async def catch(self, interface: DispatcherInterface):
        local_storage: _AlconnaLocalStorage = interface.local_storage  # type: ignore
        res = local_storage['alconna_result']
        default_duplication = generate_duplication(self.command)
        default_duplication.set_target(res.result)
        if interface.annotation == Duplication:
            return default_duplication
        if generic_issubclass(Duplication, interface.annotation):
            return interface.annotation(self.command).set_target(res.result)
        if isinstance(interface.annotation, type) and issubclass(interface.annotation, AlconnaProperty):
            return res
        if get_origin(interface.annotation) is AlconnaProperty:
            return res
        if interface.annotation == ArgsStub:
            arg = ArgsStub(self.command.args)
            arg.set_result(res.result.main_args)
            return arg
        if interface.annotation == OptionStub:
            return default_duplication.option(interface.name)
        if interface.annotation == SubcommandStub:
            return default_duplication.subcommand(interface.name)
        if interface.annotation == Arpamar or get_origin(interface.annotation) == Arpamar:
            return res.result
        if interface.annotation == str and interface.name == "help_text":
            return res.output_text
        if generic_issubclass(interface.annotation, Alconna):
            return self.command
        if interface.annotation == Match:
            r = res.result.all_matched_args.get(interface.name, Empty)
            return Match(r, r != Empty)
        if get_origin(interface.annotation) == Match:
            r = res.result.all_matched_args.get(interface.name, Empty)
            return Match(r, generic_isinstance(r, get_args(interface.annotation)[0]))
        if isinstance(interface.default, Query):
            return Query(interface.default.path, interface.default.result).set_result(
                res.result.query_with(get_args(interface.annotation)[0], interface.default.path, Empty)
                if get_origin(interface.annotation) is Query else res.result.query(interface.default.path, Empty)
            )
        if interface.name in res.result.all_matched_args:
            if generic_isinstance(res.result.all_matched_args[interface.name], interface.annotation):
                return res.result.all_matched_args[interface.name]
            return
        if generic_issubclass(interface.annotation, MessageEvent) or interface.annotation == MessageEvent:
            return Force(res.source)
