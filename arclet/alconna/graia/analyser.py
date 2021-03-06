from arclet.alconna.exceptions import NullMessage
from arclet.alconna.util import split
from arclet.alconna.config import config
from arclet.alconna.base import StrMounter
from arclet.alconna.builtin.analyser import DefaultCommandAnalyser

from graia.amnesia.message import MessageChain
from graia.amnesia.message.element import Text


class GraiaCommandAnalyser(DefaultCommandAnalyser[MessageChain]):
    """Graia Project 相关的解析器"""
    @staticmethod
    def converter(command: str):
        return MessageChain([Text(command)])

    def process(self, data: MessageChain) -> 'GraiaCommandAnalyser':
        """命令分析功能, 传入字符串或消息链, 应当在失败时返回fail的arpamar"""
        if isinstance(data, str):
            exp = ValueError(f"{data} is not a MessageChain")
            if self.is_raise_exception:
                raise exp
            self.temporary_data["fail"] = exp
            return self
        self.origin_data = data
        i, exc = 0, None
        for unit in data:
            if (uname := unit.__class__.__name__) in self.filter_out:
                continue
            if (proc := self.preprocessors.get(uname)) and (res := proc(unit)):
                unit = res
            if isinstance(unit, Text):
                if not (res := split(unit.text.strip(), tuple(self.separators))):
                    continue
                self.raw_data.append(StrMounter(res))
            else:
                self.raw_data.append(unit)
            i += 1
        if i < 1:
            exp = NullMessage(config.lang.analyser_handle_null_message.format(target=data))
            if self.is_raise_exception:
                raise exp
            self.temporary_data["fail"] = exp
        else:
            self.ndata = i
            if config.enable_message_cache:
                self.temp_token = self.generate_token(self.raw_data)
        return self
