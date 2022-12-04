from typing import Any, Callable, Dict, List, Optional, Union

from arclet.alconna import (
    Alconna,
    Field,
    ArgFlag,
    Args,
    CommandMeta,
    Namespace,
    Option,
    config,
)
from graia.saya.factory import BufferModifier, SchemaWrapper, buffer_modifier, factory

from .dispatcher import AlconnaDispatcher
from .saya import AlconnaSchema


@factory
def command(
    name: Optional[Any] = None, headers: Optional[List[Any]] = None
) -> SchemaWrapper:
    def wrapper(func: Callable, buffer: Dict[str, Any]):
        alc = Alconna(
            name or func.__name__,
            headers or [],
            buffer.pop("args", Args()),
            *buffer.pop("options", []),
            meta=buffer.pop("meta", CommandMeta()),
            namespace=buffer.pop("namespace", config.default_namespace),
        )
        if alc.meta.example and "$" in alc.meta.example and alc.headers:
            alc.meta.example = alc.meta.example.replace("$", alc.headers[0])
        buffer.setdefault("dispatchers", []).append(
            AlconnaDispatcher(alc, send_flag="reply")
        )
        return AlconnaSchema(alc)

    return wrapper


@buffer_modifier
def option(
    name: str, args: Optional[Args] = None, help: Optional[str] = None
) -> BufferModifier:
    return lambda buffer: buffer.setdefault("options", []).append(
        Option(name, args, help_text=help)
    )


@buffer_modifier
def main_args(args: Args) -> BufferModifier:
    def wrapper(buffer: Dict[str, Any]):
        buffer["args"] = args

    return wrapper


@buffer_modifier
def argument(
    name: str,
    value: Optional[Any] = None,
    default: Union[Any, Field, None] = None,
    flags: Optional[List[ArgFlag]] = None,
) -> BufferModifier:
    def wrapper(buffer: Dict[str, Any]):
        if args := buffer.get("args"):
            args: Args
            args.add(name, value=value, default=default, flags=flags)
        else:
            buffer["args"] = Args().add(
                name, value=value, default=default, flags=flags
            )

    return wrapper


@buffer_modifier
def meta(content: CommandMeta) -> BufferModifier:
    def wrapper(buffer: Dict[str, Any]):
        buffer["meta"] = content

    return wrapper


@buffer_modifier
def help(
    description: str, usage: Optional[str] = None, example: Optional[str] = None
) -> BufferModifier:
    def wrapper(buffer: Dict[str, Any]):
        buffer["meta"] = CommandMeta(description, usage, example)

    return wrapper


@buffer_modifier
def namespace(np: Union[str, Namespace]) -> BufferModifier:
    def wrapper(buffer: Dict[str, Any]):
        buffer["namespace"] = np if isinstance(np, Namespace) else Namespace(np)

    return wrapper
