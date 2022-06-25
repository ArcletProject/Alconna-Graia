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
async def test2(group: Group, result: AlconnaProperty, sth: Match[str]):
    print("sign:", result.result)
    print("sender:", group)
    print("match", sth.available, sth.result)


```

in main.py:
```python
from arclet.alconna.graia import AlconnaBehaviour
...

saya = Saya(...)
saya.install_behaviors(
    AlconnaBehaviour(...)
)

with saya.module_context():
    saya.require("module")

```