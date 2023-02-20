import sys
sys.path.append("D:\\Download\\Projects\\Alconna-Graia")

from creart import create
from launart import Launart
from graia.broadcast import Broadcast
from graia.saya import Saya

from avilla.core import Avilla
from avilla.console.protocol import ConsoleProtocol
from src.arclet.alconna.graia import AlconnaBehaviour, AlconnaGraiaService
from src.arclet.alconna.avilla import AlconnaAvillaAdapter

broadcast = create(Broadcast)
saya = create(Saya)
saya.install_behaviours(AlconnaBehaviour(broadcast))
launart = Launart()
launart.add_service(AlconnaGraiaService(AlconnaAvillaAdapter))
avilla = Avilla(broadcast, launart, [ConsoleProtocol()])

with saya.module_context():
    saya.require("avilla_saya_module")

launart.launch_blocking(loop=broadcast.loop)
