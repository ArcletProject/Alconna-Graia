"""
Alconna 对于 Graia 系列的支持

"""
from arclet.alconna import Alconna

from . import alc as alc
from .adapter import AlconnaGraiaAdapter
from .analyser import GraiaCommandAnalyser, MessageChainContainer
from .dispatcher import AlconnaOutputMessage, success_record, AlconnaDispatcher
from .model import AlconnaProperty, Match, Query, Header
from .saya import AlconnaBehaviour, AlconnaSchema
from .service import AlconnaGraiaService
from .tools import (
    MatchPrefix,
    MatchSuffix,
    fetch_name,
    assign,
    endswith,
    alcommand,
    from_command,
    match_path,
    match_value,
    shortcuts,
    startswith,
    check_account,
    mention
)

Alconna = Alconna.default_analyser(GraiaCommandAnalyser)
Alc = AlconnaDispatcher
