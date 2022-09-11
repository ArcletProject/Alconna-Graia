"""
Alconna 对于 Graia 系列的支持

注意：
    现阶段仍使用 graia.ariadne 的 MessageChain;

    后续将会更新为 graia.amnesia 的 MessageChain
"""
from arclet.alconna import Alconna
from .analyser import GraiaCommandAnalyser
from .dispatcher import AlconnaDispatcher, AlconnaOutputMessage, success_record
from .saya import AlconnaSchema, AlconnaBehaviour
from .model import AlconnaProperty, Query, Match
from .utils import ImgOrUrl, fetch_name, match_path, AtID, alcommand, match_value, from_command, shortcuts, assign

Alconna.config(analyser_type=GraiaCommandAnalyser)
Alc = AlconnaDispatcher
