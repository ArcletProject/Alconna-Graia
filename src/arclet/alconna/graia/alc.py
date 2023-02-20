from __future__ import annotations

from typing import Any, Callable

from graia.saya.factory import BufferModifier, SchemaWrapper, buffer_modifier, factory

from arclet.alconna import (
    Alconna,
    Args,
    Arg,
    CommandMeta,
    Namespace,
    Option,
    Subcommand,
    config,
)
from arclet.alconna.util import init_spec

from .dispatcher import AlconnaDispatcher
from .saya import AlconnaSchema


@factory
def command(name: Any | None = None, headers: list[Any] | None = None) -> SchemaWrapper:
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
        buffer.setdefault("dispatchers", []).append(AlconnaDispatcher(alc, send_flag="reply"))
        return AlconnaSchema(alc)

    return wrapper


@buffer_modifier
@init_spec(Option)
def option(opt: Option) -> BufferModifier:
    return lambda buffer: buffer.setdefault("options", []).append(opt)


@buffer_modifier
@init_spec(Subcommand)
def subcommand(sub: Subcommand) -> BufferModifier:
    return lambda buffer: buffer.setdefault("options", []).append(sub)


@buffer_modifier
def main_args(args: Args) -> BufferModifier:
    def wrapper(buffer: dict[str, Any]):
        buffer["args"] = args

    return wrapper


@buffer_modifier
@init_spec(Arg)
def argument(arg: Arg) -> BufferModifier:
    def wrapper(buffer: dict[str, Any]):
        if args := buffer.get("args"):
            args: Args
            args.__merge__(arg)
        else:
            buffer["args"] = Args().__merge__(arg)

    return wrapper


@buffer_modifier
def meta(content: CommandMeta) -> BufferModifier:
    def wrapper(buffer: dict[str, Any]):
        buffer["meta"] = content

    return wrapper


@buffer_modifier
def help(description: str, usage: str | None = None, example: str | None = None) -> BufferModifier:
    def wrapper(buffer: dict[str, Any]):
        buffer["meta"] = CommandMeta(description, usage, example)

    return wrapper


@buffer_modifier
def namespace(np: str | Namespace) -> BufferModifier:
    def wrapper(buffer: dict[str, Any]):
        buffer["namespace"] = np if isinstance(np, Namespace) else Namespace(np)

    return wrapper
