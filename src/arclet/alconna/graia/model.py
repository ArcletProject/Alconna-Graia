from dataclasses import dataclass, field
from typing import TypeVar, Generic, Optional

from arclet.alconna import Arparma

T_Source = TypeVar("T_Source")
T = TypeVar("T")


class Query(Generic[T]):
    result: T
    available: bool
    path: str

    def __init__(self, path: str, default: Optional[T] = None):
        self.path = path
        self.result = default
        self.available = False

    def __repr__(self):
        return f"Query({self.path}, {self.result})"


@dataclass
class Match(Generic[T]):
    result: T
    available: bool


@dataclass
class AlconnaProperty(Generic[T_Source]):
    """对解析结果的封装"""
    result: Arparma
    output: Optional[str] = field(default=None)
    source: T_Source = field(default=None)
