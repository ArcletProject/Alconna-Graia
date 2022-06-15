from typing import Union

from graia.ariadne.model import Friend
from graia.ariadne.app import Ariadne
from graia.ariadne.message.element import At, Image
from graia.broadcast.builtin.decorators import Depend

from arclet.alconna.typing import PatternModel, pattern_map, BasePattern
from .dispatcher import AlconnaProperty


def __valid(text: Union[Image, str]):
    if isinstance(text, Image):
        return text.url
    return pattern_map['url'].match(text)


ImgOrUrl = BasePattern(
    model=PatternModel.TYPE_CONVERT, origin=str, converter=__valid, alias='img_url',
    accepts=[str, Image]
)
"""
内置类型, 允许传入图片元素(Image)或者链接(URL)
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
            if isinstance(t, At):
                target = t.display
                if not target:
                    target = (await app.getUserProfile(t.target)).nickname
            else:
                target = t
        elif isinstance(event.sender, Friend):
            target = event.sender.nickname
        else:
            target = event.sender.name
        return target

    return Depend(__wrapper__)


__all__ = ["ImgOrUrl", "fetch_name"]
