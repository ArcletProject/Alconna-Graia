"""
Alconna 对于 Graia 系列的支持

注意：
    现阶段仍使用 graia.ariadne 的 MessageChain;

    后续将会更新为 graia.amnesia 的 MessageChain
"""
from arclet.alconna import Alconna
from .analyser import GraiaCommandAnalyser
from .dispatcher import AlconnaDispatcher, AlconnaOutputMessage, AlconnaProperty, Query, Match, success_record
from .saya import AlconnaSchema, AlconnaBehaviour
from .utils import ImgOrUrl, fetch_name, match_path, AtID, command, match_value

Alconna.config(analyser_type=GraiaCommandAnalyser)
