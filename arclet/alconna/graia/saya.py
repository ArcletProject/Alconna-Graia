from dataclasses import dataclass
from typing import Union

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
    command: Union[str, Alconna, AlconnaDispatcher]

    @classmethod
    def using(cls, command: str, *options: str, namespace: str = "Graia", flag: str = "reply") -> "AlconnaSchema":
        return cls(command=AlconnaDispatcher(
            alconna=AlconnaString(command, *options).reset_namespace(namespace),
            help_flag=flag  # type: ignore
        ))


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
                    return True
            else:
                if isinstance(cube.metaclass.command, AlconnaDispatcher):
                    listener.dispatchers.append(cube.metaclass.command)
                    return True
                return
        return True

    def uninstall(self, cube: Cube[AlconnaSchema]):
        if not isinstance(cube.metaclass, AlconnaSchema):
            return
        if isinstance(cube.metaclass.command, AlconnaDispatcher):
            self.broadcast.getListener(cube.content).dispatchers.remove(cube.metaclass.command)
            cmd = cube.metaclass.command.command
        else:
            cmd = cube.metaclass.command
        self.manager.delete(cmd)
        return True
