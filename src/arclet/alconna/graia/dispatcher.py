import asyncio
from atexit import register
from typing import Any, ClassVar, Literal, get_args, Optional, TYPE_CHECKING, Dict
from arclet.alconna.completion import CompSession
from arclet.alconna.core import Alconna
from arclet.alconna.builtin import generate_duplication
from arclet.alconna.duplication import Duplication
from arclet.alconna.stub import ArgsStub, OptionStub, SubcommandStub
from arclet.alconna.tools import AlconnaFormat, AlconnaString
from graia.amnesia.message import MessageChain
from graia.amnesia.message.element import Text
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.exceptions import ExecutionStop, PropagationCancelled
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.interrupt import InterruptControl
from launart import Launart
from tarina import generic_isinstance, generic_issubclass, lang, LRU
from tarina.generic import get_origin
from creart import it
from arclet.alconna import Arparma, Empty, output_manager
from arclet.alconna.exceptions import SpecialOptionTriggered

from .model import CommandResult, Header, Match, Query, CompConfig, TConvert
from .service import AlconnaGraiaService
from .adapter import AlconnaGraiaAdapter

if TYPE_CHECKING:
    result_cache: Dict[int, LRU[str, asyncio.Future[Optional[CommandResult]]]]
else:
    result_cache = {}


def get_future(alc: Alconna, source: str):
    return result_cache[alc._hash].get(source)


def set_future(alc: Alconna, source: str):
    return result_cache[alc._hash].setdefault(source, asyncio.Future())


def clear():
    for lru in result_cache.values():
        lru.clear()
    result_cache.clear()


register(clear)


class AlconnaOutputMessage(Dispatchable):
    """
    Alconna 信息输出事件
    如果触发的某个命令的可能输出 (帮助信息、模糊匹配、报错等), AlconnaDisptcher的send_flag为post时, 会发送该事件
    """

    def __init__(self, command: Alconna, text: str, source: Dispatchable):
        self.command = command
        self.output = text
        self.source_event = source

    class Dispatcher(BaseDispatcher):
        @classmethod
        async def catch(cls, interface: "DispatcherInterface[AlconnaOutputMessage]"):
            if interface.name == "output" and interface.annotation == str:
                return interface.event.output
            if isinstance(interface.annotation, Alconna):
                return interface.event.command
            if issubclass(interface.annotation, type(interface.event.source_event)) or isinstance(
                interface.event.source_event, interface.annotation
            ):
                return interface.event.source_event


