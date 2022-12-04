from typing import List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from graia.saya import Channel
from graia.saya.schema import BaseSchema
from graia.saya.cube import Cube
from arclet.alconna import (
    Alconna,
    Option,
    Args,
    CommandMeta,
    Field,
    ArgFlag,
    Namespace,
    config
)

from .dispatcher import AlconnaDispatcher
from .saya import AlconnaSchema
from .shortcut import ensure_cube_as_listener, Wrapper, T_Callable


@dataclass
class AlcTempSchema(BaseSchema):
    options: List[Option] = field(default_factory=list)
    meta: CommandMeta = field(default=CommandMeta())
    args: Args = field(default=Args())
    namespace: Namespace = field(default=config.default_namespace)


def cube_mounted(func: Callable) -> Cube[AlcTempSchema]:
    if hasattr(func, "__cube__"):
        if not isinstance(func.__cube__.metaclass, AlcTempSchema):
            raise TypeError("Cube must be AlcTempSchema")
        return func.__cube__
    channel = Channel.current()
    for cube in channel.content:
        if cube.content is func and isinstance(cube.metaclass, AlcTempSchema):
            func.__cube__ = cube
            break
    else:
        cube = Cube(func, AlcTempSchema())
        channel.content.append(cube)
        func.__cube__ = cube
    return func.__cube__


def command(name: Optional[Any] = None, headers: Optional[List[Any]] = None) -> Wrapper:
    def wrapper(func: T_Callable):
        prev = cube_mounted(func)
        delattr(func, '__cube__')
        alc = Alconna(
            name or func.__name__,
            headers or [],
            prev.metaclass.args or Args(),
            *prev.metaclass.options,
            meta=prev.metaclass.meta,
            namespace=prev.metaclass.namespace
        )
        if alc.meta.example and "$" in alc.meta.example and alc.headers:
            alc.meta.example = alc.meta.example.replace("$", alc.headers[0])
        cube = ensure_cube_as_listener(func)
        cube.metaclass.inline_dispatchers.append(AlconnaDispatcher(alc, send_flag='reply'))
        channel = Channel.current()
        channel.use(AlconnaSchema(alc))(func)
        return func

    return wrapper


def option(name: str, args: Optional[Args] = None, help: Optional[str] = None) -> Wrapper:
    def wrapper(func: T_Callable):
        cube = cube_mounted(func)
        cube.metaclass.options.append(Option(name, args, help_text=help))
        return func

    return wrapper


def main_args(args: Args) -> Wrapper:
    def wrapper(func: T_Callable):
        cube = cube_mounted(func)
        cube.metaclass.args = args
        return func

    return wrapper


def argument(
        name: str,
        value: Optional[Any] = None,
        default: Union[Any, Field, None] = None,
        flags: Optional[List[ArgFlag]] = None,
) -> Wrapper:
    def wrapper(func: T_Callable):
        cube = cube_mounted(func)
        cube.metaclass.args.add(name, value=value, default=default, flags=flags)
        return func

    return wrapper


def meta(content: CommandMeta) -> Wrapper:
    def wrapper(func: T_Callable):
        cube = cube_mounted(func)
        cube.metaclass.meta = content
        return func

    return wrapper


def help(description: str, usage: Optional[str] = None, example: Optional[str] = None) -> Wrapper:
    def wrapper(func: T_Callable):
        cube = cube_mounted(func)
        cube.metaclass.meta = CommandMeta(description, usage, example)
        return func

    return wrapper


def namespace(np: Union[str, Namespace]) -> Wrapper:
    def wrapper(func: T_Callable):
        cube = cube_mounted(func)
        cube.metaclass.namespace = np if isinstance(np, Namespace) else Namespace(np)
        return func

    return wrapper
