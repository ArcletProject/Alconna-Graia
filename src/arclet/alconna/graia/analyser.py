from __future__ import annotations

from typing import Any
from typing_extensions import Self

from arclet.alconna.exceptions import NullMessage
from arclet.alconna.config import config
from arclet.alconna.analyser import Analyser
from arclet.alconna.container import DataCollectionContainer

from graia.amnesia.message import MessageChain, __message_chain_class__, __text_element_class__
from graia.amnesia.message.element import Text


class MessageChainContainer(DataCollectionContainer):
    __message_chain_class__ = __message_chain_class__
    __text_element_class__ = __text_element_class__

    @staticmethod
    def generate_token(data: list[Any | list[str]]) -> int:
        return hash(''.join(i.__repr__() for i in data))

    def build(self, data: MessageChain) -> Self:
        if not isinstance(data, MessageChain):
            exp = ValueError(f"{data} is not a MessageChain")
            raise exp
        self.reset()
        self.temporary_data["origin"] = data
        i, exc = 0, None
        for unit in data:
            if (uname := unit.__class__.__name__) in self.filter_out:
                continue
            if (proc := self.preprocessors.get(uname)) and (res := proc(unit)):
                unit = res
            if isinstance(unit, Text):
                if not (res := unit.text.strip()):
                    continue
                self.raw_data.append(res)
            else:
                self.raw_data.append(unit)
            i += 1
        if i < 1:
            raise NullMessage(config.lang.analyser_handle_null_message.format(target=data))
        self.ndata = i
        self.bak_data = self.raw_data.copy()
        if self.message_cache:
            self.temp_token = self.generate_token(self.raw_data)
        return self


class GraiaCommandAnalyser(Analyser[MessageChainContainer, MessageChain]):
    """Graia Project 相关的解析器"""

    def converter(self, command: str):
        return self.container.__message_chain_class__(
            [self.container.__text_element_class__(command)]
        )


GraiaCommandAnalyser.default_container(MessageChainContainer)
