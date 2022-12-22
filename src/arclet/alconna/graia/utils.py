from __future__ import annotations

import inspect
from functools import lru_cache
from typing import Any, Callable, TypeVar 

from arclet.alconna import Alconna, AlconnaGroup
from arclet.alconna.tools import AlconnaFormat, AlconnaString
from graia.amnesia.message import Element, MessageChain, Text
from graia.ariadne.event.message import FriendMessage, GroupMessage
from graia.ariadne.message.element import At, Image
from graia.ariadne.model import Friend
from graia.broadcast import Decorator, DecoratorInterface, DispatcherInterface
from graia.broadcast.builtin.decorators import Depend
from graia.broadcast.builtin.derive import Derive
from graia.broadcast.exceptions import ExecutionStop
from graia.saya.factory import BufferModifier, SchemaWrapper, buffer_modifier, factory
from graiax.shortcut.saya import gen_subclass, listen
from nepattern import (
    URL,
    AllParam,
    BasePattern,
    Empty,
    PatternModel,
    UnionArg,
    type_parser,
)

from .analyser import GraiaCommandAnalyser
from .dispatcher import AlconnaDispatcher, AlconnaProperty
from .saya import AlconnaSchema

T_Callable = TypeVar("T_Callable", bound=Callable)

ImgOrUrl = (
    UnionArg(
        [
            BasePattern(
                model=PatternModel.TYPE_CONVERT,
                origin=str,
                converter=lambda _, x: x.url,
                alias="img",
                accepts=[Image],
            ),
            URL,
        ]
    )
    @ "img_url"
)
"""
内置类型, 允许传入图片元素(Image)或者链接(URL)，返回链接
"""

AtID = (
    UnionArg(
        [
            BasePattern(
                model=PatternModel.TYPE_CONVERT,
                origin=int,
                alias="At",
                accepts=[At],
                converter=lambda _, x: x.target,
            ),
            BasePattern(
                r"@(\d+)",
                model=PatternModel.REGEX_CONVERT,
                origin=int,
                alias="@xxx",
                accepts=[str],
            ),
            type_parser(int),
        ]
    )
    @ "at_id"
)
"""
内置类型，允许传入提醒元素(At)或者'@xxxx'式样的字符串或者数字, 返回数字
"""


def fetch_name(path: str = "name"):
    """
    在可能的命令输入中获取目标的名字

    要求 Alconna 命令中含有 Args[path;O:[str, At]] 参数
    """
    from graia.ariadne.app import Ariadne

    async def __wrapper__(app: Ariadne, result: AlconnaProperty):
        event = result.source
        arp = result.result
        if t := arp.all_matched_args.get(path, None):
            return (
                t.representation or (await app.get_user_profile(t.target)).nickname
                if isinstance(t, At)
                else t
            )
        elif isinstance(event.sender, Friend):
            return event.sender.nickname
        else:
            return event.sender.name

    return Depend(__wrapper__)


def match_path(path: str):
    """
    当 Arpamar 解析成功后, 依据 path 是否存在以继续执行事件处理

    当 path 为 ‘$main’ 时表示认定当且仅当主命令匹配
    """

    def __wrapper__(result: AlconnaProperty):
        if path == "$main":
            if not result.result.components:
                return True
            raise ExecutionStop
        else:
            if result.result.query(path, "\0") == "\0":
                raise ExecutionStop
            return True

    return Depend(__wrapper__)


def match_value(path: str, value: Any, or_not: bool = False):
    """
    当 Arpamar 解析成功后, 依据查询 path 得到的结果是否符合传入的值以继续执行事件处理

    当 or_not 为真时允许查询 path 失败时继续执行事件处理
    """

    def __wrapper__(result: AlconnaProperty):
        if result.result.query(path) == value:
            return True
        if or_not and result.result.query(path, Empty) == Empty:
            return True
        raise ExecutionStop

    return Depend(__wrapper__)


