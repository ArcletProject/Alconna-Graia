"""
Alconna 对于 Graia 系列的支持

"""
from arclet.alconna import Alconna

from . import alc as alc
from .analyser import GraiaCommandAnalyser, MessageChainContainer
from .dispatcher import AlconnaOutputMessage, success_record
from .model import AlconnaProperty, Match, Query, Header
from .saya import AlconnaBehaviour, AlconnaSchema
from .tools import (
    MatchPrefix,
    MatchSuffix,
    assign,
    endswith,
    from_command,
    match_path,
    match_value,
    shortcuts,
    startswith,
)

Alconna = Alconna.default_analyser(GraiaCommandAnalyser)
