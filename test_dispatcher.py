from arclet.alconna.graia import Alconna, AlconnaDispatcher, AlconnaHelpMessage, Match, Query, success_record, \
    AlconnaProperty, match_path
from arclet.alconna import Args, Arpamar, AlconnaDuplication
from arclet.alconna import ArgsStub, command_manager

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


alc1 = Alconna("!jrrp", Args["sth", str, 1123])


@bcc.receiver(
    GroupMessage,
    dispatchers=[AlconnaDispatcher(alconna=alc1, help_flag='stay')]
)
async def test2(
        group: Group,
        result: AlconnaProperty[GroupMessage],
        sth: Match[str]
):
    print("sign:", result.result)
    print("listener:", group)
    print("match", sth.available, sth.result)


@bcc.receiver(AlconnaHelpMessage)
async def test_event(help_string: str, app: Ariadne, event: GroupMessage):
    print(help_string)
    print(app)
    print(event.sender.group)


alc2 = Alconna("test11") + "foo/bar:int"


@bcc.receiver(
    GroupMessage,
    dispatchers=[AlconnaDispatcher(alc2, help_flag='stay')],
    decorators=[match_path("foo.bar")]
)
async def test3(
        group: Group,
        result: AlconnaProperty[GroupMessage],
        bar: Match[int]
):
    print("result:", result.result)
    print("match", bar.available, bar.result)


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

ev3 = GroupMessage.parse_obj(
    {
        'messageChain': [{"type": "Plain", "text": "test11"}],
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

ev4 = GroupMessage.parse_obj(
    {
        'messageChain': [{"type": "Plain", "text": "test11 foo 123"}],
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
    bcc.postEvent(ev3)
    await asyncio.sleep(0.1)
    bcc.postEvent(ev4)
    await asyncio.sleep(0.1)


loop.run_until_complete(main())
print(success_record)
