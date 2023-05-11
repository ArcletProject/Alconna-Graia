# Alconna Graia

该项目为 [`Alconna`](https://github.com/ArcletProject/Alconna) 为 [`GraiaProject`](https://github.com/GraiaProject) 下项目的内建支持

包括解析器、Dispatcher、SayaSchema 和 附加组件

## 安装

```shell
pip install arclet-alconna-graia, arclet-alconna-ariadne
pdm add arclet-alconna-graia, arclet-alconna-ariadne
```

或

```shell
pip install arclet-alconna-graia, arclet-alconna-avilla
pdm add arclet-alconna-graia, arclet-alconna-avilla
```

或

```shell
pip install arclet-alconna-graia, arclet-alconna-ichika
pdm add arclet-alconna-graia, arclet-alconna-ichika
```

## 前提

Alconna-Graia 现在依赖 `Launart` 的 `service` 功能

你需要在你使用 Alconna-Graia 组件时加入如下代码：

```python
from launart import Launart
from arclet.alconna.graia import AlconnaGraiaService
from arclet.alconna.xxx import AlconnaXXXAdapter
...

manager = Launart(...)
manager.add_service(AlconnaGraiaService(AlconnaXXXAdapter))
```

`adapater` 的使用可以直接导入：

```python
from launart import Launart
from arclet.alconna.graia import AlconnaGraiaService
import arclet.alconna.xxx
...

manager = Launart(...)
manager.add_service(AlconnaGraiaService())
```

或传入 endpoint, 其等价于直接导入:

```python
from launart import Launart
from arclet.alconna.graia import AlconnaGraiaService
...

manager = Launart(...)
manager.add_service(AlconnaGraiaService("xxx"))
```

不指定 adapter 时 Alconna-Graia 默认使用基础 adapter


## 快速使用

### 单文件

ariadne:

```python
from arclet.alconna import Args
from arclet.alconna.graia import Alconna, AlconnaDispatcher, Match, AlconnaProperty
from arclet.alconna.graia.service import AlconnaGraiaService
import arclet.alconna.ariadne
...
manager = Launart(...)
manager.add_service(AlconnaGraiaService())
app = Ariadne(...)


alc = Alconna("!jrrp", Args["sth", str, 1123])

@app.broadcast.receiver(
    GroupMessage,
    dispatchers=[AlconnaDispatcher(alc, send_flag='stay')]
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

avilla:

```python
from arclet.alconna import Args
from arclet.alconna.graia import Alconna, AlconnaDispatcher, Match, AlconnaProperty
from arclet.alconna.graia.service import AlconnaGraiaService
import arclet.alconna.avilla
...
broadcast = create(Broadcast)
manager = Launart(...)
manager.add_service(AlconnaGraiaService())
avilla = Avilla(...)


alc = Alconna("!jrrp", Args["sth", str, 1123])

@broadcast.receiver(
    MessageReceived,
    dispatchers=[AlconnaDispatcher(alc, send_flag='stay')]
)
async def test2(
    context: Context,
    result: AlconnaProperty[MessageReceived],
    sth: Match[str]
):
    print("sign:", result.result)
    print("sender:", context.scene)
    print("match", sth.available, sth.result)
```

### 使用 Saya

in module.py:
```python
from arclet.alconna.graia import Alconna, AlconnaDispatcher, Match, AlconnaProperty, AlconnaSchema
from arclet.alconna import Args
...
channel = Channel.current()

alc = Alconna("!jrrp", Args["sth", str, 1123])

@channel.use(AlconnaSchema(AlconnaDispatcher(alc)))
@channel.use(ListenerSchema([...]))
async def test2(result: AlconnaProperty[...], sth: Match[str]):
    print("sign:", result.result)
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
### 使用 Saya Util

in module.py:

```python
from graiax.shortcut.saya import listen
from arclet.alconna.graia import alcommand, Alconna, Match, from_command, startswith, endswith
from arclet.alconna import  Args, Arpamar

...


@alcommand(Alconna("!jrrp", Args["sth", str, 1123]), private=False)
async def test1(result: Arpamar, sth: Match[str]):
    print("sign:", result)
    print("match", sth.available, sth.result)


@alcommand("[!|.]hello <name:str>", send_error=True)
async def test1(result: Arpamar, name: Match[str]):
    print("sign:", result)
    print("match", name.available, name.result)

    
@listen(...) 
@from_command("foo bar {baz}")
async def test2(baz: int):
    print("baz", baz)
    
    
@listen(...)
@startswith("foo bar")
async def test3(event: ...):
    ...


@listen(...)
@endswith(int)
async def test4(event: ...):
    ...
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
class AlconnaDispatcher(BaseDispatcher, Generic[TOHandler]):
    def __init__(
        self,
        command: Alconna | AlconnaGroup,
        *,
        send_flag: Literal["reply", "post", "stay"] = "stay",
        skip_for_unmatch: bool = True,
        comp_session: Optional[CompConfig] = None,
        message_converter: Callable[[OutType, str], MessageChain | Coroutine[Any, Any, MessageChain]] | None = None,
    ): ...
```

`command`: 使用的 Alconna 指令

`send_flag`: 解析期间输出信息的发送方式
- reply: 直接发送给指令发送者
- post: 以事件通过 Broadcast 广播
- stay: 存入 AlconnaProperty 传递给事件处理器

`skip_for_unmatch`: 解析失败时是否跳过, 否则错误信息按 send_flag 处理

`comp_session`: 补全会话配置, 不传入则不启用补全会话

`message_converter`: send_flag 为 reply 时 输出信息的预处理器

## 附加组件

- `Match`: 查询某个参数是否匹配，如`foo: Match[int]`。使用时以 `Match.available` 判断是否匹配成功，以
`Match.result` 获取匹配结果

- `Query`: 查询某个参数路径是否存在，如`sth: Query[int] = Query("foo.bar")`；可以指定默认值如
`Query("foo.bar", 1234)`。使用时以 `Query.available` 判断是否匹配成功，以 `Query.result` 获取匹配结果

- `Header`: 表示命令头部为特殊形式时的头部匹配

- `assign`: 依托路径是否匹配成功为命令分发处理器。

```python
from arclet.alconna.graia import assign, alcommand
from arclet.alconna import Alconna, Arpamar
...

alc = Alconna(...)

@alcommand(alc, private=False)
@assign("foo")
async def foo(result: Arpamar):
    ...

@alcommand(alc, private=False)
@assign("bar.baz", 1)
async def bar_baz_1(result: Arpamar):
    ...
```

## 便捷方法

```python
from arclet.alconna.graia import Match, Alc
...

@app.broadcast.receiver(
    ..., dispatchers=[Alc.from_format("foo bar {baz:int}")]
)
async def test2(baz: Match[int]):
    print("match", baz.available, baz.result)
```

or

```python
from arclet.alconna.graia import Match, AlconnaSchema
...
channel = Channel.current()

@channel.use(AlconnaSchema.from_("foo {sth:str} bar {baz:int}"))
@channel.use(ListenerSchema([...]))
async def test2(sth: Match[str]):
    print("match", sth.available, sth.result)
```

## 文档

[链接](https://graiax.cn/guide/alconna.html#kirakira%E2%98%86dokidoki%E7%9A%84dispatcher)