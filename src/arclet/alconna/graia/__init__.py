"""
Alconna 对于 Graia 系列的支持

"""
from . import alc as alc
from .adapter import AlconnaGraiaAdapter as AlconnaGraiaAdapter
from .argv import BaseMessageChainArgv as BaseMessageChainArgv
from .dispatcher import AlconnaDispatcher as AlconnaDispatcher
from .dispatcher import AlconnaOutputMessage as AlconnaOutputMessage
from .model import CommandResult as CommandResult
from .model import Header as Header
from .model import Match as Match
from .model import Query as Query
from .saya import AlconnaBehaviour as AlconnaBehaviour
from .saya import AlconnaSchema as AlconnaSchema
from .service import AlconnaGraiaService as AlconnaGraiaService
from .tools import MatchPrefix as MatchPrefix
from .tools import MatchSuffix as MatchSuffix
from .tools import alcommand as alcommand
from .tools import assign as assign
from .tools import endswith as endswith
from .tools import fetch_name as fetch_name
from .tools import from_command as from_command
from .tools import funcommand as funcommand
from .tools import match_path as match_path
from .tools import match_value as match_value
from .tools import shortcuts as shortcuts
from .tools import startswith as startswith

Alc = AlconnaDispatcher
AlconnaProperty = CommandResult
