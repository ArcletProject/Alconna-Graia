from dataclasses import dataclass
from typing import Union, Any
import inspect
from pathlib import Path
from graia.broadcast import Broadcast
from graia.saya.behaviour import Behaviour
from graia.saya.cube import Cube
from graia.saya.schema import BaseSchema

from arclet.alconna.manager import CommandManager
from arclet.alconna.builtin.construct import AlconnaString
from arclet.alconna.core import Alconna
from .dispatcher import AlconnaDispatcher


@dataclass
class AlconnaSchema(BaseSchema):
    command: Union[Alconna, AlconnaDispatcher]

    @classmethod
    def using(cls, command: str, *options: str, flag: str = "reply") -> "AlconnaSchema":
        return cls(
            command=AlconnaDispatcher(
                alconna=AlconnaString(command, *options),
                help_flag=flag  # type: ignore
            )
        )

    def record(self, func: Any, manager: CommandManager):
        command: Alconna
        if isinstance(self.command, str):
            command = manager.get_command(self.command)
        elif isinstance(self.command, AlconnaDispatcher):
            command = self.command.command
        else:
            command = self.command
        try:
            file = inspect.getsourcefile(func)
        except TypeError:
            return
        if file:
            path = Path(file)
            command.reset_namespace(f"{path.parts[-2]}.{path.stem}")


class AlconnaBehaviour(Behaviour):
    """命令行为"""

    def __init__(self, broadcast: Broadcast, manager: CommandManager) -> None:
        self.manager = manager
        self.broadcast = broadcast

    def allocate(self, cube: Cube[AlconnaSchema]):
        if not isinstance(cube.metaclass, AlconnaSchema):
            return
        listener = self.broadcast.getListener(cube.content)
        if listener:
            for dispatcher in listener.dispatchers:
                if isinstance(dispatcher, AlconnaDispatcher):
                    cube.metaclass.command = dispatcher.command
                    cube.metaclass.record(cube.content, self.manager)
                    return True
            else:
                if isinstance(cube.metaclass.command, AlconnaDispatcher):
                    listener.dispatchers.append(cube.metaclass.command)
                    cube.metaclass.record(cube.content, self.manager)
                return
        cube.metaclass.record(cube.content, self.manager)
        return True

    def uninstall(self, cube: Cube[AlconnaSchema]):
        if not isinstance(cube.metaclass, AlconnaSchema):
            return
        if isinstance(cube.metaclass.command, AlconnaDispatcher):
            cmd = cube.metaclass.command.command
        else:
            cmd = cube.metaclass.command
        self.manager.delete(cmd)
        return True
