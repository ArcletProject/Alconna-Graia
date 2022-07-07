from typing import Union

from graia.ariadne.model import Friend
from graia.ariadne.app import Ariadne
from graia.ariadne.message.element import At, Image
from graia.broadcast.builtin.decorators import Depend
from graia.broadcast.exceptions import ExecutionStop

from arclet.alconna.typing import PatternModel, pattern_map, BasePattern
from .dispatcher import AlconnaProperty


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
    当 Arpamar 解析成功后
    """

    def __wrapper__(result: AlconnaProperty):
        if result.result.query(path, "\0") == "\0" and not result.output_text:
            raise ExecutionStop
        return True

    return Depend(__wrapper__)


__all__ = ["ImgOrUrl", "AtID", "fetch_name", "match_path"]