def shortcuts(
    mapping: dict[str, MessageChain] | None = None, **kwargs: MessageChain
):
    def wrapper(func: T_Callable) -> T_Callable:
        kwargs.update(mapping or {})
        if hasattr(func, "__alc_shortcuts__"):
            getattr(func, "__alc_shortcuts__", {}).update(kwargs)
        else:
            setattr(func, "__alc_shortcuts__", kwargs)
        return func

    return wrapper


@factory
def alcommand(
    alconna: Alconna | AlconnaGroup | str,
    guild: bool = True,
    private: bool = True,
    send_error: bool = False,
    post: bool = False,
) -> SchemaWrapper:
    """
    saya-util 形式的注册一个消息事件监听器并携带 AlconnaDispatcher

    请将其放置在装饰器的顶层

    Args:
        alconna: 使用的 Alconna 命令
        guild: 命令是否群聊可用
        private: 命令是否私聊可用
        send_error: 是否发送错误信息
        post: 是否以事件发送输出信息
    """
    if isinstance(alconna, str):
        if not alconna.strip():
            raise ValueError(alconna)
        cmds = alconna.split(";")
        alconna = AlconnaString(cmds[0], *cmds[1:])
    if alconna.meta.example and "$" in alconna.meta.example and alconna.headers:
        alconna.meta.example = alconna.meta.example.replace("$", alconna.headers[0])

    def wrapper(func: Callable, buffer: dict[str, Any]):
        events = []
        if guild:
            events.append(GroupMessage)
        if private:
            events.append(FriendMessage)
        buffer.setdefault("dispatchers", []).append(
            AlconnaDispatcher(
                alconna, send_flag="post" if post else "reply", skip_for_unmatch=not send_error  # type: ignore
            )
        )
        listen(*events)(func)  # noqa
        return AlconnaSchema(alconna)

    return wrapper


@factory
def from_command(
    format_command: str,
    args: dict[str, type | BasePattern] | None = None,
    post: bool = False,
) -> SchemaWrapper:
    """
    saya-util 形式的仅注入一个 AlconnaDispatcher, 事件监听部分自行处理

    Args:
        format_command: 格式化命令字符串
        args: 格式化填入内容
        post: 是否以事件发送输出信息
    """

    def wrapper(func: Callable, buffer: dict[str, Any]):
        custom_args = {
            v.name: v.annotation for v in inspect.signature(func).parameters.values()
        }
        custom_args.update(args or {})
        cmd = AlconnaFormat(format_command, custom_args)
        buffer.setdefault("dispatchers", []).append(
            AlconnaDispatcher(cmd, send_flag="post" if post else "reply")  # type: ignore
        )
        return AlconnaSchema(cmd)

    return wrapper


_seminal = type("_seminal", (object,), {})


@buffer_modifier
def assign(path: str, value: Any = _seminal, or_not: bool = False) -> BufferModifier:
    """
    match_path 与 match_value 的合并形式
    """
    def wrapper(buffer: dict[str, Any]):
        if value == _seminal:
            if or_not:
                buffer.setdefault("decorators", []).append(match_path("$main"))
            buffer.setdefault("decorators", []).append(match_path(path))
        else:
            buffer.setdefault("decorators", []).append(match_value(path, value, or_not))

    return wrapper


@lru_cache()
def search_element(name: str):
    for i in gen_subclass(Element):
        if i.__name__ == name:
            return i


def _get_filter_out() -> list[type[Element]]:
    res = []
    for i in GraiaCommandAnalyser.filter_out:
        if t := search_element(i):
            res.append(t)
    return res


