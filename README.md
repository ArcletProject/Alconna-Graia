# Alconna Graia

该项目为 [`Alconna`](https://github.com/ArcletProject/Alconna) 为 [`GraiaProject`](https://github.com/GraiaProject) 下项目的内建支持

包括解析器、Dispatcher、SayaSchema 和 附加组件

## 快速使用

### 单文件

```python
from arclet.alconna.graia import AlconnaDispatcher, Match, AlconnaProperty
from arclet.alconna import Alconna, Args
...

app = Ariadne(...)


alc = Alconna("!jrrp", Args["sth", str, 1123])

@app.broadcast.receiver(
    GroupMessage,
    dispatchers=[AlconnaDispatcher(alc, help_flag='stay')]
)
async def test2(
        group: Group,
        result: AlconnaProperty[GroupMessage],
        sth: Match[str]
):
    print("sign:", result.result)
    print("sender:", group)
    print("match", sth.available, sth.result)
```
### 使用 Saya

in module.py:
```python
from arclet.alconna.graia import AlconnaDispatcher, Match, AlconnaProperty, AlconnaSchema
from arclet.alconna import Alconna, Args
...
channel = Channel.current()

alc = Alconna("!jrrp", Args["sth", str, 1123])

@channel.use(AlconnaSchema(AlconnaDispatcher(alc)))
@channel.use(ListenerSchema([GroupMessage]))
async def test2(group: Group, result: AlconnaProperty[GroupMessage], sth: Match[str]):
    print("sign:", result.result)
    print("sender:", group)
    print("match", sth.available, sth.result)


```

in main.py:
```python
from arclet.alconna.graia import AlconnaBehaviour
from creart import create
...

saya = create(Saya)
create(AlconnaBehaviour)

with saya.module_context():
    saya.require("module")

```
### 使用 Saya util

in module.py:
```python
from arclet.alconna.graia import Match, command
from arclet.alconna import Alconna, Args, Arpamar
...
channel = Channel.current()

@command(Alconna("!jrrp", Args["sth", str, 1123]), private=False)
async def test2(group: Group, result: Arpamar, sth: Match[str]):
    print("sign:", result)
    print("sender:", group)
    print("match", sth.available, sth.result)


```

in main.py:
```python
from creart import create
...

saya = create(Saya)

with saya.module_context():
    saya.require("module")

```

## AlconnaDispatcher 参数说明

```python
class AlconnaDispatcher(BaseDispatcher):
    def __init__(
        self,
        alconna: "Alconna",
        *,
        send_flag: Literal["reply", "post", "stay"] = "stay",
        skip_for_unmatch: bool = True,
        send_handler: Optional[Callable[[str], MessageChain]] = None,
        allow_quote: bool = False
    ): ...
```

`alconna`: 使用的 Alconna 指令

`send_flag`: 解析期间输出信息的发送方式
- reply: 直接发送给指令发送者
- post: 以事件通过 Broadcast 广播
- stay: 存入 AlconnaProperty 传递给事件处理器

`skip_for_unmatch`: 解析失败时是否跳过, 否则错误信息按 send_flag 处理

`send_handler`: send_flag 为 reply 时 输出信息的预处理器

`allow_quote`: 是否允许以回复的方式触发指令

## 附加组件

`Query`

`Match`