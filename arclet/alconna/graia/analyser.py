from arclet.alconna.exceptions import NullTextMessage
from arclet.alconna.util import split
from arclet.alconna.lang import lang_config
from arclet.alconna.builtin.analyser import DefaultCommandAnalyser

from graia.amnesia.message import MessageChain
from graia.amnesia.message.element import Text


class GraiaCommandAnalyser(DefaultCommandAnalyser[MessageChain]):
    """
    无序的分析器

    """
    @staticmethod
    def converter(command: str):
        return MessageChain([Text(command)])

    def process_message(self, data: MessageChain) -> 'GraiaCommandAnalyser':
        """命令分析功能, 传入字符串或消息链, 应当在失败时返回fail的arpamar"""
        if isinstance(data, str):
            exp = ValueError(f"{data} is not a MessageChain")
            if self.is_raise_exception:
                raise exp
            self.temporary_data["fail"] = exp
            return self
        self.origin_data = data
        separates = self.separators
        i, __t, exc = 0, False, None
        raw_data = []
        for unit in data:
            if isinstance(unit, Text):
                res = split(unit.text.lstrip(' '), separates)
                if not res:
                    continue
                raw_data.append(res)
                __t = True
            elif unit.__class__.__name__ not in self.filter_out:
                raw_data.append(unit)
            else:
                continue
            i += 1
        if __t is False:
            exp = NullTextMessage(lang_config.analyser_handle_null_message.format(target=data))
            if self.is_raise_exception:
                raise exp
            self.temporary_data["fail"] = exp
        else:
            self.raw_data = raw_data
            self.ndata = i
            self.temp_token = self.generate_token(raw_data)
        return self
