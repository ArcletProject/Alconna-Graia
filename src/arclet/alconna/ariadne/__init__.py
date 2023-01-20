from arclet.alconna.graia.analyser import MessageChainContainer
from .dispatcher import AlconnaDispatcher, AriadneOutputHandler
from .tools import alcommand, fetch_name, check_account, mention
from .typings import ImgOrUrl, AtID

MessageChainContainer.config(
    filter_out=["Source", "File", "Quote"]
)
Alc = AlconnaDispatcher
