from __future__ import annotations

import contextlib
import inspect
import sys
import types
from typing import Any, Callable, Generator, TypeVar, Union, get_args


from graia.broadcast import Decorator
from graia.broadcast.entities.event import Dispatchable
from graia.saya.builtins.broadcast import ListenerSchema
from graia.saya.factory import SchemaWrapper, factory
from typing_extensions import Annotated, ParamSpec, get_origin as typing_ext_get_origin


Unions = (Union, types.UnionType) if sys.version_info >= (3, 10) else (Union,)
AnnotatedType = type(Annotated[int, lambda x: x > 0])


def get_origin(obj: Any) -> Any:
    return typing_ext_get_origin(obj) or obj


def generic_issubclass(cls: Any, par: Union[type, Any, tuple[type, ...]]) -> bool:
    """检查 cls 是否是 args 中的一个子类, 支持泛型, Any, Union

    Args:
        cls (type): 要检查的类
        par (Union[type, Any, Tuple[type, ...]]): 要检查的类的父类

    Returns:
        bool: 是否是父类
    """
    if par is Any:
        return True
    with contextlib.suppress(TypeError):
        if isinstance(par, AnnotatedType):
            return generic_issubclass(cls, get_args(par)[0])
        if isinstance(par, (type, tuple)):
            return issubclass(cls, par)
        if get_origin(par) in Unions:
            return any(generic_issubclass(cls, p) for p in get_args(par))
        if isinstance(par, TypeVar):
            if par.__constraints__:
                return any(generic_issubclass(cls, p) for p in par.__constraints__)
            if par.__bound__:
                return generic_issubclass(cls, par.__bound__)
    return False


T = TypeVar("T")


def gen_subclass(cls: type[T]) -> Generator[type[T], Any, Any]:
    yield cls
    for sub in cls.__subclasses__():
        yield from gen_subclass(sub)


@factory
def listen(*event: type[Dispatchable] | str) -> SchemaWrapper:
    """在当前 Saya Channel 中监听指定事件

    Args:
        *event (Union[Type[Dispatchable], str]): 事件类型或事件名称

    Returns:
        Callable[[T_Callable], T_Callable]: 装饰器
    """
    EVENTS: dict[str, type[Dispatchable]] = {e.__name__: e for e in gen_subclass(Dispatchable)}
    events: list[type[Dispatchable]] = [e if isinstance(e, type) else EVENTS[e] for e in event]

    def wrapper(func: Callable, buffer: dict[str, Any]) -> ListenerSchema:
        decorator_map: dict[str, Decorator] = buffer.pop("decorator_map", {})
        buffer["inline_dispatchers"] = buffer.pop("dispatchers", [])
        if decorator_map:
            sig = inspect.signature(func)
            for param in sig.parameters.values():
                if decorator := decorator_map.get(param.name):
                    setattr(param, "_default", decorator)
            func.__signature__ = sig
        return ListenerSchema(listening_events=events, **buffer)

    return wrapper


T_Callable = TypeVar("T_Callable", bound=Callable)

R = TypeVar("R")
P = ParamSpec("P")