class MatchPrefix(Decorator, Derive[MessageChain]):
    pre = True

    def __init__(self, prefix: Any, extract: bool = False):  # noqa
        """
        利用 NEPattern 的前缀匹配

        Args:
            prefix: 检测的前缀, 支持格式有 a|b , ['a', At(...)] 等
            extract: 是否为提取模式, 默认为 False
        """
        pattern = type_parser(prefix)
        if pattern in (AllParam, Empty):
            raise ValueError(prefix)
        self.pattern = pattern.prefixed()
        self.extract = extract

    async def target(self, interface: DecoratorInterface):
        return await self(
            await interface.dispatcher_interface.lookup_param(
                "message_chain", MessageChain, None
            ),
            interface.dispatcher_interface,
        )

    async def __call__(
        self, chain: MessageChain, interface: DispatcherInterface
    ) -> MessageChain:
        header = chain.include(*_get_filter_out())
        rest: MessageChain = chain.exclude(*_get_filter_out())
        if not rest.content:
            raise ExecutionStop
        elem = rest.content[0]
        if isinstance(elem, Text) and (res := self.pattern.validate(elem.text)).success:
            if self.extract:
                return MessageChain([Text(str(res.value))])
            elem.text = elem.text[len(str(res.value)):].lstrip()
            return header + rest
        elif self.pattern.validate(elem).success:
            if self.extract:
                return MessageChain([elem])
            rest.content.remove(elem)
            return header + rest
        raise ExecutionStop


class MatchSuffix(Decorator, Derive[MessageChain]):
    pre = True

    def __init__(self, suffix: Any, extract: bool = False):  # noqa
        """
        利用 NEPattern 的后缀匹配

        Args:
            suffix: 检测的前缀, 支持格式有 a|b , ['a', At(...)] 等
            extract: 是否为提取模式, 默认为 False
        """
        pattern = type_parser(suffix)
        if pattern in (AllParam, Empty):
            raise ValueError(suffix)
        self.pattern = pattern.suffixed()
        self.extract = extract

    async def target(self, interface: DecoratorInterface):
        return await self(
            await interface.dispatcher_interface.lookup_param(
                "message_chain", MessageChain, None
            ),
            interface.dispatcher_interface,
        )

    async def __call__(
        self, chain: MessageChain, interface: DispatcherInterface
    ) -> MessageChain:
        header = chain.include(*_get_filter_out())
        rest: MessageChain = chain.exclude(*_get_filter_out())
        if not rest.content:
            raise ExecutionStop
        elem = rest.content[-1]
        if isinstance(elem, Text) and (res := self.pattern.validate(elem.text)).success:
            if self.extract:
                return MessageChain([Text(str(res.value))])
            elem.text = elem.text[: elem.text.rfind(str(res.value))].rstrip()
            return header + rest
        elif self.pattern.validate(elem).success:
            if self.extract:
                return MessageChain([elem])
            rest.content.remove(elem)
            return header + rest
        raise ExecutionStop


@buffer_modifier
def startswith(
    prefix: Any, include: bool = False, bind: str | None = None
) -> BufferModifier:
    """
    MatchPrefix 的 shortcut形式

    Args:
        prefix: 需要匹配的前缀
        include: 指示是否仅返回匹配部分, 默认为 False
        bind: 指定注入返回值的参数名称
    """
    decorator = MatchPrefix(prefix, include)

    def wrapper(buffer: dict[str, Any]):
        if bind:
            buffer.setdefault("decorator_map", {})[bind] = decorator
        else:
            buffer.setdefault("decorators", []).append(decorator)

    return wrapper


@buffer_modifier
def endswith(
    suffix: Any, include: bool = False, bind: str | None = None
) -> BufferModifier:
    """
    MatchSuffix 的 shortcut形式

    Args:
        suffix: 需要匹配的前缀
        include: 指示是否仅返回匹配部分, 默认为 False
        bind: 指定注入返回值的参数名称
    """
    decorator = MatchSuffix(suffix, include)

    def wrapper(buffer: dict[str, Any]):
        if bind:
            buffer.setdefault("decorator_map", {})[bind] = decorator
        else:
            buffer.setdefault("decorators", []).append(decorator)

    return wrapper


__all__ = [
    "ImgOrUrl",
    "AtID",
    "fetch_name",
    "match_path",
    "alcommand",
    "match_value",
    "from_command",
    "shortcuts",
    "assign",
    "startswith",
    "MatchPrefix",
    "endswith",
    "MatchSuffix",
]
