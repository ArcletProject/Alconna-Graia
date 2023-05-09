from __future__ import annotations

from typing import Any
from arclet.alconna.argv import set_default_argv_type
from arclet.alconna._internal._argv import Argv
from graia.amnesia.message import MessageChain


class MessageChainArgv(Argv[MessageChain]):

    @staticmethod
    def generate_token(data: list[Any | list[str]]) -> int:
        return hash(''.join(i.__repr__() for i in data))


set_default_argv_type(MessageChainArgv)
