from __future__ import annotations

from typing import Any, Callable 

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
    name: Any | None = None, headers: list[Any] | None = None
) -> SchemaWrapper:
    def wrapper(func: Callable, buffer: dict[str, Any]):
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
    name: str, args: Args | None = None, help: str | None = None
) -> BufferModifier:
    return lambda buffer: buffer.setdefault("options", []).append(
        Option(name, args, help_text=help)
    )


@buffer_modifier
def main_args(args: Args) -> BufferModifier:
    def wrapper(buffer: dict[str, Any]):
        buffer["args"] = args

    return wrapper


@buffer_modifier
def argument(
    name: str,
    value: Any | None = None,
    default: Any | Field | None = None,
    flags: list[ArgFlag] | None = None,
) -> BufferModifier:
    def wrapper(buffer: dict[str, Any]):
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
    def wrapper(buffer: dict[str, Any]):
        buffer["meta"] = content

    return wrapper


@buffer_modifier
def help(
    description: str, usage: str | None = None, example: str | None = None
) -> BufferModifier:
    def wrapper(buffer: dict[str, Any]):
        buffer["meta"] = CommandMeta(description, usage, example)

    return wrapper


@buffer_modifier
def namespace(np: str | Namespace) -> BufferModifier:
    def wrapper(buffer: dict[str, Any]):
        buffer["namespace"] = np if isinstance(np, Namespace) else Namespace(np)

    return wrapper
