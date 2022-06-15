from arclet.alconna.graia import Alconna, AlconnaDispatcher, AlconnaHelpMessage, Query
from arclet.alconna import Args, Arpamar
from arclet.alconna import command_manager

from graia.broadcast import Broadcast
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.model import Group
from graia.ariadne.app import Ariadne
from graia.ariadne.connection.config import config
from graia.ariadne.context import ariadne_ctx
import asyncio

loop = asyncio.get_event_loop()

bcc = Broadcast(loop=loop)

Ariadne.config(loop=loop, broadcast=bcc)
bot = Ariadne(
    connection=config(
        123456789, "1234567890abcdef"
    )
)

alc = Alconna(
    command="!test",
    is_raise_exception=True,
    help_text="test_dispatch"
)

alc1 = Alconna(
    command="!jrrp",
    main_args=Args["sth", str, 1123]
)


ariadne_ctx.set(bot)


@bcc.receiver(
    GroupMessage, dispatchers=[
        AlconnaDispatcher(alconna=alc, help_flag='stay', skip_for_unmatch=True)
    ]
)
async def test(group: Group, result: Arpamar):
    print("test:", result)
    print("listener:", group)
    print(command_manager.all_command_help())


@bcc.receiver(
    GroupMessage, dispatchers=[
        AlconnaDispatcher(alconna=alc1, help_flag='stay')
    ]
)
async def test2(
        group: Group,
        result: Arpamar,
        aaa: Query[str] = "sth",
        bbb: str = Query("sth"),
        ccc: Query = "sth",
        ddd=Query("sth")
):
    print("sign:", result)
    print("listener:", group)
    print("sth:", aaa, bbb, ccc, ddd)
    print("sth_res:", aaa.result, bbb, ccc.result, ddd.result)


@bcc.receiver(AlconnaHelpMessage)
async def test_event(help_string: str, app: Ariadne, event: GroupMessage):
    print(help_string)
    print(app)
    print(event.sender.group)

ev = GroupMessage.parse_obj(
    {
        'messageChain': [{"type": "Plain", "text": "!test --help"}],
        'sender': {
            "id": 12345678,
            "memberName": "test1",
            "specialTitle": "",
            "permission": "MEMBER",
            "joinTimestamp": 0,
            "lastSpeakTimestamp": 0,
            "muteTimeRemaining": 0,
            "group": {
                "id": 987654321,
                "name": "test",
                "permission": "OWNER",
            },
        }
    }
)
ev1 = GroupMessage.parse_obj(
    {
        'messageChain': [{"type": "Plain", "text": "!jrrp -h"}],
        'sender': {
            "id": 54322411,
            "memberName": "test2",
            "specialTitle": "",
            "permission": "MEMBER",
            "joinTimestamp": 0,
            "lastSpeakTimestamp": 0,
            "muteTimeRemaining": 0,
            "group": {
                "id": 123456789,
                "name": "test",
                "permission": "OWNER",
            },
        }
    }
)
ev2 = GroupMessage.parse_obj(
    {
        'messageChain': [{"type": "Plain", "text": "!jrrp 334"}],
        'sender': {
            "id": 42425665,
            "memberName": "test3",
            "specialTitle": "",
            "permission": "MEMBER",
            "joinTimestamp": 0,
            "lastSpeakTimestamp": 0,
            "muteTimeRemaining": 0,
            "group": {
                "id": 987654321,
                "name": "test",
                "permission": "OWNER",
            },
        }
    }
)


async def main():
    bcc.postEvent(ev)
    await asyncio.sleep(0.1)
    bcc.postEvent(ev1)
    await asyncio.sleep(0.1)
    bcc.postEvent(ev2)
    await asyncio.sleep(0.1)


loop.run_until_complete(main())
print(AlconnaDispatcher.success_hook)
