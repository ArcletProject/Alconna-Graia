from arclet.alconna.graia import Alconna, AlconnaDispatcher, AlconnaHelpMessage
from arclet.alconna import Args, Arpamar, AlconnaDuplication
from arclet.alconna import ArgsStub, command_manager

from graia.broadcast import Broadcast
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.model import Member, Group
from graia.ariadne.app import Ariadne
from graia.ariadne.adapter import MiraiSession
from graia.ariadne.context import ariadne_ctx
from graia.saya import Saya
from graia.saya.builtins.broadcast import BroadcastBehaviour
from arclet.alconna.graia.saya import AlconnaBehaviour

import asyncio

loop = asyncio.get_event_loop()

bcc = Broadcast(loop=loop)

bot = Ariadne(loop=loop, broadcast=bcc,
              use_loguru_traceback=False,
              connect_info=MiraiSession(host="http://localhost:8080", verify_key="1234567890abcdef", account=123456789))
ariadne_ctx.set(bot)

saya = Saya(bcc)
saya.install_behaviours(
    BroadcastBehaviour(broadcast=bcc),
    AlconnaBehaviour(broadcast=bcc, manager=command_manager)
)

with saya.module_context():
    saya.require("test_saya_module")


m1 = Member(id=12345678, memberName="test1", permission="MEMBER", group=Group(id=987654321, name="test", permission="OWNER"))
m2 = Member(id=54322411, memberName="test2", permission="MEMBER", group=Group(id=123456789, name="test", permission="OWNER"))
m3 = Member(id=42425665, memberName="test3", permission="MEMBER", group=Group(id=987654321, name="test", permission="OWNER"))
#frd = Friend.parse_obj({"id": 12345678, "nickname": "test", "remark": "none"})
#frd1 = Friend.parse_obj({"id": 54322411, "nickname": "test1", "remark": "none1"})
msg = MessageChain.create(f"!test --help")
msg1 = MessageChain.create(f"jrrp --help")
msg2 = MessageChain.create(f"北京今日天气")
msg3 = MessageChain.create("ghrepo https://github.com/ArcletProject/Alconna")
ev = GroupMessage(sender=m1, messageChain=msg)
ev1 = GroupMessage(sender=m2, messageChain=msg1)
ev2 = GroupMessage(sender=m3, messageChain=msg)
ev3 = GroupMessage(sender=m3, messageChain=msg2)
ev4 = GroupMessage(sender=m2, messageChain=msg3)

async def main():
    bcc.postEvent(ev)
    await asyncio.sleep(0.1)
    bcc.postEvent(ev1)
    await asyncio.sleep(0.1)
    bcc.postEvent(ev2)
    await asyncio.sleep(0.1)
    bcc.postEvent(ev3)
    await asyncio.sleep(0.1)
    bcc.postEvent(ev4)
    await asyncio.sleep(0.1)


loop.run_until_complete(main())
print(AlconnaDispatcher)
