import asyncio
import sys
import traceback
from collections import deque
from typing import Any, Callable, ClassVar, Coroutine, Literal, get_args, Optional, TYPE_CHECKING, Dict, Union
from arclet.alconna.args import AllParam, Args
from arclet.alconna.completion import CompSession
from arclet.alconna.core import Alconna
from arclet.alconna.typing import CommandMeta
from arclet.alconna.duplication import Duplication, generate_duplication
from arclet.alconna.stub import ArgsStub, OptionStub, SubcommandStub
from arclet.alconna.manager import command_manager
from arclet.alconna.tools import AlconnaFormat, AlconnaString
from graia.amnesia.message import MessageChain
from graia.amnesia.message.element import Text
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.exceptions import ExecutionStop, PropagationCancelled
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.interrupt import InterruptControl
from launart import Launart
from tarina import generic_isinstance, generic_issubclass, lang
from tarina.generic import get_origin

from arclet.alconna import Arparma, Empty, output_manager
from arclet.alconna.exceptions import SpecialOptionTriggered

from .model import AlconnaProperty, Header, Match, Query, CompConfig
from .service import AlconnaGraiaInterface

if TYPE_CHECKING:
    from .adapter import AlconnaGraiaAdapter

success_record = deque(maxlen=10)


def success_hook(event, args):
    if event in ["success_analysis"]:
        success_record.append(args[0])


sys.addaudithook(success_hook)
OutType = Literal["help", "shortcut", "completion"]


class AlconnaOutputMessage(Dispatchable):
    """
    Alconna 信息输出事件
    如果触发的某个命令的可能输出 (帮助信息、模糊匹配、报错等), AlconnaDisptcher的send_flag为post时, 会发送该事件
    """


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

    default_send_handler: ClassVar[
        Callable[[OutType, str], Optional[Union[MessageChain, Coroutine[Any, Any, MessageChain]]]]
    ] = lambda _, x: MessageChain([Text(x)])

    def __init__(
        self,
        command: Alconna,
        *,
        send_flag: Literal["reply", "post", "stay"] = "reply",
        skip_for_unmatch: bool = True,
        comp_session: Optional[CompConfig] = None,
        message_converter: Callable[[OutType, str], Optional[Union[MessageChain, Coroutine[Any, Any, MessageChain]]]] = None,
    ):
        """
        构造 Alconna调度器
        Args:
            command (Alconna): Alconna实例
            send_flag ("reply", "post", "stay"): 输出信息的发送方式
            skip_for_unmatch (bool): 当指令匹配失败时是否跳过对应的事件监听器, 默认为 True
            comp_session (CompConfig, optional): 补全会话配置, 不传入则不启用补全会话
        """
        super().__init__()
        self.command = command
        self.send_flag = send_flag
        self.skip_for_unmatch = skip_for_unmatch
        self.comp_session = comp_session
        self.converter = message_converter or self.__class__.default_send_handler

    async def handle(self, dii: DispatcherInterface, msg: MessageChain, adapter: 'AlconnaGraiaAdapter'):
        inc = InterruptControl(dii.broadcast)
        interface = CompSession(self.command)
        if self.comp_session is None:
            return self.command.parse(msg)  # type: ignore
        _tab = Alconna(
            self.comp_session.get("tab", ".tab"),
            Args["offset", int, 1], meta=CommandMeta(hide=True, compact=True)
        )
        _enter = Alconna(
            self.comp_session.get("enter", ".enter"),
            Args["content", AllParam, []], meta=CommandMeta(hide=True, compact=True)
        )
        _exit = Alconna(
            self.comp_session.get("exit", ".exit"),
            meta=CommandMeta(hide=True, compact=True)
        )

        def clear():
            command_manager.delete(_tab)
            command_manager.delete(_enter)
            command_manager.delete(_exit)
            interface.clear()

        with interface:
            res = self.command.parse(msg)  # type: ignore
        while interface.available:
            res = Arparma(self.command.path, msg, False, error_info=SpecialOptionTriggered("completion"))
            await adapter.send(self, res, str(interface), dii.event, exclude=False)
            await adapter.send(
                self, res,
                f"{lang.require('alconna/graia', 'tab').format(cmd=_tab.command)}\n"
                f"{lang.require('alconna/graia', 'enter').format(cmd=_enter.command)}\n"
                f"{lang.require('alconna/graia', 'exit').format(cmd=_exit.command)}",
                dii.event,
                exclude=False
            )
            while True:
                waiter = adapter.completion_waiter(dii, self.comp_session.get('priority', 10))
                try:
                    ans: MessageChain = await inc.wait(waiter, timeout=30)  # type: ignore
                except asyncio.TimeoutError:
                    clear()
                    return res
                if _exit.parse(ans).matched:
                    clear()
                    return res
                if (mat := _tab.parse(ans)).matched:
                    interface.tab(mat.offset)
                    await adapter.send(self, res, "\n".join(interface.lines()), dii.event, exclude=False)
                    continue
                if (mat := _enter.parse(ans)).matched:
                    content = list(mat.content)
                    if not content or not content[0]:
                        content = None
                    try:
                        with interface:
                            res = interface.enter(content)
                    except Exception as e:
                        traceback.print_exc()
                        await adapter.send(self, res, str(e), dii.event, exclude=False)
                        continue
                    break
                else:
                    await adapter.send(self, res, interface.current(), dii.event, exclude=False)
        clear()
        return res

    async def beforeExecution(self, interface: DispatcherInterface):
        try:
            adapter = Launart.current().get_interface(AlconnaGraiaInterface).adapter
        except (ValueError, LookupError, AttributeError):
            from .adapter import AlconnaGraiaAdapter
            adapter = AlconnaGraiaAdapter.instance()
        message: MessageChain = await adapter.lookup_source(interface)

        with output_manager.capture(self.command.name) as cap:
            output_manager.set_action(lambda x: x, self.command.name)
            try:
                _res = await self.handle(interface, message, adapter)
            except Exception as e:
                _res = Arparma(self.command.path, message, False, error_info=repr(e))
            may_help_text: Optional[str] = cap.get("output", None)
        if not may_help_text and not _res.matched and ((not _res.head_matched) or self.skip_for_unmatch):
            raise ExecutionStop
        if not may_help_text and _res.error_info:
            may_help_text = _res.error_info.strip("'").strip("\\n").split("\\n")[-1]
        if not may_help_text and _res.matched:
            adapter.output_cache.clear()
            sys.audit("success_analysis", self.command)
        try:
            _property = await adapter.send(self, _res, may_help_text, interface.event)
        except LookupError:
            _property = await adapter.send(self, _res, may_help_text, None)
        if not _res.matched and not _property.output:
            raise PropagationCancelled
        interface.local_storage["alconna_result"] = _property
        return

    async def catch(self, interface: DispatcherInterface):
        res: AlconnaProperty = interface.local_storage["alconna_result"]
        default_duplication = generate_duplication(res.result)
        if interface.annotation is Duplication:
            return default_duplication
        if generic_issubclass(Duplication, interface.annotation):
            return interface.annotation(res.result)
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
