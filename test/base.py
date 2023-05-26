from graia.ariadne.message.chain import MessageChain

from src.arclet.alconna.graia import (
    AlconnaDispatcher,
    AlconnaOutputMessage,
    Match,
    Query,
    CommandResult,
    match_path,
    MatchSuffix,
    MatchPrefix,
)
from src.arclet.alconna.graia.dispatcher import result_cache
from arclet.alconna import Args, Arparma, Duplication, CommandMeta, Alconna
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

bot = Ariadne(connection=config(123456789, "1234567890abcdef"))

alc = Alconna("!test", meta=CommandMeta("test_dispatch", raise_exception=True))

ariadne_ctx.set(bot)

#
# @bcc.receiver(
#     GroupMessage, dispatchers=[
#         AlconnaDispatcher(command=alc, send_flag='stay', skip_for_unmatch=True)
#     ]
# )
# async def test(group: Group, result: Arpamar):
#     print("test:", result)
#     print("listener:", group)
#     print(command_manager.all_command_help())
#
#
# alc1 = Alconna("!jrrp", Args["sth", str, 1123])
#
#
# @bcc.receiver(
#     GroupMessage,
#     dispatchers=[AlconnaDispatcher(command=alc1, send_flag='stay')]
# )
# async def test2(
#         group: Group,
#         result: AlconnaProperty[GroupMessage],
#         sth: Match[str]
# ):
#     print("sign:", result.result)
#     print("listener:", group)
#     print("match", sth.available, sth.result)
#
#
# @bcc.receiver(AlconnaOutputMessage)
# async def test_event(help_string: str, app: Ariadne, event: GroupMessage):
#     print(help_string)
#     print(app)
#     print(event.sender.group)
#
#
# alc2 = Alconna("test11") + "foo/bar:int"
#
#
# @bcc.receiver(
#     GroupMessage,
#     dispatchers=[AlconnaDispatcher(alc2, send_flag='stay')],
#     decorators=[match_path("foo.bar")]
# )
# async def test3(
#         group: Group,
#         result: AlconnaProperty[GroupMessage],
#         bar: Match[int]
# ):
#     print("result:", result.result)
#     print("match", bar.available, bar.result)


@bcc.receiver(GroupMessage)
async def test4(
    group: Group,
    event: GroupMessage,
    message: MessageChain = MatchPrefix("shell"),
):
    print("-", message, "-")


ev = GroupMessage.parse_obj(
    {
        "messageChain": [{"type": "Plain", "text": "!test --help"}],
        "source": {"id": 0, "time": 10},
        "sender": {
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
        },
    }
)
ev1 = GroupMessage.parse_obj(
    {
        "source": {"id": 0, "time": 10},
        "messageChain": [{"type": "Plain", "text": "!jrrp -h"}],
        "sender": {
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
        },
    }
)
ev2 = GroupMessage.parse_obj(
    {
        "source": {"id": 0, "time": 10},
        "messageChain": [{"type": "Plain", "text": "!jrrp 334"}],
        "sender": {
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
        },
    }
)

ev3 = GroupMessage.parse_obj(
    {
        "source": {"id": 0, "time": 10},
        "messageChain": [{"type": "Plain", "text": "test11"}],
        "sender": {
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
        },
    }
)

ev4 = GroupMessage.parse_obj(
    {
        "messageChain": [{"type": "Plain", "text": "test11 foo 123"}],
        "sender": {
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
        },
        "source": {"id": 0, "time": 10},
    }
)

ev5 = GroupMessage.parse_obj(
    {
        "messageChain": [{"type": "Plain", "text": "shell echo hello"}],
        "sender": {
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
        },
        "source": {"id": 0, "time": 10},
    }
)


async def main():
    # bcc.postEvent(ev)
    # await asyncio.sleep(0.1)
    # bcc.postEvent(ev1)
    # await asyncio.sleep(0.1)
    # bcc.postEvent(ev2)
    # await asyncio.sleep(0.1)
    # bcc.postEvent(ev3)
    # await asyncio.sleep(0.1)
    # bcc.postEvent(ev4)
    # await asyncio.sleep(0.1)
    await bcc.postEvent(ev5)


loop.run_until_complete(main())
print(list(result_cache.items()))
