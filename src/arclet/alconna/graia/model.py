from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeVar, Generic 

from arclet.alconna import Arparma

T_Source = TypeVar("T_Source")
T = TypeVar("T")


class Query(Generic[T]):
    """
    查询项，表示参数是否可由 `Arparma.query` 查询并获得结果

    result (T): 查询结果

    available (bool): 查询状态

    path (str): 查询路径
    """
    result: T
    available: bool
    path: str

    def __init__(self, path: str, default: T | None = None):
        self.path = path
        self.result = default
        self.available = False

    def __repr__(self):
        return f"Query({self.path}, {self.result})"


@dataclass
class Match(Generic[T]):
    """
    匹配项，表示参数是否存在于 `all_matched_args` 内

    result (T): 匹配结果

    available (bool): 匹配状态
    """
    result: T
    available: bool


@dataclass
class AlconnaProperty(Generic[T_Source]):
    """对解析结果的封装"""
    result: Arparma
    output: str | None = field(default=None)
    source: T_Source = field(default=None)


@dataclass
class Header:
    """
    头部项，表示命令头部为特殊形式时的头部匹配

    result (T): 匹配结果

    available (bool): 匹配状态
    """
    result: dict
    available: bool
