from typing import Union, Any

from graia.saya.cube import Cube
from graia.saya.builtins.broadcast import ListenerSchema
from graia.ariadne.model import Friend
from graia.ariadne.message.element import At, Image
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.util.saya import ensure_cube_as_listener, Wrapper, T_Callable
from graia.broadcast.builtin.decorators import Depend
from graia.broadcast.exceptions import ExecutionStop

from arclet.alconna import Alconna, Empty
from arclet.alconna.typing import PatternModel, pattern_map, BasePattern
from .dispatcher import AlconnaProperty, AlconnaDispatcher


def __valid(text: Union[Image, str]):
    return text.url if isinstance(text, Image) else pattern_map['url'].match(text)


ImgOrUrl = BasePattern(
    model=PatternModel.TYPE_CONVERT, origin=str, converter=__valid, alias='img_url',
    accepts=[str, Image]
)
"""
内置类型, 允许传入图片元素(Image)或者链接(URL)，返回链接
"""

AtID = BasePattern(
    model=PatternModel.TYPE_CONVERT, origin=int, alias='at_id', accepts=[str, At, int],
    converter=lambda x: x.target if isinstance(x, At) else int(str(x).lstrip('@'))
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
            return t.display or (await app.getUserProfile(t.target)).nickname if isinstance(t, At) else t
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
        if path == '$main':
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


def command(alconna: Alconna, guild: bool = True, private: bool = True, send_error: bool = False) -> Wrapper:
    """
    saya-util 形式的注册一个消息事件监听器并携带 AlconnaDispatcher

    Args:
        alconna: 使用的 Alconna 命令
        guild: 命令是否群聊可用
        private: 命令是否私聊可用
        send_error: 是否发送错误信息
    """
    if '$' in alconna.help_text:
        alconna.help_text = alconna.help_text.replace('$', alconna.headers[0], 1)

    def wrapper(func: T_Callable) -> T_Callable:
        cube: Cube[ListenerSchema] = ensure_cube_as_listener(func)
        if guild:
            cube.metaclass.listening_events.append(GroupMessage)
        if private:
            cube.metaclass.listening_events.append(FriendMessage)
        cube.metaclass.inline_dispatchers.append(
            AlconnaDispatcher(alconna, send_flag='reply', skip_for_unmatch=not send_error))
        return func

    return wrapper


__all__ = ["ImgOrUrl", "AtID", "fetch_name", "match_path", "command", "match_value"]