class AlconnaDispatcher(BaseDispatcher):
    @classmethod
    def from_format(cls, command: str, args: Optional[Dict[str, Any]] = None):
        return cls(AlconnaFormat(command, args), send_flag="reply")

    @classmethod
    def from_command(cls, command: str, *options: str):
        factory = AlconnaString(command)
        for option in options:
            factory.option(option)
        return cls(factory.build(), send_flag="reply")

    default_send_handler: ClassVar[TConvert] = lambda _, x: MessageChain([Text(x)])

    def __init__(
        self,
        command: Alconna,
        *,
        send_flag: Literal["reply", "post", "stay"] = "reply",
        skip_for_unmatch: bool = True,
        comp_session: Optional[CompConfig] = None,
        message_converter: Optional[TConvert] = None,
        remove_tome: bool = True,
    ):
        """
        构造 Alconna调度器
        Args:
            command (Alconna): Alconna实例
            send_flag ("reply", "post", "stay"): 输出信息的发送方式
            skip_for_unmatch (bool): 当指令匹配失败时是否跳过对应的事件监听器, 默认为 True
            comp_session (CompConfig, optional): 补全会话配置, 不传入则不启用补全会话
            remove_tome (bool, optional): 是否移除首部的 @自己，默认为 True
        """
        super().__init__()
        self.command = command
        self.send_flag = send_flag
        self.skip_for_unmatch = skip_for_unmatch
        self.comp_session = comp_session
        self.converter = message_converter or self.__class__.default_send_handler
        self.remove_tome = remove_tome
        self._interface = CompSession(self.command)
        result_cache.setdefault(command._hash, LRU(10))
        self._comp_help = ""
        self._waiter = None
        if self.comp_session is not None:
            _tab = self.comp_session.get("tab") or ".tab"
            _enter = self.comp_session.get("enter") or ".enter"
            _exit = self.comp_session.get("exit") or ".exit"
            disables = self.comp_session.get("disables", set())
            hides = self.comp_session.get("hides", set())
            hide_tabs = self.comp_session.get("hide_tabs", False)
            if self.comp_session.get("lite", False):
                hide_tabs = True
                hides = {"tab", "enter", "exit"}
            hides |= disables
            if len(hides) < 3:
                template = f"\n\n{{}}{{}}{{}}{lang.require('comp/graia', 'other')}\n"
                self._comp_help = template.format(
                    (lang.require("comp/graia", "tab").format(cmd=_tab) + "\n")
                    if "tab" not in hides
                    else "",
                    (lang.require("comp/graia", "enter").format(cmd=_enter) + "\n")
                    if "enter" not in hides
                    else "",
                    (lang.require("comp/graia", "exit").format(cmd=_exit) + "\n")
                    if "exit" not in hides
                    else "",
                )

            async def _(message: MessageChain):
                msg = str(message)
                if msg.startswith(_exit) and "exit" not in disables:
                    if msg == _exit:
                        return False
                    return lang.require("analyser", "param_unmatched").format(
                        target=msg.replace(_exit, "", 1)
                    )

                elif msg.startswith(_enter) and "enter" not in disables:
                    if msg == _enter:
                        return True
                    return lang.require("analyser", "param_unmatched").format(
                        target=msg.replace(_enter, "", 1)
                    )

                elif msg.startswith(_tab) and "tab" not in disables:
                    offset = msg.replace(_tab, "", 1).lstrip() or 1
                    try:
                        offset = int(offset)
                    except ValueError:
                        return lang.require("analyser", "param_unmatched").format(target=offset)
                    else:
                        self._interface.tab(offset)
                        return (
                            f"* {self._interface.current()}"
                            if hide_tabs
                            else "\n".join(self._interface.lines())
                        )
                else:
                    return message

            self._waiter = _

    async def handle(self, source: Optional[Dispatchable], msg: MessageChain, adapter: AlconnaGraiaAdapter):
        inc = it(InterruptControl)
        if self.comp_session is None or not source:
            return self.command.parse(msg)  # type: ignore
        res = None
        with self._interface:
            res = self.command.parse(msg)  # type: ignore
        if res:
            return res
        res = Arparma(self.command.path, msg, False, error_info=SpecialOptionTriggered("completion"))
        while self._interface.available:
            await adapter.send(self.converter, res, f"{str(self._interface)}{self._comp_help}", source)
            while True:
                waiter = adapter.completion_waiter(source, self._waiter, self.comp_session.get('priority', 10))
                try:
                    ans: MessageChain = await inc.wait(
                        waiter, timeout=self.comp_session.get('timeout', 60)
                    )
                except asyncio.TimeoutError:
                    await adapter.send(self.converter, res, lang.require("comp/graia", "timeout"), source)
                    self._interface.exit()
                    return res
                if ans is False:
                    await adapter.send(self.converter, res, lang.require("comp/graia", "exited"), source)
                    self._interface.exit()
                    return res
                if isinstance(ans, str):
                    await adapter.send(self.converter, res, ans, source)
                    continue
                _res = self._interface.enter(None if ans is True else ans)
                if _res.result:
                    res = _res.result
                elif _res.exception and not isinstance(_res.exception, SpecialOptionTriggered):
                    await adapter.send(self.converter, res, str(_res.exception), source)
                break
        self._interface.exit()
        return res

    async def output(
        self,
        dii: DispatcherInterface,
        adapter: AlconnaGraiaAdapter,
        result: Arparma[MessageChain],
        output_text: Optional[str] = None,
        source: Optional[Dispatchable] = None,
    ):
        if not source or (result.matched or not output_text):
            return CommandResult(result, None, source)
        if self.send_flag == "stay":
            return CommandResult(result, output_text, source)
        if self.send_flag == "reply":
            await adapter.send(self.converter, result, output_text, source)
        elif self.send_flag == "post":
            dii.broadcast.postEvent(AlconnaOutputMessage(self.command, output_text, source), source)
        return CommandResult(result, None, source)

    async def beforeExecution(self, interface: DispatcherInterface):
        try:
            manager = Launart.current()
            if hasattr(manager, "get_service"):
                adapter = manager.get_service(AlconnaGraiaService.id).get_adapter()
            else:
                adapter = Launart.current().get_component(AlconnaGraiaService).get_adapter()
        except (ValueError, LookupError, AttributeError):
            adapter = AlconnaGraiaAdapter.instance()
        message: MessageChain = await adapter.lookup_source(interface, self.remove_tome)
        try:
            source = interface.event
        except LookupError:
            source = None
        if future := get_future(self.command, adapter.source_id(source)):
            await future
            if not (_property := future.result()):
                raise ExecutionStop
        else:
            fut = set_future(self.command, adapter.source_id(source))
            with output_manager.capture(self.command.name) as cap:
                output_manager.set_action(lambda x: x, self.command.name)
                try:
                    _res = await self.handle(source, message, adapter)
                except Exception as e:
                    _res = Arparma(self.command.path, message, False, error_info=e)
                may_help_text: Optional[str] = cap.get("output", None)
            if not may_help_text and not _res.matched and ((not _res.head_matched) or self.skip_for_unmatch):
                fut.set_result(None)
                raise ExecutionStop
            if not may_help_text and _res.error_info:
                may_help_text = repr(_res.error_info)
            _property = await self.output(interface, adapter, _res, may_help_text, source)
            fut.set_result(_property)
        if not _property.result.matched and not _property.output:
            raise PropagationCancelled
        interface.local_storage["alconna_result"] = _property
        return

    async def catch(self, interface: DispatcherInterface):
        res: CommandResult = interface.local_storage["alconna_result"]
        default_duplication = generate_duplication(self.command)(res.result)
        if interface.annotation is Duplication:
            return default_duplication
        if generic_issubclass(Duplication, interface.annotation):
            return interface.annotation(res.result)
        if generic_issubclass(get_origin(interface.annotation), CommandResult):
            return res
        if interface.annotation is ArgsStub:
            arg = ArgsStub(self.command.args)
            arg.set_result(res.result.all_matched_args)
            return arg
        if interface.annotation is OptionStub:
            return default_duplication.option(interface.name)
        if interface.annotation is SubcommandStub:
            return default_duplication.subcommand(interface.name)
        if generic_issubclass(get_origin(interface.annotation), Arparma):
            return res.result
        if interface.annotation is str and interface.name == "output":
            return res.output
        if generic_issubclass(interface.annotation, Alconna):
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
            result = res.result.query(q.path, Empty)
            if interface.annotation is Query:
                q.available = result != Empty
            elif get_origin(interface.annotation) is Query:
                q.available = generic_isinstance(result, get_args(interface.annotation)[0])
            if q.available:
                q.result = result
            elif interface.default.result != Empty:
                q.available = True
            return q
        if interface.name in res.result.all_matched_args:
            if generic_isinstance(res.result.all_matched_args[interface.name], interface.annotation):
                return res.result.all_matched_args[interface.name]
            return
