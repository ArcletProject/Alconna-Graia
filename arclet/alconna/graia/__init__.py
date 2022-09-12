"""
Alconna 对于 Graia 系列的支持

"""
from arclet.alconna import Alconna
from .analyser import GraiaCommandAnalyser
from .dispatcher import AlconnaDispatcher, AlconnaOutputMessage, success_record
from .saya import AlconnaSchema, AlconnaBehaviour
from .model import AlconnaProperty, Query, Match
from .utils import (
    ImgOrUrl,
    fetch_name,
    match_path,
    AtID,
    alcommand,
    match_value,
    from_command,
    shortcuts,
    assign,
    startswith,
    endswith,
    Startswith,
    Endswith,
)

Alconna.config(analyser_type=GraiaCommandAnalyser)
Alc = AlconnaDispatcher
