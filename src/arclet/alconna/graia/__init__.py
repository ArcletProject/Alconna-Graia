"""
Alconna 对于 Graia 系列的支持

该版本添加了 shortcut 的 支持

"""
from arclet.alconna import Alconna

from . import alc as alc
from .analyser import GraiaCommandAnalyser
from .dispatcher import AlconnaDispatcher, AlconnaOutputMessage, success_record
from .model import AlconnaProperty, Match, Query
from .saya import AlconnaBehaviour, AlconnaSchema
from .utils import (
    AtID,
    ImgOrUrl,
    MatchPrefix,
    MatchSuffix,
    alcommand,
    assign,
    endswith,
    fetch_name,
    from_command,
    match_path,
    match_value,
    shortcuts,
    startswith,
)
from .shortcut import listen, decorate, dispatch, priority

Alconna.default_analyser(GraiaCommandAnalyser)
Alc = AlconnaDispatcher
