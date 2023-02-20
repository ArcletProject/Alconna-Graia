from src.arclet.alconna.graia import AlconnaBehaviour, Alconna, alcommand, startswith
from src.arclet.alconna.graia.utils import listen
from graia.saya import Saya, channel_instance
from creart import it
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.app import Ariadne
from graia.ariadne.model import Group
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.context import ariadne_ctx
from graia.ariadne.connection.config import config
from graia.broadcast import Broadcast
from src.arclet.alconna.ariadne import AlconnaAriadneAdapter
import asyncio
import random

AlconnaAriadneAdapter()
bcc = it(Broadcast)
saya = it(Saya)
saya.install_behaviours(AlconnaBehaviour(bcc))
bot = Ariadne(connection=config(123456789, "1234567890abcdef"))
alc = Alconna("!jrrp")

ariadne_ctx.set(bot)
main_ = saya.create_main_channel()
channel_instance.set(main_)


@listen(GroupMessage)
async def on_message_received(event: GroupMessage):
    print(event.message_chain, "Hello, Ariadne!")


@alcommand(alc)
async def on_message_received(sender: Group):
    print(sender.id, '<-', """\
## 菜单
- /help
- /echo
- /md
- /emoji
""")


@listen(GroupMessage)
@startswith("/echo", bind="content")
async def on_message_received(group: Group, content: MessageChain):
    print(group.id, '<-',  content)


with saya.behaviour_interface.require_context("__main__") as inter:
    for cube in main_.content:
        inter.allocate_cube(cube)


def gen(text):
    return GroupMessage.parse_obj(
        {
            "messageChain": [{"type": "Plain", "text": text}],
            "source": {"id": 0, "time": 10},
            "sender": {
                "id": random.randint(1, 1000),
                "memberName": "Member",
                "specialTitle": "",
                "permission": "MEMBER",
                "joinTimestamp": 0,
                "lastSpeakTimestamp": 0,
                "muteTimeRemaining": 0,
                "group": {
                    "id": random.randint(10000, 20000),
                    "name": "Group",
                    "permission": "OWNER",
                },
            },
        }
    )


async def main():
    await bcc.postEvent(gen("!jrrp"))
    await asyncio.sleep(1)
    await bcc.postEvent(gen("/echo 1234"))
    await asyncio.sleep(1)
    await bcc.postEvent(gen("!jrrp"))
    await asyncio.sleep(1)
    await bcc.postEvent(gen("/echo 1234"))
    await asyncio.sleep(1)


bcc.loop.run_until_complete(main())
