from arclet.alconna.graia.analyser import MessageChainContainer
from .dispatcher import AlconnaDispatcher, AvillaOutputHandler
from .tools import alcommand, fetch_name, check_account, mention
from .typings import NoticeID

MessageChainContainer.config(
    filter_out=[]
)
Alc = AlconnaDispatcher
