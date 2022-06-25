import sys
from collections import deque
from dataclasses import dataclass, field
from typing import Literal, Callable, Optional, TypedDict, TypeVar, Generic, get_origin, get_args
from arclet.alconna import Alconna, output_manager, Empty
from arclet.alconna.arpamar import Arpamar
from arclet.alconna.util import generic_isinstance
from arclet.alconna.components.duplication import AlconnaDuplication, generate_duplication
from arclet.alconna.components.stub import ArgsStub, OptionStub, SubcommandStub
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.utilles import run_always_await
from graia.broadcast.entities.signatures import Force

from graia.ariadne.app import Ariadne, logger
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
    help_text: Optional[str] = field(default=None)
    source: T_Source = field(default=None)


class AlconnaHelpDispatcher(BaseDispatcher):
    mixin = [ContextDispatcher]

    def __init__(self, alconna: "Alconna", help_string: str, source_event: MessageEvent):
        self.command = alconna
        self.help_string = help_string
        self.source_event = source_event

    async def catch(self, interface: "DispatcherInterface"):
        if interface.name == "help_string" and interface.annotation == str:
            return self.help_string
        if isinstance(interface.annotation, Alconna):
            return self.command
        if issubclass(interface.annotation, MessageEvent) or interface.annotation == MessageEvent:
            return self.source_event


class AlconnaHelpMessage(Dispatchable):
    """
    Alconna帮助信息发送事件
    如果触发的某个命令的帮助选项, 当AlconnaDisptcher的reply_help为False时, 会发送该事件
    """

    command: "Alconna"
    """命令"""

    help_string: str
    """帮助信息"""

    source_event: MessageEvent
    """来源事件"""


class _AlconnaLocalStorage(TypedDict):
    alconna_result: AlconnaProperty[MessageEvent]


class AlconnaDispatcher(BaseDispatcher):
    def __init__(
            self,
            alconna: "Alconna",
            *,
            help_flag: Literal["reply", "post", "stay"] = "stay",
            skip_for_unmatch: bool = True,
            help_handler: Optional[Callable[[str], MessageChain]] = None,
            allow_quote: bool = False
    ):
        """
        构造 Alconna调度器
        Args:
            alconna (Alconna): Alconna实例
            help_flag ("reply", "post", "stay"): 帮助信息发送方式
            skip_for_unmatch (bool): 当指令匹配失败时是否跳过对应的事件监听器, 默认为 True
            allow_quote (bool): 是否允许引用回复消息触发对应的命令, 默认为 False
        """
        super().__init__()
        self.command = alconna
        self.help_flag = help_flag
        self.skip_for_unmatch = skip_for_unmatch
        self.help_handler = help_handler or (lambda x: MessageChain(x))
        self.allow_quote = allow_quote

    async def beforeExecution(self, interface: DispatcherInterface):
        async def reply_help_message(
                result: Arpamar,
                help_text: Optional[str] = None,
                source: Optional[MessageEvent] = None,
        ) -> AlconnaProperty[MessageEvent]:
            app: Ariadne = Ariadne.current()
            if result.matched is False and help_text:
                if self.help_flag == "reply":
                    help_message: MessageChain = await run_always_await(self.help_handler, help_text)
                    if isinstance(source, GroupMessage):
                        await app.send_group_message(source.sender.group, help_message)
                    else:
                        await app.send_message(source.sender, help_message)  # type: ignore
                    return AlconnaProperty(result, None, source)
                if self.help_flag == "post":
                    dispatchers = resolve_dispatchers_mixin(
                        [source.Dispatcher]) + [AlconnaHelpDispatcher(self.command, help_text, source)]
                    for listener in interface.broadcast.default_listener_generator(AlconnaHelpMessage):
                        await interface.broadcast.Executor(listener, dispatchers=dispatchers)
                        listener.oplog.clear()
                    return AlconnaProperty(result, None, source)
            return AlconnaProperty(result, help_text, source)

        message: MessageChain = await interface.lookup_param("message", MessageChain, None)
        if not self.allow_quote and message.has(Quote):
            raise ExecutionStop
        event: MessageEvent = interface.event
        try:
            may_help_text = None

            def _h(string):
                nonlocal may_help_text
                may_help_text = string

            output_manager.set_action(_h, self.command.name)

            _res = self.command.parse(message)
        except Exception as e:
            logger.warning(f"{self.command} error: {e}")
            interface.stop()
        else:
            if not _res.head_matched and self.skip_for_unmatch:
                raise ExecutionStop
            if not _res.matched and not may_help_text and self.skip_for_unmatch:
                raise ExecutionStop
            sys.audit("success_analysis", self.command.command)
            _property = await reply_help_message(_res, may_help_text, event)
            local_storage: _AlconnaLocalStorage = interface.local_storage  # type: ignore
            if not _res.matched and not _property.help_text:
                raise ExecutionStop
            local_storage['alconna_result'] = _property
            return

    async def catch(self, interface: DispatcherInterface):
        local_storage: _AlconnaLocalStorage = interface.local_storage  # type: ignore
        res = local_storage['alconna_result']
        default_duplication = generate_duplication(self.command)
        default_duplication.set_target(res.result)
        if interface.annotation == AlconnaDuplication:
            return default_duplication
        if generic_issubclass(AlconnaDuplication, interface.annotation):
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
        if interface.annotation == Arpamar:
            return res.result
        if interface.annotation == str and interface.name == "help_text":
            return res.help_text
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
