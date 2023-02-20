from avilla.console.message import Emoji, Markdown
from avilla.core import Context, MessageChain, MessageReceived

from arclet.alconna import Args
from src.arclet.alconna.graia import Alconna, Match, alcommand, startswith
from src.arclet.alconna.graia.utils import listen


@listen(MessageReceived)
async def on_message_received(ctx: Context):
    await ctx.scene.send_message("Hello, Avilla!")


@alcommand(Alconna("/help"))
async def on_message_received(ctx: Context):
    await ctx.scene.send_message(
        [
            Markdown(
                """\
## 菜单
- /help
- /echo
- /md
- /emoji
"""
            )
        ]
    )


@listen(MessageReceived)
@startswith("/echo", bind="content")
async def on_message_received(ctx: Context, content: MessageChain):
    await ctx.scene.send_message(content)


@alcommand(Alconna("/md"))
async def on_message_received(ctx: Context):
    await ctx.scene.send_message(
        [
            Markdown(
                """\
# Avilla-Console

`avilla` 的 `Console` 适配，使用 `Textual`

参考: [`nonebot-adapter-console`](https://github.com/nonebot/adapter-console)

## 样例

```python
from creart import create
from launart import Launart
from graia.broadcast import Broadcast

from avilla.core import Avilla, Context, MessageReceived
from avilla.console.protocol import ConsoleProtocol

broadcast = create(Broadcast)
launart = Launart()
avilla = Avilla(broadcast, launart, [ConsoleProtocol()])


@broadcast.receiver(MessageReceived)
async def on_message_received(ctx: Context):
    await ctx.scene.send_message("Hello, Avilla!")


launart.launch_blocking(loop=broadcast.loop)

```
"""
            )
        ]
    )


@alcommand(Alconna("/emoji", Args["emoji", str, "art"]))
async def on_message_received(ctx: Context, emoji: Match[str]):
    await ctx.scene.send_message([Emoji(emoji.result), " | this is apple -> ", Emoji("apple")])
