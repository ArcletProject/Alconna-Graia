from nepattern import (
    BasePattern,
    MatchMode,
    UnionPattern,
)
from typing import Union
from nepattern.base import INTEGER
from avilla.core.elements import Notice

NoticeID = (
    UnionPattern[Union[str, Notice]](
        [
            BasePattern(
                mode=MatchMode.TYPE_CONVERT,
                origin=int,
                alias="Notice",
                accepts=Notice,
                converter=lambda _, x: int(x.target.pattern["member"]),  # type: ignore
            ),
            BasePattern(
                r"@(\d+)",
                mode=MatchMode.REGEX_CONVERT,
                origin=int,
                alias="@xxx",
                accepts=str,
            ),
            INTEGER,
        ]
    )
    @ "notice_id"
)
"""
内置类型，允许传入提醒元素(Notice)或者'@xxxx'式样的字符串或者数字, 返回数字
"""
