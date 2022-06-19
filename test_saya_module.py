from arclet.alconna.graia import Alconna, AlconnaDispatcher
from arclet.alconna.graia.dispatcher import AlconnaProperty
from arclet.alconna import Args

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
@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=alc1)))
async def test2(group: Group, result: AlconnaProperty):
    print("sign:", result.result)
    print("listener:", group)


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=alc)))
@channel.use(ListenerSchema([GroupMessage]))
async def test2(group: Group, result: AlconnaProperty):
    print("test:", result.result)
    print("listener:", group)


@channel.use(AlconnaSchema(alc2))
@channel.use(
    ListenerSchema(
        [GroupMessage],
        inline_dispatchers=[AlconnaDispatcher(alconna=alc2)]
    )
)
async def test3(group: Group, result: AlconnaProperty):
    print("city:", result.result.header)
    print("listener:", group)


@channel.use(AlconnaSchema.using("ghrepo <link:url>"))
@channel.use(ListenerSchema([GroupMessage]))
async def test4(group: Group, result: AlconnaProperty):
    print("ghrepo:", result.result.link)
    print("listener:", group)
