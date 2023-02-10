from __future__ import annotations

import sys
from collections import deque
from typing import Any, Callable, ClassVar, Coroutine, Literal, get_args

from arclet.alconna.components.duplication import Duplication, generate_duplication
from arclet.alconna.components.stub import ArgsStub, OptionStub, SubcommandStub
from arclet.alconna.core import Alconna, AlconnaGroup
from arclet.alconna.tools import AlconnaFormat, AlconnaString
from graia.amnesia.message import __message_chain_class__, __text_element_class__, MessageChain
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.entities.event import Dispatchable
from graia.broadcast.exceptions import ExecutionStop, PropagationCancelled
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from launart import Launart
from nepattern.util import generic_isinstance

from arclet.alconna import Arparma, Empty, output_manager

from .model import AlconnaProperty, Header, Match, Query
from .service import AlconnaGraiaInterface
from .utils import generic_issubclass, get_origin

success_record = deque(maxlen=10)


def success_hook(event, args):
    if event in ["success_analysis"]:
        success_record.append(args[0])


sys.addaudithook(success_hook)


class AlconnaOutputMessage(Dispatchable):
    """
    Alconna 信息输出事件
    如果触发的某个命令的可能输出 (帮助信息、模糊匹配、报错等), AlconnaDisptcher的send_flag为post时, 会发送该事件
    """


class AlconnaDispatcher(BaseDispatcher):
    @classmethod
    def from_format(cls, command: str, args: dict[str, Any] | None = None):
        return cls(AlconnaFormat(command, args), send_flag="reply")

    @classmethod
    def from_command(cls, command: str, *options: str):
        return cls(AlconnaString(command, *options), send_flag="reply")

    default_send_handler: ClassVar[
        Callable[[str], MessageChain | Coroutine[Any, Any, MessageChain]]
    ] = lambda x: __message_chain_class__([__text_element_class__(x)])

    def __init__(
        self,
        command: Alconna | AlconnaGroup,
        *,
        send_flag: Literal["reply", "post", "stay"] = "reply",
        skip_for_unmatch: bool = True,
        message_converter: Callable[[str], MessageChain | Coroutine[Any, Any, MessageChain]] | None = None,
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
        self.converter = message_converter or self.__class__.default_send_handler

    async def beforeExecution(self, interface: DispatcherInterface):
        try:
            adapter = Launart.current().get_interface(AlconnaGraiaInterface).adapter
        except (ValueError, LookupError, AttributeError):
            from .adapter import AlconnaGraiaAdapter
            adapter = AlconnaGraiaAdapter.instance()
        message: MessageChain = await interface.lookup_param("message", MessageChain, None)

        with output_manager.capture(self.command.name) as cap:
            output_manager.set_action(lambda x: x, self.command.name)
            try:
                _res = self.command.parse(message)  # type: ignore
            except Exception as e:
                _res = Arparma(self.command.path, message, False, error_info=repr(e))
            may_help_text: str | None = cap.get("output", None)
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
