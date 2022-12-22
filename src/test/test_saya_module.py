from arclet.alconna.graia import Alconna, AlconnaDispatcher, alcommand
from arclet.alconna import Args, Arpamar

from graia.ariadne.event.message import GroupMessage
from graia.ariadne.model import Group

from graia.saya.builtins.broadcast import ListenerSchema
from arclet.alconna.graia.saya import AlconnaSchema
from graia.saya.channel import Channel

channel = Channel.current()

alc = Alconna(
    command="!test",
    is_raise_exception=True,
    help_text="test_dispatch"
)

alc1 = Alconna(
    command="jrrp",
    main_args=Args["sth", str, 1123]
)

alc2 = Alconna("{city}今日天气")


@channel.use(
    ListenerSchema(
        [GroupMessage]
    )
)
@channel.use(AlconnaSchema(AlconnaDispatcher(command=alc1)))
async def test2(group: Group, result: Arpamar):
    print("sign:", result)
    print("listener:", group)


@channel.use(AlconnaSchema(AlconnaDispatcher(command=alc)))
@channel.use(ListenerSchema([GroupMessage]))
async def test2(group: Group, result: Arpamar):
    print("test:", result)
    print("listener:", group)


@channel.use(AlconnaSchema(alc2))
@channel.use(
    ListenerSchema(
        [GroupMessage],
        inline_dispatchers=[AlconnaDispatcher(command=alc2)]
    )
)
async def test3(group: Group, result: Arpamar):
    print("city:", result.header)
    print("listener:", group)


@channel.use(AlconnaSchema.from_("ghrepo <link:url>"))
@channel.use(ListenerSchema([GroupMessage]))
async def test4(group: Group, result: Arpamar):
    print("ghrepo:", result.link)
    print("listener:", group)


@alcommand(Alconna("hello!"), private=False)
async def test5(group: Group, result: Arpamar):
    print("result:", result)
    print("group:", group)
