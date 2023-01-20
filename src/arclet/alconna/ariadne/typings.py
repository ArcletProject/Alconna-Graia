from nepattern import (
    URL,
    BasePattern,
    PatternModel,
    UnionArg,
)
from nepattern.main import INTEGER
from graia.ariadne.message.element import Image, At

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
            INTEGER,
        ]
    )
    @ "at_id"
)
"""
内置类型，允许传入提醒元素(At)或者'@xxxx'式样的字符串或者数字, 返回数字
"""
