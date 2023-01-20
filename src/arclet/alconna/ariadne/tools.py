from __future__ import annotations

from typing import Any, Callable

from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import FriendMessage, GroupMessage
from graia.ariadne.message.element import At
from graia.ariadne.model import Friend
from graia.broadcast.builtin.decorators import Depend
from graia.broadcast.exceptions import ExecutionStop
from graia.saya.factory import SchemaWrapper, factory, buffer_modifier, BufferModifier

from arclet.alconna import Alconna, AlconnaGroup, Arparma
from arclet.alconna.tools import AlconnaString

from .dispatcher import AlconnaDispatcher
from ..graia.utils import listen
from ..graia.saya import AlconnaSchema
from ..graia.model import AlconnaProperty


def fetch_name(path: str = "name"):
    """
    在可能的命令输入中获取目标的名字

    要求 Alconna 命令中含有 Args[path;O:[str, At]] 参数
    """

    async def __wrapper__(app: Ariadne, result: AlconnaProperty):
        event = result.source
        arp = result.result
        if t := arp.all_matched_args.get(path, None):
            return t.representation or (await app.get_user_profile(t.target)).nickname if isinstance(t, At) else t
        elif isinstance(event.sender, Friend):
            return event.sender.nickname
        else:
            return event.sender.name

    return Depend(__wrapper__)


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


def check_account(path: str):
    """
    依据可能的指定路径, 检查路径是否为指向当前 bot 账号的 At 元素

    Args:
        path: 指定的路径
    """

    def __wrapper__(app: Ariadne, arp: Arparma):
        match: At | str = arp.query(path, "\0")
        if isinstance(match, str):
            return True
        if match.target == app.account:
            return True
        raise ExecutionStop

    return Depend(__wrapper__)


@buffer_modifier
def mention(path: str) -> BufferModifier:
    """
    检查路径是否为指向当前 bot 账号的 At 元素

    Args:
        path: 指定的路径
    """

    def wrapper(buffer: dict[str, Any]):
        buffer.setdefault("decorators", []).append(check_account(path))

    return wrapper
